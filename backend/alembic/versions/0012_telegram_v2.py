"""Telegram bildirishnomalari: filial kesimi, bayramlar, ota-ona yozishmalari.

Uchta yangi jadval:

* `branch_notification_settings` — bildirishnoma kalitlari va eslatma kunlari
  endi HAR FILIAL uchun alohida. Ilgari ular yagona global
  `kindergarten_settings.notification_toggles` da edi, ya'ni bir filialda
  o'chirilgan tur hamma filialda o'chib qolardi. Migratsiya global qiymatni
  har bir filialga nusxalaydi — hozirgi xatti-harakat saqlanadi.
* `holidays` — filial qo'lda kiritadigan bayram/tadbirlar va ularni necha kun
  oldin eslatish.
* `parent_messages` — ota-ona ↔ xodim yozishmalari. `notifications` jadvali
  faqat chiquvchi xabar uchun edi, ota-onadan kelgan savolni saqlaydigan joy
  yo'q edi.

`kindergarten_settings.notification_toggles` o'chirilmaydi (orqaga moslik),
lekin bundan keyin o'qilmaydi.

Revision ID: 0012_telegram_v2
Revises: 0011_login_lockout
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0012_telegram_v2"
down_revision: str | None = "0011_login_lockout"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "branch_notification_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "branch_id",
            sa.Uuid(),
            sa.ForeignKey("branches.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("toggles", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "payment_reminder_days_before",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
        sa.Column(
            "debt_warning_days_late", sa.Integer(), nullable=False, server_default="15"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_branch_notification_settings_branch_id",
        "branch_notification_settings",
        ["branch_id"],
    )

    op.create_table(
        "holidays",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "branch_id",
            sa.Uuid(),
            sa.ForeignKey("branches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("days_before", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "repeats_yearly",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_holidays_branch_id", "holidays", ["branch_id"])
    op.create_index("ix_holidays_holiday_date", "holidays", ["holiday_date"])

    op.create_table(
        "parent_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "branch_id",
            sa.Uuid(),
            sa.ForeignKey("branches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "guardian_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "staff_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_parent_messages_branch_id", "parent_messages", ["branch_id"])
    op.create_index(
        "ix_parent_messages_guardian_user_id", "parent_messages", ["guardian_user_id"]
    )
    op.create_index("ix_parent_messages_created_at", "parent_messages", ["created_at"])
    op.create_index(
        "ix_parent_messages_thread",
        "parent_messages",
        ["branch_id", "guardian_user_id", "created_at"],
    )

    # Har bir filialga sozlama qatori yaratiladi va global kalitlar nusxalanadi.
    # Shu tufayli migratsiyadan keyin xatti-harakat aynan avvalgidek qoladi.
    op.execute(
        """
        INSERT INTO branch_notification_settings (id, branch_id, toggles)
        SELECT gen_random_uuid(),
               b.id,
               COALESCE(
                   (SELECT s.notification_toggles
                      FROM kindergarten_settings s
                     LIMIT 1),
                   '{}'::json
               )
          FROM branches b
        """
    )


def downgrade() -> None:
    op.drop_table("parent_messages")
    op.drop_index("ix_holidays_holiday_date", table_name="holidays")
    op.drop_index("ix_holidays_branch_id", table_name="holidays")
    op.drop_table("holidays")
    op.drop_index(
        "ix_branch_notification_settings_branch_id",
        table_name="branch_notification_settings",
    )
    op.drop_table("branch_notification_settings")
