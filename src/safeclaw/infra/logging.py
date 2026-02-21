import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from safeclaw.config.settings import settings


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        if hasattr(record, "tool"):
            log_record["tool"] = record.tool

        if hasattr(record, "principal_id"):
            log_record["principal.id"] = record.principal_id

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Merge extra fields
        if hasattr(record, "extra_fields"):
            log_record.update(record.extra_fields)

        return json.dumps(log_record)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # Remove existing handlers to avoid duplication
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    root_logger.addHandler(handler)

    # Set levels for third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
