"""Structured JSON logging configuration for the Ovulite backend."""

import json
import logging
import logging.config
import os
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "name": record.name,
        }

        # Include request_id if present (set by middleware)
        request_id = getattr(record, "request_id", None)
        if request_id:
            log_entry["request_id"] = request_id

        # Include exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging() -> None:
    """Configure stdlib logging to output structured JSON.

    Reads LOG_LEVEL from environment (default: INFO).
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
        # Quiet down noisy third-party loggers
        "loggers": {
            "uvicorn": {"level": "WARNING"},
            "uvicorn.access": {"level": "WARNING"},
            "sqlalchemy.engine": {"level": "WARNING"},
        },
    }

    logging.config.dictConfig(config)
