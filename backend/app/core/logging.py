"""Strukturali JSON logging sozlamasi (12-bo'lim: strukturali log)."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime

# Telegram Bot API manzili tokenni o'z ichiga oladi:
# `https://api.telegram.org/bot<id>:<maxfiy>/sendMessage`. U so'rov logi yoki
# xato matni (httpx istisnosi manzilni ko'rsatadi) orqali logga tushardi — log
# ko'rgan har kim bot nomidan ota-onalarga yoza olardi.
_BOT_TOKEN_RE = re.compile(r"bot\d+:[A-Za-z0-9_-]+")


def redact_secrets(text: str) -> str:
    """Log matnidan maxfiy qiymatlarni (bot tokeni) olib tashlaydi."""
    return _BOT_TOKEN_RE.sub("bot<yashirilgan>", text)


class JsonFormatter(logging.Formatter):
    """Log yozuvlarini JSON ko'rinishida chiqaradi."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Qo'shimcha kontekst (extra=...) maydonlarini qo'shish.
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_KEYS and not key.startswith("_"):
                payload[key] = value

        # Oxirgi satrga qo'llanadi — xabar, istisno va extra maydonlar birdan
        # tozalanadi.
        return redact_secrets(json.dumps(payload, ensure_ascii=False, default=str))


_RESERVED_LOG_KEYS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime"}


def configure_logging(debug: bool = False) -> None:
    """Root loggerni JSON formatter bilan sozlaydi."""
    level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Kutubxonalarning ortiqcha loglarini kamaytirish.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    # httpx har so'rovni to'liq manzili bilan (INFO), httpcore esa har TCP/TLS
    # qadamini (DEBUG) yozadi — worker Telegram'ga yuborganda log shu shovqin
    # bilan to'lib ketardi.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
