"""`Content-Disposition` sarlavhasini xavfsiz yig'ish.

Ilgari fayl nomi sarlavhaga to'g'ridan-to'g'ri qo'yilardi — nomida qo'shtirnoq
bo'lsa sarlavha buzilardi, kirill/lotin diakritikasi esa yo'qolardi.
"""

from __future__ import annotations

from app.utils.http_headers import content_disposition


def test_plain_ascii_name() -> None:
    header = content_disposition("hisobot.pdf")
    assert 'filename="hisobot.pdf"' in header
    assert "filename*=UTF-8''hisobot.pdf" in header


def test_quote_in_name_does_not_break_header() -> None:
    """Asosiy tekshiruv: qo'shtirnoq qiymatni erta yopmasligi kerak."""
    header = content_disposition('a"b.pdf')
    ascii_part = header.split('filename="')[1].split('"')[0]
    assert '"' not in ascii_part
    # To'liq nom kodlangan shaklda saqlanadi.
    assert "%22" in header


def test_control_characters_are_stripped() -> None:
    """Yangi qator sarlavha kiritishga urinish bo'lardi."""
    header = content_disposition("a\r\nX-Injected: 1.pdf")
    assert "\r" not in header
    assert "\n" not in header
    ascii_part = header.split('filename="')[1].split('"')[0]
    assert "X-Injected" not in ascii_part or ":" not in ascii_part.split("X-Injected")[0]


def test_backslash_is_stripped() -> None:
    header = content_disposition("a\\b.pdf")
    ascii_part = header.split('filename="')[1].split('"')[0]
    assert "\\" not in ascii_part


def test_cyrillic_name_survives_in_utf8_form() -> None:
    """Ruscha nom ASCII qismida yo'qoladi, lekin UTF-8 shaklida saqlanadi."""
    header = content_disposition("отчёт.pdf")
    assert "filename*=UTF-8''" in header
    assert "%D0%BE" in header  # "о" harfi


def test_name_with_no_ascii_gets_fallback() -> None:
    """Butunlay ASCII'siz nom bo'sh qolmasligi kerak."""
    header = content_disposition("отчёт")
    assert 'filename="file"' in header


def test_uzbek_apostrophe_name() -> None:
    header = content_disposition("o'quvchi ro'yxati.pdf")
    assert "filename*=UTF-8''" in header
    assert 'filename="' in header
