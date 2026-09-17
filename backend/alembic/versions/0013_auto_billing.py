"""Avtomatik oylik hisob-faktura: filial bo'yicha to'lov muddati.

Hisob-fakturalar endi qo'lda ("Hisob-faktura yaratish" tugmasi) emas, worker
tomonidan har oy avtomatik yaratiladi. Qo'lda yaratishda to'lov muddati
formada tanlanardi — endi u filial sozlamasida saqlanadi (sukut bo'yicha
har oyning 10-sanasi, avvalgi formadagi standart qiymat).

Revision ID: 0013_auto_billing
Revises: 0012_telegram_v2
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0013_auto_billing"
down_revision: str | None = "0012_telegram_v2"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "branch_notification_settings",
        sa.Column("invoice_due_day", sa.Integer(), nullable=False, server_default="10"),
    )


def downgrade() -> None:
    op.drop_column("branch_notification_settings", "invoice_due_day")
