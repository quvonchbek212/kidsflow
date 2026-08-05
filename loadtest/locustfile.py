"""KIDSFLOW yuklama testi (12-bo'lim: yuklama testi).

Ishga tushirish (avval `pip install locust`):
    locust -f loadtest/locustfile.py --host http://localhost:8000

So'ng brauzerda http://localhost:8089 orqali foydalanuvchilar sonini belgilang.

Muhit o'zgaruvchilari:
    KIDSFLOW_LOGIN     login (telefon yoki email)
    KIDSFLOW_PASSWORD  parol
Agar berilmasa, faqat autentifikatsiyasiz (health/docs) yo'llar sinaladi.
"""

from __future__ import annotations

import os

from locust import HttpUser, between, task

API = "/api/v1"


class PublicUser(HttpUser):
    """Autentifikatsiyasiz yo'llar: health, readiness, openapi."""

    wait_time = between(1, 3)

    @task(3)
    def health(self) -> None:
        self.client.get(f"{API}/health", name="health")

    @task(1)
    def openapi(self) -> None:
        self.client.get(f"{API}/openapi.json", name="openapi")


class AuthenticatedUser(HttpUser):
    """Login qilib, himoyalangan yo'llarni sinaydi (login ma'lumotlari berilsa)."""

    wait_time = between(1, 4)

    def on_start(self) -> None:
        login = os.getenv("KIDSFLOW_LOGIN")
        password = os.getenv("KIDSFLOW_PASSWORD")
        self.token: str | None = None
        if not login or not password:
            return
        resp = self.client.post(
            f"{API}/auth/login",
            json={"login": login, "password": password},
            name="auth/login",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")

    @task
    def me(self) -> None:
        if not self.token:
            return
        self.client.get(
            f"{API}/auth/me",
            headers={"Authorization": f"Bearer {self.token}"},
            name="auth/me",
        )

    @task
    def list_children(self) -> None:
        if not self.token:
            return
        self.client.get(
            f"{API}/children",
            headers={"Authorization": f"Bearer {self.token}"},
            name="children",
        )
