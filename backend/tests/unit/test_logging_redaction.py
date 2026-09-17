"""Loglarda Telegram bot tokeni chiqmasligi."""

from __future__ import annotations

import logging
import sys

from app.core.logging import JsonFormatter, configure_logging

# Soxta, lekin haqiqiy token shaklidagi qiymat.
TOKEN = "1234567890:AAFakeTokenForTests_abcdefghijklmnop"
URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"


def _record(message: str, exc_info=None) -> logging.LogRecord:
    return logging.LogRecord("test", logging.INFO, __file__, 1, message, (), exc_info)


def test_bot_token_is_redacted_in_message() -> None:
    out = JsonFormatter().format(_record(f"HTTP Request: POST {URL}"))
    assert TOKEN not in out
    assert "api.telegram.org/bot<yashirilgan>/sendMessage" in out


def test_bot_token_is_redacted_in_exception() -> None:
    try:
        raise RuntimeError(f"Client error for url '{URL}'")
    except RuntimeError:
        out = JsonFormatter().format(_record("Telegram xatosi", sys.exc_info()))
    assert TOKEN not in out
    assert "bot<yashirilgan>" in out


def test_http_client_request_logs_are_silenced() -> None:
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    try:
        configure_logging(debug=True)
        assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
        assert logging.getLogger("httpcore").getEffectiveLevel() >= logging.WARNING
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)
