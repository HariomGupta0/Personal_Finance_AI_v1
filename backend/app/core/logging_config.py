"""
Central logging configuration for the Personal Finance AI backend.

Call setup_logging() once at application startup (in main.py).
All modules then simply do:
    import logging
    logger = logging.getLogger(__name__)
"""
import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """
    Configure structured, human-readable logging to stdout.

    Format: TIMESTAMP | LEVEL | LOGGER_NAME | MESSAGE

    Args:
        level: Log level string ("DEBUG", "INFO", "WARNING", "ERROR").
               Defaults to "INFO".  Override via LOG_LEVEL env var at
               the call site if desired.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Root logger configuration — applies to all loggers in the process.
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # Override any existing basicConfig (e.g. from uvicorn).
    )

    # Keep uvicorn's own access log at INFO so HTTP requests are visible.
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    # Suppress noisy low-level libs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
