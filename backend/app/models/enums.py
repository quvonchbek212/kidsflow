"""Domen enumlari.

Rollar bazada matn (String) sifatida saqlanadi; qiymatlar shu enum orqali
tekshiriladi. Bu migratsiyani soddalashtiradi va cross-database ishlaydi.
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """Foydalanuvchi rollari (loyiha strukturasi, 3-bo'lim)."""

    OWNER = "OWNER"
    MANAGER = "MANAGER"
    TEACHER = "TEACHER"
    PARENT = "PARENT"


# Filial talab qilinmaydigan (global) rollar. Boshqa barcha rollar uchun
# `branch_id` majburiy (5.2-bo'lim qoidasi).
BRANCHLESS_ROLES: frozenset[Role] = frozenset({Role.OWNER})


class Gender(StrEnum):
    """Bola jinsi (5.3-bo'lim, ixtiyoriy)."""

    MALE = "MALE"
    FEMALE = "FEMALE"


class GuardianRelationship(StrEnum):
    """Vasiyning bolaga aloqasi (4.2-bo'lim: ota, ona, qarindosh, boshqa)."""

    FATHER = "FATHER"
    MOTHER = "MOTHER"
    RELATIVE = "RELATIVE"
    OTHER = "OTHER"


class EnrollmentStatus(StrEnum):
    """Enrollment holatlari (5.3-bo'lim)."""

    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AttendanceStatus(StrEnum):
    """Davomat holatlari (4.3-bo'lim)."""

    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    EXCUSED = "EXCUSED"
    SICK = "SICK"


class MealStatus(StrEnum):
    """Kunlik hisobotda ovqatlanish holati (4.4-bo'lim)."""

    ATE_WELL = "ATE_WELL"
    ATE_SOME = "ATE_SOME"
    REFUSED = "REFUSED"


class Mood(StrEnum):
    """Kunlik hisobotda kayfiyat (4.4-bo'lim)."""

    HAPPY = "HAPPY"
    CALM = "CALM"
    TIRED = "TIRED"
    SAD = "SAD"
    SICK = "SICK"


class FileScanStatus(StrEnum):
    """Fayl xavfsizlik tekshiruvi holati (11-bo'lim)."""

    PENDING = "PENDING"
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"


class OutboxStatus(StrEnum):
    """Outbox hodisasi holati (9-bo'lim)."""

    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class NotificationStatus(StrEnum):
    """Bildirishnoma holati (5.8-bo'lim)."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationChannel(StrEnum):
    TELEGRAM = "TELEGRAM"


class NotificationType(StrEnum):
    DAILY_REPORT = "DAILY_REPORT"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    CHILD_CHECKED_IN = "CHILD_CHECKED_IN"
    CHILD_SICK = "CHILD_SICK"
    PAYMENT_REMINDER = "PAYMENT_REMINDER"
    DEBT_WARNING = "DEBT_WARNING"
    BIRTHDAY_GREETING = "BIRTHDAY_GREETING"
    BROADCAST = "BROADCAST"


class InvoiceStatus(StrEnum):
    """Invoice holatlari (5.5-bo'lim)."""

    DRAFT = "DRAFT"
    OPEN = "OPEN"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class PaymentStatus(StrEnum):
    """To'lov holatlari (5.5-bo'lim)."""

    RECORDED = "RECORDED"
    CONFIRMED = "CONFIRMED"
    REVERSED = "REVERSED"
    REFUNDED = "REFUNDED"


class PaymentMethod(StrEnum):
    """To'lov usuli (MVP: Payme/Click yo'q — qo'lda kiritiladi)."""

    CASH = "CASH"
    CARD = "CARD"
    TERMINAL = "TERMINAL"
    BANK = "BANK"
    OTHER = "OTHER"


class AdjustmentType(StrEnum):
    """Invoice tuzatmasi turi (5.5-bo'lim)."""

    DISCOUNT = "DISCOUNT"  # chegirma — to'lanadigan summani kamaytiradi
    SURCHARGE = "SURCHARGE"  # qo'shimcha — summani oshiradi
    WRITE_OFF = "WRITE_OFF"  # qarzni kechirish — kamaytiradi


class ExpenseStatus(StrEnum):
    """Xarajat holati (5.6-bo'lim)."""

    RECORDED = "RECORDED"
    REVERSED = "REVERSED"


class PayrollStatus(StrEnum):
    """Oylik hisob-kitobi holati (7-bosqich B: payroll kengaytmasi)."""

    RECORDED = "RECORDED"
    REVERSED = "REVERSED"


class AIFeature(StrEnum):
    """AI foydalanish turlari (10-bo'lim, ai_usage_logs.feature)."""

    DAILY_REPORT = "DAILY_REPORT"
    FINANCE_NARRATIVE = "FINANCE_NARRATIVE"
    PARENT_ASSISTANT = "PARENT_ASSISTANT"
    OCR = "OCR"
    TRANSLATION = "TRANSLATION"


class KnowledgeCategory(StrEnum):
    """Parent yordamchi RAG manba turlari (10.2-bo'lim)."""

    RULES = "RULES"
    WORKING_HOURS = "WORKING_HOURS"
    MEAL_SCHEDULE = "MEAL_SCHEDULE"
    PRICING = "PRICING"
    EVENTS = "EVENTS"
    OTHER = "OTHER"


class StaffPosition(StrEnum):
    """Xodim lavozimi — faqat ko'rsatish/guruhlash uchun, RBAC rolidan mustaqil.

    Kadrlar bo'limida xodimlar shu bo'yicha guruhlanadi (Manager/Tarbiyachi/
    Oshpaz/Farrosh/Hamshira/Yordamchi). RBAC ruxsatlari `Role` orqali
    (OWNER/MANAGER/TEACHER/PARENT) belgilanadi — lavozim faqat yorliq.
    """

    MANAGER = "MANAGER"
    TEACHER = "TEACHER"
    COOK = "COOK"
    CLEANER = "CLEANER"
    NURSE = "NURSE"
    ASSISTANT = "ASSISTANT"


class EmploymentType(StrEnum):
    """Xodimning ish turi (kadrlar bo'limi kengaytmasi)."""

    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    HOURLY = "HOURLY"


class DiscountType(StrEnum):
    """Bolaning doimiy (standing) chegirma turi (5.3-bo'lim kengaytmasi).

    Enrollment darajasida saqlanadi va invoice generatsiyasida avtomatik
    `InvoiceAdjustment(DISCOUNT)` sifatida qo'llanadi.
    """

    NONE = "NONE"
    SIBLING = "SIBLING"
    STAFF_CHILD = "STAFF_CHILD"
    SOCIAL = "SOCIAL"
    OTHER = "OTHER"


class StockMovementType(StrEnum):
    """Ombor harakati turi (kirim/chiqim)."""

    IN = "IN"
    OUT = "OUT"


class StockMovementReason(StrEnum):
    """Ombor harakati sababi."""

    PURCHASE = "PURCHASE"  # xarid (kirim)
    CONSUMPTION = "CONSUMPTION"  # ovqat tayyorlashda sarf (chiqim)
    ADJUSTMENT = "ADJUSTMENT"  # inventarizatsiya tuzatmasi
    WASTE = "WASTE"  # yaroqsiz/isrof (chiqim)
