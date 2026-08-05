"""API v1 asosiy routeri.

1-bosqich: health, setup, auth, branches, users.
2-bosqich: children, groups, enrollments, attendance, telegram.
Keyingi bosqichlarda daily_reports, invoices va boshqalar qo'shiladi (6-bo'lim).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    analytics,
    attendance,
    auth,
    billing,
    branches,
    children,
    daily_reports,
    enrollments,
    expenses,
    files,
    food,
    groups,
    health,
    messages,
    payments,
    payroll,
    settings,
    setup,
    telegram,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(setup.router)
api_router.include_router(auth.router)
api_router.include_router(branches.router)
api_router.include_router(users.router)
api_router.include_router(children.router)
api_router.include_router(groups.router)
api_router.include_router(enrollments.router)
api_router.include_router(attendance.router)
api_router.include_router(daily_reports.router)
api_router.include_router(files.router)
api_router.include_router(billing.router)
api_router.include_router(payments.router)
api_router.include_router(expenses.router)
api_router.include_router(food.router)
api_router.include_router(analytics.router)
api_router.include_router(ai.router)
api_router.include_router(telegram.router)
api_router.include_router(payroll.router)
api_router.include_router(settings.router)
api_router.include_router(messages.router)
