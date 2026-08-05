"""Invoice pul hisob-kitobi uchun unit testlar (4.7, 5.5-bo'lim)."""

from __future__ import annotations

from decimal import Decimal

from app.services.invoice_math import compute_totals


def _d(value: str) -> Decimal:
    return Decimal(value)


def test_unpaid_invoice_is_open() -> None:
    t = compute_totals(_d("500000"), [], _d("0"))
    assert t.adjusted_amount == _d("500000.00")
    assert t.outstanding_amount == _d("500000.00")
    assert t.status == "OPEN"


def test_partial_payment() -> None:
    t = compute_totals(_d("500000"), [], _d("200000"))
    assert t.outstanding_amount == _d("300000.00")
    assert t.status == "PARTIALLY_PAID"


def test_full_payment() -> None:
    t = compute_totals(_d("500000"), [], _d("500000"))
    assert t.outstanding_amount == _d("0.00")
    assert t.status == "PAID"


def test_overpayment_clamps_outstanding_to_zero() -> None:
    t = compute_totals(_d("500000"), [], _d("600000"))
    assert t.outstanding_amount == _d("0.00")
    assert t.status == "PAID"


def test_discount_reduces_adjusted() -> None:
    t = compute_totals(_d("500000"), [("DISCOUNT", _d("100000"))], _d("0"))
    assert t.discount_amount == _d("100000.00")
    assert t.adjusted_amount == _d("400000.00")
    assert t.status == "OPEN"


def test_write_off_full_settles_invoice() -> None:
    t = compute_totals(_d("500000"), [("WRITE_OFF", _d("500000"))], _d("0"))
    assert t.adjusted_amount == _d("0.00")
    assert t.outstanding_amount == _d("0.00")
    assert t.status == "PAID"


def test_surcharge_increases_adjusted() -> None:
    t = compute_totals(_d("500000"), [("SURCHARGE", _d("50000"))], _d("0"))
    assert t.adjusted_amount == _d("550000.00")


def test_adjusted_never_negative() -> None:
    t = compute_totals(_d("100000"), [("DISCOUNT", _d("200000"))], _d("0"))
    assert t.adjusted_amount == _d("0.00")


def test_cancelled_status() -> None:
    t = compute_totals(_d("500000"), [], _d("0"), cancelled=True)
    assert t.status == "CANCELLED"
