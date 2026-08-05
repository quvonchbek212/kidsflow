"""Backend API bilan ishlovchi HTTP klient (7-bo'lim).

Bot hech qachon bazaga to'g'ridan-to'g'ri ulanmaydi — barcha ma'lumot backend
API orqali olinadi. Ota-ona amallari uchun bot avval `/telegram/session` orqali
o'sha ota-ona nomidan qisqa muddatli token oladi.
"""

from __future__ import annotations

from typing import Any

import httpx

from config import get_bot_settings


class BackendError(Exception):
    """Backend so'rovi muvaffaqiyatsiz bo'ldi."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")


class BackendClient:
    """Backend API uchun yupqa (thin) klient."""

    def __init__(self) -> None:
        settings = get_bot_settings()
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.backend_api_url,
            timeout=settings.request_timeout_seconds,
        )

    # --- Umumiy ---

    async def health(self) -> bool:
        try:
            response = await self._client.get("/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self._client.aclose()

    def _bot_headers(self) -> dict[str, str]:
        return {"X-Bot-Token": self._settings.backend_bot_token}

    @staticmethod
    def _auth_headers(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        response = await self._client.request(
            method, url, headers=headers, json=json
        )
        if response.status_code >= 400:
            detail = _extract_detail(response)
            raise BackendError(response.status_code, detail)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    # --- Telegram hisobini bog'lash (bot token bilan) ---

    async def link_account(
        self, code: str, telegram_user_id: int, telegram_chat_id: int
    ) -> dict:
        return await self._request(
            "POST",
            "/telegram/link",
            headers=self._bot_headers(),
            json={
                "code": code,
                "telegram_user_id": telegram_user_id,
                "telegram_chat_id": telegram_chat_id,
            },
        )

    async def get_session_token(self, telegram_user_id: int) -> str | None:
        """Bog'langan ota-ona uchun access token oladi (bog'lanmagan bo'lsa None)."""
        try:
            data = await self._request(
                "POST",
                "/telegram/session",
                headers=self._bot_headers(),
                json={"telegram_user_id": telegram_user_id},
            )
        except BackendError as exc:
            if exc.status_code in (401, 404):
                return None
            raise
        return data.get("access_token") if data else None

    # --- Ota-ona ma'lumotlari (session token bilan) ---

    async def list_children(self, token: str) -> list[dict]:
        return await self._request(
            "GET", "/children", headers=self._auth_headers(token)
        )

    async def child_attendance(self, token: str, child_id: str) -> list[dict]:
        return await self._request(
            "GET",
            f"/attendance/child/{child_id}",
            headers=self._auth_headers(token),
        )

    async def child_reports(self, token: str, child_id: str) -> list[dict]:
        return await self._request(
            "GET",
            f"/children/{child_id}/daily-reports",
            headers=self._auth_headers(token),
        )

    async def child_invoices(self, token: str, child_id: str) -> list[dict]:
        return await self._request(
            "GET",
            f"/children/{child_id}/invoices",
            headers=self._auth_headers(token),
        )

    async def ask_assistant(self, token: str, question: str) -> dict:
        return await self._request(
            "POST",
            "/ai/assistant",
            headers=self._auth_headers(token),
            json={"question": question},
        )


def _extract_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        detail = body.get("detail")
        if isinstance(detail, str):
            return detail
    except (ValueError, AttributeError):
        pass
    return "So'rovni bajarib bo'lmadi."
