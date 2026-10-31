import asyncio
import logging
import re
import time
from typing import Any

from groq import AsyncGroq, Groq

from backend.config import GROQ_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

_client: Groq | None = None
_async_client: AsyncGroq | None = None


class LLMResponse(dict):
    """
    Subclass of dict representing a structured LLM response.
    Preserves dictionary key-access (e.g. response['content'], response['tokens_used'])
    while supporting direct string operations (e.g. .strip(), str()) for maximum
    backward compatibility with existing callers.
    """

    @property
    def content(self) -> str:
        return str(self.get("content", ""))

    @property
    def is_fallback(self) -> bool:
        return bool(self.get("is_fallback", False))

    @property
    def latency_ms(self) -> float:
        return float(self.get("latency_ms", 0.0))

    def strip(self, *args, **kwargs) -> str:
        return self.content.strip(*args, **kwargs)

    def startswith(self, *args, **kwargs) -> bool:
        return self.content.startswith(*args, **kwargs)

    def endswith(self, *args, **kwargs) -> bool:
        return self.content.endswith(*args, **kwargs)

    def __str__(self) -> str:
        return self.content


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


def _get_async_client() -> AsyncGroq:
    """Lazy-init AsyncGroq client for non-blocking asynchronous calls."""
    global _async_client
    if _async_client is None:
        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file or environment."
            )
        _async_client = AsyncGroq(api_key=GROQ_API_KEY, timeout=20.0)
    return _async_client


def _is_transient_error(exc: Exception) -> bool:
    """
    Determine whether an error is transient (safe to retry) or permanent.
    Permanent failures (e.g., 401 auth, 400 bad request, 404, 422) fail fast
    without wasting time on futile retries.
    """
    exc_type = type(exc).__name__
    status_code = getattr(exc, "status_code", None)

    # Permanent HTTP status codes
    if status_code is not None:
        if status_code in (400, 401, 403, 404, 422):
            return False
        if status_code in (408, 429, 500, 502, 503, 504):
            return True

    # Known permanent error class names
    permanent_types = (
        "AuthenticationError",
        "PermissionDeniedError",
        "BadRequestError",
        "NotFoundError",
        "UnprocessableEntityError",
    )
    if any(pt in exc_type for pt in permanent_types):
        return False

    msg_lower = str(exc).lower()
    if any(
        k in msg_lower
        for k in (
            "invalid api key",
            "unauthorized",
            "model_not_found",
            "permission denied",
        )
    ):
        return False

    # Known transient error types or keywords
    transient_types = (
        "RateLimitError",
        "APIConnectionError",
        "APITimeoutError",
        "InternalServerError",
        "TimeoutError",
        "ConnectionError",
    )
    if any(tt in exc_type for tt in transient_types):
        return True

    if any(
        k in msg_lower
        for k in (
            "rate limit",
            "timed out",
            "timeout",
            "connection refused",
            "temporarily unavailable",
            "503",
            "502",
            "504",
        )
    ):
        return True

    # Generic exceptions default to retry if attempts remain
    return True


def _sanitize_error(exc: Exception | None) -> str | None:
    """
    Sanitize internal/provider exceptions into safe, human-readable strings.
    Strips raw API keys, bearer tokens, file paths, and sensitive connection info.
    """
    if exc is None:
        return None

    exc_type = type(exc).__name__
    raw_msg = str(exc)

    # Redact sensitive patterns
    sanitized = re.sub(r"gsk_[a-zA-Z0-9_-]+", "[REDACTED_API_KEY]", raw_msg)
    sanitized = re.sub(
        r"Bearer\s+[a-zA-Z0-9_\-\.]+", "Bearer [REDACTED_TOKEN]", sanitized, flags=re.IGNORECASE
    )
    sanitized = re.sub(r"[A-Za-z]:\\[^ \n\r\t]+", "[REDACTED_PATH]", sanitized)

    # Clean standardized categories
    if "AuthenticationError" in exc_type or "401" in sanitized or "unauthorized" in sanitized.lower():
        return "Authentication failure with LLM provider (check GROQ_API_KEY)"
    if "PermissionDeniedError" in exc_type or "403" in sanitized:
        return "Permission denied by LLM provider"
    if "RateLimitError" in exc_type or "rate limit" in sanitized.lower():
        return f"LLM provider rate limit exceeded: {sanitized[:80]}"
    if "APITimeoutError" in exc_type or "timeout" in sanitized.lower():
        return "LLM provider request timed out"
    if "APIConnectionError" in exc_type or "connection" in sanitized.lower():
        return "Failed to connect to LLM provider"
    if "BadRequestError" in exc_type or "400" in sanitized:
        return f"Invalid request to LLM provider: {sanitized[:80]}"

    return sanitized[:120].strip() or "LLM provider service error"


_DEFAULT_FALLBACK_TEXT = (
    "🎯 **The Quick Take**\n"
    "Financial Analysis Complete. All figures have been verified by the deterministic engine.\n\n"
    "📊 **The Numbers**\n"
    "• All amounts and balances are preserved in Indian Rupees (₹).\n"
    "• Please refer to the evidence card below for exact amounts.\n\n"
    "💡 **Smart Insights**\n"
    "• The deterministic financial engine serves as the single source of truth.\n"
    "• Your financial data and calculations remain 100% accurate and unaffected.\n\n"
    "🚀 **What You Should Do Next**\n"
    "• Review the verified evidence cards below for detailed breakdown.\n"
    "*(AI explanation temporarily unavailable — your financial data is unaffected.)*"
)



async def ask_llm_async(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    retries: int = 2,
    fallback_text: str | None = None,
) -> LLMResponse:
    """
    Non-blocking async call to Groq LLM with exponential-backoff retry
    and comprehensive telemetry tracking.
    """
    use_model = model or LLM_MODEL

    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    last_exc: Exception | None = None
    overall_start = time.perf_counter()

    for attempt in range(retries + 1):
        try:
            resp = await _get_async_client().chat.completions.create(
                model=use_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            raw_content = resp.choices[0].message.content or ""

            # Guard against empty completions
            if not raw_content.strip():
                logger.warning(
                    "async_llm_call returned empty response on attempt %d/%d",
                    attempt + 1,
                    retries + 1,
                )
                if attempt < retries:
                    wait = 1.0 * (attempt + 1)
                    await asyncio.sleep(wait)
                    continue
                last_exc = RuntimeError("LLM returned empty response")
                break

            total_latency_ms = (time.perf_counter() - overall_start) * 1000
            usage = resp.usage

            logger.info(
                "async_llm_call | model=%s | prompt_tokens=%d | completion_tokens=%d | latency_ms=%.0f",
                use_model,
                usage.prompt_tokens,
                usage.completion_tokens,
                total_latency_ms,
            )

            return LLMResponse(
                {
                    "content": raw_content,
                    "tokens_used": usage.total_tokens,
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "latency_ms": round(total_latency_ms, 1),
                    "model": use_model,
                    "is_fallback": False,
                    "error": None,
                }
            )

        except Exception as exc:
            last_exc = exc
            is_transient = _is_transient_error(exc)

            if is_transient and attempt < retries:
                wait = 1.5 * (attempt + 1)
                logger.warning(
                    "async_llm_call failed attempt %d/%d (%s) — retrying in %.1fs",
                    attempt + 1,
                    retries + 1,
                    type(exc).__name__,
                    wait,
                )
                await asyncio.sleep(wait)
            else:
                if not is_transient:
                    logger.warning(
                        "async_llm_call encountered non-transient error (%s) — aborting retries",
                        type(exc).__name__,
                    )
                else:
                    logger.error(
                        "async_llm_call failed after %d retries: %s",
                        retries,
                        _sanitize_error(exc),
                    )
                break

    # Graceful fallback response
    total_latency_ms = (time.perf_counter() - overall_start) * 1000
    fallback_content = fallback_text or _DEFAULT_FALLBACK_TEXT
    sanitized_err = _sanitize_error(last_exc)

    return LLMResponse(
        {
            "content": fallback_content,
            "tokens_used": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": round(total_latency_ms, 1),
            "model": use_model,
            "is_fallback": True,
            "error": sanitized_err,
        }
    )


def ask_llm(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    retries: int = 2,
    fallback_text: str | None = None,
) -> LLMResponse:
    """
    Call the Groq LLM synchronously with exponential-backoff retry
    and comprehensive telemetry tracking.
    """
    use_model = model or LLM_MODEL

    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    last_exc: Exception | None = None
    overall_start = time.perf_counter()

    for attempt in range(retries + 1):
        try:
            resp = _get_client().chat.completions.create(
                model=use_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            raw_content = resp.choices[0].message.content or ""

            # Guard against empty completions
            if not raw_content.strip():
                logger.warning(
                    "llm_call returned empty response on attempt %d/%d",
                    attempt + 1,
                    retries + 1,
                )
                if attempt < retries:
                    wait = 1.0 * (attempt + 1)
                    time.sleep(wait)
                    continue
                last_exc = RuntimeError("LLM returned empty response")
                break

            total_latency_ms = (time.perf_counter() - overall_start) * 1000
            usage = resp.usage

            logger.info(
                "llm_call | model=%s | prompt_tokens=%d | completion_tokens=%d | latency_ms=%.0f",
                use_model,
                usage.prompt_tokens,
                usage.completion_tokens,
                total_latency_ms,
            )

            return LLMResponse(
                {
                    "content": raw_content,
                    "tokens_used": usage.total_tokens,
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "latency_ms": round(total_latency_ms, 1),
                    "model": use_model,
                    "is_fallback": False,
                    "error": None,
                }
            )

        except Exception as exc:
            last_exc = exc
            is_transient = _is_transient_error(exc)

            if is_transient and attempt < retries:
                wait = 1.5 * (attempt + 1)
                logger.warning(
                    "llm_call failed attempt %d/%d (%s) — retrying in %.1fs",
                    attempt + 1,
                    retries + 1,
                    type(exc).__name__,
                    wait,
                )
                time.sleep(wait)
            else:
                if not is_transient:
                    logger.warning(
                        "llm_call encountered non-transient error (%s) — aborting retries",
                        type(exc).__name__,
                    )
                else:
                    logger.error(
                        "llm_call failed after %d retries: %s",
                        retries,
                        _sanitize_error(exc),
                    )
                break

    # All retries exhausted or permanent error — return graceful fallback
    total_latency_ms = (time.perf_counter() - overall_start) * 1000
    fallback_content = fallback_text or _DEFAULT_FALLBACK_TEXT
    sanitized_err = _sanitize_error(last_exc)

    return LLMResponse(
        {
            "content": fallback_content,
            "tokens_used": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": round(total_latency_ms, 1),
            "model": use_model,
            "is_fallback": True,
            "error": sanitized_err,
        }
    )


# Alias for explicit synchronous usage
ask_llm_sync = ask_llm

__all__ = [
    "LLMResponse",
    "ask_llm",
    "ask_llm_async",
    "ask_llm_sync",
    "_is_transient_error",
    "_sanitize_error",
]


