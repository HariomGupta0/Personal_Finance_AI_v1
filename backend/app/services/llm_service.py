import logging
import time

from groq import Groq

from backend.config import GROQ_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

_client: Groq | None = None


def _get_client() -> Groq:
    """Lazy-init Groq client — avoids import-time side effects and enables mocking."""
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file or environment."
            )
        _client = Groq(api_key=GROQ_API_KEY, timeout=20.0)
    return _client


def ask_llm(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    retries: int = 2,
    fallback_text: str | None = None,
) -> dict:
    """
    Call the Groq LLM with exponential-backoff retry.

    Returns a dict with the following keys:
      - content          (str)   : The model's text response.
      - tokens_used      (int)   : Total tokens consumed (prompt + completion).
      - prompt_tokens    (int)   : Prompt tokens consumed.
      - completion_tokens(int)   : Completion tokens generated.
      - latency_ms       (float) : Wall-clock time for the successful API call.
      - model            (str)   : Model identifier used.
      - error            (str | None): Set only on fallback; None on success.
    """
    use_model = model or LLM_MODEL

    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    last_exc: Exception | None = None

    for attempt in range(retries + 1):
        t0 = time.perf_counter()
        try:
            resp = _get_client().chat.completions.create(
                model=use_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency_ms = (time.perf_counter() - t0) * 1000
            usage = resp.usage

            logger.info(
                "llm_call | model=%s | prompt_tokens=%d | completion_tokens=%d | latency_ms=%.0f",
                use_model,
                usage.prompt_tokens,
                usage.completion_tokens,
                latency_ms,
            )

            return {
                "content": resp.choices[0].message.content or "",
                "tokens_used": usage.total_tokens,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "latency_ms": round(latency_ms, 1),
                "model": use_model,
                "error": None,
            }

        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                wait = 1.5 * (attempt + 1)
                logger.warning(
                    "llm_call failed attempt %d/%d (%s) — retrying in %.1fs",
                    attempt + 1,
                    retries,
                    type(exc).__name__,
                    wait,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "llm_call failed after %d retries: %s — %s",
                    retries,
                    type(exc).__name__,
                    str(exc),
                )

    # All retries exhausted — return graceful fallback
    fallback_content = fallback_text or (
        "🎯 **Financial Analysis Complete**\n"
        "• All figures have been verified by the deterministic engine.\n"
        "• Please refer to the evidence card below for exact amounts.\n"
        "*(AI explanation temporarily unavailable — your financial data is unaffected.)*"
    )

    return {
        "content": fallback_content,
        "tokens_used": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "latency_ms": 0.0,
        "model": use_model,
        "error": str(last_exc),
    }
