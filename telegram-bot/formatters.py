"""Backend javoblarini o'qiladigan matnga aylantiruvchi yordamchilar."""

from __future__ import annotations

_STATUS_UZ = {
    "PRESENT": "✅ Keldi",
    "ABSENT": "❌ Kelmadi",
    "LATE": "🕐 Kechikdi",
    "EXCUSED": "📄 Sababli",
    "SICK": "🤒 Kasal",
}
_MEAL_UZ = {
    "ATE_WELL": "yaxshi ovqatlandi",
    "ATE_SOME": "biroz ovqatlandi",
    "REFUSED": "ovqatdan bosh tortdi",
}
_MOOD_UZ = {
    "HAPPY": "quvnoq",
    "CALM": "xotirjam",
    "TIRED": "charchagan",
    "SAD": "xafa",
    "SICK": "betob",
}
_INVOICE_UZ = {
    "OPEN": "To'lanmagan",
    "PARTIALLY_PAID": "Qisman to'langan",
    "PAID": "To'langan",
    "OVERDUE": "Muddati o'tgan",
    "CANCELLED": "Bekor qilingan",
    "DRAFT": "Qoralama",
}


def format_attendance(items: list[dict]) -> str:
    if not items:
        return "Davomat yozuvi yo'q."
    lines = ["📋 So'nggi davomat:"]
    for item in items[:10]:
        status = _STATUS_UZ.get(item["status"], item["status"])
        lines.append(f"• {item['attendance_date']}: {status}")
    return "\n".join(lines)


def format_reports(items: list[dict]) -> str:
    published = [r for r in items if r.get("is_published")]
    if not published:
        return "E'lon qilingan hisobot yo'q."
    lines = ["📝 So'nggi hisobotlar:"]
    for report in published[:5]:
        parts = [f"📅 {report['report_date']}"]
        if report.get("final_summary"):
            parts.append(report["final_summary"])
        else:
            if report.get("meal_status"):
                parts.append(_MEAL_UZ.get(report["meal_status"], report["meal_status"]))
            if report.get("mood"):
                parts.append(f"kayfiyat: {_MOOD_UZ.get(report['mood'], report['mood'])}")
        lines.append(" — ".join(parts))
    return "\n\n".join(lines)


def format_invoices(items: list[dict]) -> str:
    if not items:
        return "To'lov hisob-fakturasi yo'q."
    lines = ["💰 To'lovlar holati:"]
    for inv in items[:6]:
        status = _INVOICE_UZ.get(inv["status"], inv["status"])
        outstanding = inv.get("outstanding_amount", "0")
        lines.append(
            f"• {inv['billing_period']}: {status} "
            f"(qoldiq: {outstanding} so'm)"
        )
    return "\n".join(lines)
