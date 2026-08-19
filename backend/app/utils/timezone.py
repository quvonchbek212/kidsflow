"""Mahalliy taqvim sanasi (5-bo'lim: UTC saqlanadi, mahalliy vaqtda ko'rsatiladi).

Vaqt nuqtalari (`created_at`, `sent_at`, token muddati va h.k.) doim UTC da
saqlanadi — buni o'zgartirish kerak emas. Ammo *taqvim* savollari ("bugun qaysi
kun?", "shu oy qachon boshlandi?") mahalliy vaqt zonasida hisoblanishi shart.

`date.today()` konteynerning vaqt zonasini oladi, u esa UTC. Toshkent UTC+5
bo'lgani uchun har kuni soat 00:00 dan 05:00 gacha server hali kechagi kunni
"bugun" deb bilardi: kunlik bildirishnomalar noto'g'ri kunga tushardi, qarzdorlik
yoshi bir kun surilardi, brauzer esa (mahalliy sanani yuborib) backend bilan
kelishmay qolardi.

Shu sababli taqvim hisoblari uchun `date.today()` o'rniga shu moduldagi
`today_local()` ishlatiladi.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import get_settings


def local_zone() -> tzinfo:
    """Sozlamalardagi vaqt zonasi.

    Noto'g'ri zona nomi yozilgan bo'lsa ilova yiqilmaydi — UTC ga qaytadi.
    Sana bir kunga adashishi mumkin, lekin bu butun tizim to'xtashidan afzal.

    Zaxira sifatida `ZoneInfo("UTC")` emas, `datetime.UTC` qaytariladi: zona
    bazasi umuman topilmagan muhitda (Windows, ba'zi slim/alpine image'lar)
    `ZoneInfo("UTC")` ning o'zi ham `ZoneInfoNotFoundError` beradi va zaxira
    yo'li ham yiqilardi. `datetime.UTC` hech qanday tashqi bazaga tayanmaydi.
    Odatdagi holda baza `tzdata` paketi orqali keladi (requirements.txt).
    """
    settings = get_settings()
    try:
        return ZoneInfo(settings.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return UTC


def now_local() -> datetime:
    """Mahalliy vaqt zonasidagi hozirgi payt (zona ma'lumoti bilan)."""
    return datetime.now(UTC).astimezone(local_zone())


def today_local() -> date:
    """Mahalliy vaqt zonasidagi bugungi taqvim sanasi."""
    return now_local().date()


def month_start_local() -> date:
    """Mahalliy vaqt zonasida joriy oyning birinchi kuni."""
    return today_local().replace(day=1)


def month_start_utc() -> datetime:
    """Mahalliy oy boshlangan payt, UTC da ifodalangan.

    Bazadagi vaqt ustunlari UTC da saqlanadi, shuning uchun "shu oyda nechta
    xabar ketdi?" degan savolga javob berish uchun mahalliy oy chegarasini UTC
    nuqtasiga aylantirish kerak. To'g'ridan-to'g'ri `datetime.now(UTC)` dan oy
    boshi olinsa, oyning birinchi kuni 00:00–05:00 orasida hisob o'tgan oyga
    tushib ketardi.
    """
    local_month_start = now_local().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    return local_month_start.astimezone(UTC)
