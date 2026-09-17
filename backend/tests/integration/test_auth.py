"""Login, refresh va me oqimi uchun integratsiya testlari (11-bo'lim)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import FakeEmailSender, auth_header, complete_setup, login

pytestmark = pytest.mark.asyncio

OWNER_USERNAME = "egasi"
OWNER_PHONE = "+998901112233"
OWNER_EMAIL = "egasi@example.com"
OWNER_PASSWORD = "owner-parol-123"


async def test_login_success_returns_tokens(client: AsyncClient) -> None:
    await complete_setup(client)
    tokens = await login(client, OWNER_PHONE, OWNER_PASSWORD)

    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] > 0


async def test_login_wrong_password_rejected(client: AsyncClient) -> None:
    await complete_setup(client)
    response = await client.post(
        "/api/v1/auth/login",
        json={"login": OWNER_PHONE, "password": "noto'g'ri"},
    )
    assert response.status_code == 401


async def test_me_returns_owner_role(client: AsyncClient) -> None:
    await complete_setup(client)
    tokens = await login(client, OWNER_PHONE, OWNER_PASSWORD)

    response = await client.get(
        "/api/v1/auth/me", headers=auth_header(tokens["access_token"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["phone"] == OWNER_PHONE
    assert body["roles"][0]["role"] == "OWNER"


async def test_me_requires_token(client: AsyncClient) -> None:
    await complete_setup(client)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_refresh_rotation_invalidates_old_token(client: AsyncClient) -> None:
    await complete_setup(client)
    tokens = await login(client, OWNER_PHONE, OWNER_PASSWORD)
    old_refresh = tokens["refresh_token"]

    # Birinchi refresh muvaffaqiyatli.
    first = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert first.status_code == 200

    # Eski refresh token endi ishlamaydi (rotation).
    second = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert second.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    await complete_setup(client)
    tokens = await login(client, OWNER_PHONE, OWNER_PASSWORD)

    logout_resp = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_resp.status_code == 204

    reuse = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse.status_code == 401


async def test_login_with_username_success(client: AsyncClient) -> None:
    await complete_setup(client, owner_username=OWNER_USERNAME)
    tokens = await login(client, OWNER_USERNAME, OWNER_PASSWORD)
    assert tokens["access_token"]


async def test_me_returns_username(client: AsyncClient) -> None:
    await complete_setup(client, owner_username=OWNER_USERNAME)
    tokens = await login(client, OWNER_USERNAME, OWNER_PASSWORD)
    response = await client.get(
        "/api/v1/auth/me", headers=auth_header(tokens["access_token"])
    )
    assert response.json()["username"] == OWNER_USERNAME


async def test_forgot_password_sends_reset_email(
    client: AsyncClient, monkeypatch
) -> None:
    fake = FakeEmailSender()
    monkeypatch.setattr(
        "app.services.auth_service.get_default_email_sender", lambda: fake
    )
    await complete_setup(client, owner_email=OWNER_EMAIL)

    response = await client.post(
        "/api/v1/auth/forgot-password", json={"email": OWNER_EMAIL}
    )
    assert response.status_code == 204
    assert len(fake.sent) == 1
    to, subject, body = fake.sent[0]
    assert to == OWNER_EMAIL
    assert "reset-password?token=" in body


async def test_forgot_password_unknown_email_is_silent(
    client: AsyncClient, monkeypatch
) -> None:
    """Xavfsizlik: mavjud bo'lmagan email uchun ham 204 qaytadi, xat yuborilmaydi."""
    fake = FakeEmailSender()
    monkeypatch.setattr(
        "app.services.auth_service.get_default_email_sender", lambda: fake
    )
    await complete_setup(client, owner_email=OWNER_EMAIL)

    response = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "noone@example.com"}
    )
    assert response.status_code == 204
    assert fake.sent == []


async def test_reset_password_with_token_changes_password(
    client: AsyncClient, monkeypatch
) -> None:
    fake = FakeEmailSender()
    monkeypatch.setattr(
        "app.services.auth_service.get_default_email_sender", lambda: fake
    )
    await complete_setup(client, owner_username=OWNER_USERNAME, owner_email=OWNER_EMAIL)
    await client.post("/api/v1/auth/forgot-password", json={"email": OWNER_EMAIL})

    body = fake.sent[0][2]
    token = body.split("token=")[1].split()[0].strip()

    new_password = "yangi-parol-456"
    reset_resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )
    assert reset_resp.status_code == 204

    # Eski parol endi ishlamaydi.
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"login": OWNER_USERNAME, "password": OWNER_PASSWORD},
    )
    assert old_login.status_code == 401

    # Yangi parol ishlaydi.
    new_login = await login(client, OWNER_USERNAME, new_password)
    assert new_login["access_token"]

    # Token bir martalik — qayta ishlatib bo'lmaydi.
    reuse = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "yana-boshqa-789"},
    )
    assert reuse.status_code == 401


async def test_update_own_profile(client: AsyncClient) -> None:
    """Foydalanuvchi o'z ismi, telefoni va tilini o'zgartira oladi."""
    setup = await complete_setup(client)
    assert setup
    access = (await login(client, OWNER_USERNAME, OWNER_PASSWORD))["access_token"]

    resp = await client.patch(
        "/api/v1/auth/me",
        headers=auth_header(access),
        json={
            "full_name": "Yangi Ism",
            "phone": "+998901234567",
            "preferred_language": "ru",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["full_name"] == "Yangi Ism"
    assert body["phone"] == "+998901234567"
    assert body["preferred_language"] == "ru"

    # O'zgarish saqlangan — /me ham yangi qiymatlarni qaytaradi.
    me = await client.get("/api/v1/auth/me", headers=auth_header(access))
    assert me.json()["full_name"] == "Yangi Ism"


async def test_teacher_can_update_own_profile(client: AsyncClient) -> None:
    """Tarbiyachi ham o'z profilini tahrirlaydi — bu OWNER huquqi emas.

    `PATCH /users/{id}` faqat OWNER uchun, shuning uchun tarbiyachining o'z
    profilini o'zgartira olishi alohida tekshiriladi.
    """
    from tests.conftest import create_staff

    setup = await complete_setup(client)
    owner = (await login(client, OWNER_USERNAME, OWNER_PASSWORD))["access_token"]
    await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000077",
        password="teacher-parol-1",
        branch_id=setup["branch_id"],
        username="tarbiyachi",
    )
    teacher = (await login(client, "tarbiyachi", "teacher-parol-1"))["access_token"]

    resp = await client.patch(
        "/api/v1/auth/me",
        headers=auth_header(teacher),
        json={"full_name": "Zulfiya Rahimova", "preferred_language": "en"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["full_name"] == "Zulfiya Rahimova"


async def test_profile_rejects_duplicate_phone(client: AsyncClient) -> None:
    """Boshqa xodimning telefon raqamini o'zlashtirib bo'lmaydi."""
    from tests.conftest import create_staff

    setup = await complete_setup(client)
    owner = (await login(client, OWNER_USERNAME, OWNER_PASSWORD))["access_token"]
    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000088",
        password="mgr-parol-12",
        branch_id=setup["branch_id"],
        username="menejer",
    )
    manager = (await login(client, "menejer", "mgr-parol-12"))["access_token"]

    # OWNER'ning telefon raqamini olishga urinish.
    resp = await client.patch(
        "/api/v1/auth/me",
        headers=auth_header(manager),
        json={"phone": OWNER_PHONE},
    )
    assert resp.status_code == 409, resp.text


async def test_profile_cannot_change_role_or_salary(client: AsyncClient) -> None:
    """Sxema faqat uch maydonni qabul qiladi — qolgani e'tiborsiz qoldiriladi.

    Foydalanuvchi o'ziga maosh belgilay olmasligi yoki hisobini o'chira
    olmasligi kerak.
    """
    await complete_setup(client, owner_email=OWNER_EMAIL)
    access = (await login(client, OWNER_USERNAME, OWNER_PASSWORD))["access_token"]

    resp = await client.patch(
        "/api/v1/auth/me",
        headers=auth_header(access),
        json={
            "full_name": "Egasi",
            "monthly_salary": "99000000",
            "is_active": False,
            "email": "boshqa@example.com",
        },
    )
    assert resp.status_code == 200, resp.text
    # Email o'zgarmagan — sxema uni qabul qilmaydi.
    assert resp.json()["email"] == OWNER_EMAIL

    # Hisob hali faol: login ishlayapti.
    again = await login(client, OWNER_USERNAME, OWNER_PASSWORD)
    assert again["access_token"]


async def test_validation_error_does_not_echo_password(client: AsyncClient) -> None:
    """422 javobida foydalanuvchi yuborgan parol qaytarilmasligi kerak.

    FastAPI'ning standart validatsiya handleri har bir xatoga `input` maydonini
    qo'shadi va u yerda so'rov tanasidagi qiymat aynan turadi. Auth
    endpointlarida bu parolning ochiq matnda javobga (demak proksi log'lari va
    brauzer HAR eksportiga) tushishini anglatadi.
    """
    await complete_setup(client)
    secret = "juda-maxfiy-parol-" + "x" * 200  # max_length=128 dan uzun

    response = await client.post(
        "/api/v1/auth/login",
        json={"login": OWNER_PHONE, "password": secret},
    )

    assert response.status_code == 422
    body = response.text
    assert secret not in body
    assert "input" not in response.json()["detail"][0]
    # Xatoni tushunish uchun kerakli ma'lumot esa qolishi kerak.
    assert response.json()["detail"][0]["loc"] == ["body", "password"]


async def test_validation_error_does_not_echo_new_password(
    client: AsyncClient,
) -> None:
    """Xuddi shu himoya parolni tiklash oqimida ham amal qiladi."""
    await complete_setup(client)
    secret = "qisqa"  # min_length=8 dan kalta

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "hech-qanday", "new_password": secret},
    )

    assert response.status_code == 422
    assert secret not in response.text
