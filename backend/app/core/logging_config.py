"""
Central logging configuration for the Personal Finance AI backend.

Call setup_logging() once at application startup (in main.py).
All modules then simply do:
    import logging
    logger = logging.getLogger(__name__)
"""
import logging
import re
import sys


class SensitiveDataFilter(logging.Filter):
    """
    Scans and redacts credentials, passwords, session tokens, API keys,
    and sensitive financial numbers from all log outputs.
    """
    PATTERNS = [
        # Passwords in JSON / query params / dicts
        (re.compile(r'(["\']?password["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])', re.IGNORECASE), r'\1[REDACTED_PASSWORD]\3'),
        # Session secrets and bearer tokens
        (re.compile(r'(finance_session=)[a-zA-Z0-9_\-\.]+', re.IGNORECASE), r'\1[REDACTED_SESSION]'),
        (re.compile(r'(Bearer\s+)[a-zA-Z0-9_\-\.]+', re.IGNORECASE), r'\1[REDACTED_TOKEN]'),
        # Groq / OpenAI API keys
        (re.compile(r'gsk_[a-zA-Z0-9_-]+', re.IGNORECASE), '[REDACTED_API_KEY]'),
        (re.compile(r'sk-[a-zA-Z0-9_-]{20,}', re.IGNORECASE), '[REDACTED_API_KEY]'),
        # Credit card numbers (13-19 digits with optional spaces/hyphens)
        (re.compile(r'\b(?:\d[ -]*?){13,19}\b'), '[REDACTED_CARD_NUMBER]'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        if record.args:
            if isinstance(record.args, dict):
                clean_args = dict(record.args)
                for k, v in clean_args.items():
                    if isinstance(v, str):
                        for pattern, replacement in self.PATTERNS:
                            clean_args[k] = pattern.sub(replacement, v)
                record.args = clean_args
            elif isinstance(record.args, tuple):
                clean_args = []
                for item in record.args:
                    if isinstance(item, str):
                        for pattern, replacement in self.PATTERNS:
                            item = pattern.sub(replacement, item)
                    clean_args.append(item)
                record.args = tuple(clean_args)
        return True


def setup_logging(level: str = "INFO") -> None:
    """
    Configure structured, human-readable logging to stdout with sensitive data redaction.

    Format: TIMESTAMP | LEVEL | LOGGER_NAME | MESSAGE

    Args:
        level: Log level string ("DEBUG", "INFO", "WARNING", "ERROR").
               Defaults to "INFO".  Override via LOG_LEVEL env var at
               the call site if desired.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.addFilter(SensitiveDataFilter())

    # Root logger configuration — applies to all loggers in the process.
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[stream_handler],
        force=True,  # Override any existing basicConfig (e.g. from uvicorn).
    )

    # Keep uvicorn's own access log at INFO so HTTP requests are visible.
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    # Suppress noisy low-level libs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
