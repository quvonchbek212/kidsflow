"""Email yuborish abstraksiyasi (parolni tiklash uchun, Gmail SMTP).

`telegram_sender.py` bilan bir xil naqsh: pluggable interfeys, sozlanmagan
holatda hech narsa yubormaydigan Noop implementatsiya.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    async def send(self, to: str, subject: str, body: str) -> bool:
        """Xat yuboradi. Muvaffaqiyatda True qaytaradi."""
        ...


class NoopEmailSender:
    """SMTP sozlanmagan holat — faqat log'ga yozadi."""

    async def send(self, to: str, subject: str, body: str) -> bool:
        logger.info(
            "SMTP sozlanmagan — xat yuborilmadi",
            extra={"to": to, "subject": subject},
        )
        return False


class SmtpEmailSender:
    """Gmail (yoki boshqa) SMTP orqali real yuboruvchi (STARTTLS)."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_addr: str,
        from_name: str,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_addr = from_addr
        self._from_name = from_name

    async def send(self, to: str, subject: str, body: str) -> bool:
        try:
            await asyncio.to_thread(self._send_sync, to, subject, body)
            return True
        except (smtplib.SMTPException, OSError):
            logger.exception("SMTP orqali xat yuborishda xatolik", extra={"to": to})
            return False

    def _send_sync(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{self._from_name} <{self._from_addr}>"
        message["To"] = to
        message.set_content(body)

        with smtplib.SMTP(self._host, self._port, timeout=10) as client:
            client.starttls()
            client.login(self._username, self._password)
            client.send_message(message)


def get_default_email_sender() -> EmailSender:
    """Konfiguratsiyaga qarab yuboruvchini tanlaydi."""
    settings = get_settings()
    if settings.smtp_host and settings.smtp_username and settings.smtp_password:
        return SmtpEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            from_addr=settings.smtp_from or settings.smtp_username,
            from_name=settings.smtp_from_name,
        )
    return NoopEmailSender()
