"""4-bosqich: moliya — tarif, invoice, to'lov, tuzatma va xarajat

Revision ID: 0004_finance
Revises: 0003_reports
Create Date: 2026-07-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_finance"
down_revision: str | None = "0003_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MONEY = sa.Numeric(18, 2)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "fee_plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("monthly_amount", _MONEY, nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="UZS"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_fee_plans_branch_id", "fee_plans", ["branch_id"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=True),
        sa.Column("billing_period", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("original_amount", _MONEY, nullable=False),
        sa.Column("discount_amount", _MONEY, nullable=False, server_default="0"),
        sa.Column("adjusted_amount", _MONEY, nullable=False),
        sa.Column("paid_amount", _MONEY, nullable=False, server_default="0"),
        sa.Column("outstanding_amount", _MONEY, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="OPEN"),
        *_timestamps(),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["enrollments.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "child_id", "billing_period", name="uq_invoice_child_period"
        ),
    )
    op.create_index("ix_invoices_branch_id", "invoices", ["branch_id"])
    op.create_index("ix_invoices_child_id", "invoices", ["child_id"])
    op.create_index("ix_invoices_billing_period", "invoices", ["billing_period"])
    op.create_index("ix_invoices_status", "invoices", ["status"])

    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("amount", _MONEY, nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="UZS"),
        sa.Column("payment_method", sa.String(16), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("receipt_file_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="RECORDED"),
        sa.Column("recorded_by", sa.Uuid(), nullable=True),
        sa.Column("reversed_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(64), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receipt_file_id"], ["files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["reversed_transaction_id"],
            ["payment_transactions.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_payment_idempotency_key"),
    )
    op.create_index(
        "ix_payment_transactions_branch_id", "payment_transactions", ["branch_id"]
    )
    op.create_index(
        "ix_payment_transactions_child_id", "payment_transactions", ["child_id"]
    )
    op.create_index(
        "ix_payment_transactions_status", "payment_transactions", ["status"]
    )

    op.create_table(
        "payment_allocations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("payment_transaction_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("amount", _MONEY, nullable=False),
        sa.ForeignKeyConstraint(
            ["payment_transaction_id"],
            ["payment_transactions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_payment_allocations_payment_transaction_id",
        "payment_allocations",
        ["payment_transaction_id"],
    )
    op.create_index(
        "ix_payment_allocations_invoice_id",
        "payment_allocations",
        ["invoice_id"],
    )

    op.create_table(
        "invoice_adjustments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("adjustment_type", sa.String(16), nullable=False),
        sa.Column("amount", _MONEY, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_invoice_adjustments_invoice_id",
        "invoice_adjustments",
        ["invoice_id"],
    )

    op.create_table(
        "expense_categories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column(
            "is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        *_timestamps(),
        sa.UniqueConstraint("name", name="uq_expense_category_name"),
    )

    op.create_table(
        "expenses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("amount", _MONEY, nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="UZS"),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("vendor", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("receipt_file_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="RECORDED"),
        sa.Column("recorded_by", sa.Uuid(), nullable=True),
        sa.Column("reversed_expense_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["category_id"], ["expense_categories.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["receipt_file_id"], ["files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["reversed_expense_id"], ["expenses.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_expenses_branch_id", "expenses", ["branch_id"])
    op.create_index("ix_expenses_expense_date", "expenses", ["expense_date"])
    op.create_index("ix_expenses_status", "expenses", ["status"])


def downgrade() -> None:
    op.drop_table("expenses")
    op.drop_table("expense_categories")
    op.drop_table("invoice_adjustments")
    op.drop_table("payment_allocations")
    op.drop_table("payment_transactions")
    op.drop_table("invoices")
    op.drop_table("fee_plans")
