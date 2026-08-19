"""HTTP sarlavhalarini xavfsiz yig'ish."""

from __future__ import annotations

import unicodedata
from urllib.parse import quote

# Sarlavha qiymatida qolmasligi kerak bo'lgan belgilar: qo'shtirnoq qiymatni
# erta yopadi, teskari chiziq esa ekranlash sifatida o'qiladi.
_UNSAFE_IN_HEADER = frozenset('"\\')


def content_disposition(original_name: str, *, disposition: str = "inline") -> str:
    """`Content-Disposition` sarlavhasini xavfsiz yig'adi.

    Fayl nomini to'g'ridan-to'g'ri qo'yib bo'lmaydi: u foydalanuvchi kiritadigan
    qiymat. Ichida qo'shtirnoq bo'lsa sarlavha buziladi va yuklab olish ishdan
    chiqadi; boshqaruv belgilari esa sarlavha kiritishga urinish bo'ladi.

    Ikki shakl beriladi (RFC 6266):

    - `filename=` — faqat ASCII, xavfli belgilar olib tashlangan zaxira nom.
      Eski mijozlar shuni o'qiydi.
    - `filename*=UTF-8''…` — to'liq nom, foizli kodlangan. Zamonaviy brauzerlar
      buni afzal ko'radi, ya'ni o'zbekcha va ruscha nomlar to'g'ri ko'rinadi
      (ilgari ular ASCII ga tushib, tanib bo'lmas holga kelardi).
    """
    folded = (
        unicodedata.normalize("NFKD", original_name)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    ascii_name = "".join(
        ch for ch in folded if ch.isprintable() and ch not in _UNSAFE_IN_HEADER
    ).strip()
    if not ascii_name:
        ascii_name = "file"

    quoted = quote(original_name, safe="")
    return f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{quoted}"
