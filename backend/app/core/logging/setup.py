import os
import sys
import logging
from typing import Optional

from app.core.logging.formatter import StructuredJSONFormatter


def setup_logging(log_level: Optional[str] = None, structured: bool = True) -> None:
    """
    Configures root logging with StructuredJSONFormatter for cloud-native/Docker observability.
    Guarantees consistent JSON output to standard output stream.
    """
    level_name = (log_level or os.getenv("LOG_LEVEL", "INFO")).upper().strip()
    numeric_level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers to prevent duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    if structured:
        stream_handler.setFormatter(StructuredJSONFormatter())
    else:
        stream_handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        )

    root_logger.addHandler(stream_handler)

    # Harmonize third-party noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
