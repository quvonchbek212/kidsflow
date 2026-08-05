"""Oziq-ovqat va oshxona ombori: mahsulotlar, ovqat menyusi, ombor harakati

Revision ID: 0007_food
Revises: 0006_payroll
Create Date: 2026-07-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_food"
down_revision: str | None = "0006_payroll"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_QTY = sa.Numeric(18, 3)
_MONEY = sa.Numeric(18, 2)


def upgrade() -> None:
    op.create_table(
        "food_products",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("unit", sa.String(16), nullable=False),
        sa.Column("unit_cost", _MONEY, nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
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
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("branch_id", "name", name="uq_food_product_branch_name"),
    )
    op.create_index("ix_food_products_branch_id", "food_products", ["branch_id"])

    op.create_table(
        "meals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
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
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_meals_branch_id", "meals", ["branch_id"])

    op.create_table(
        "meal_ingredients",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("meal_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity_per_serving", _QTY, nullable=False),
        sa.ForeignKeyConstraint(["meal_id"], ["meals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["product_id"], ["food_products.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("meal_id", "product_id", name="uq_meal_ingredient_pair"),
    )
    op.create_index("ix_meal_ingredients_meal_id", "meal_ingredients", ["meal_id"])
    op.create_index(
        "ix_meal_ingredients_product_id", "meal_ingredients", ["product_id"]
    )

    op.create_table(
        "meal_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("meal_id", sa.Uuid(), nullable=False),
        sa.Column("serving_date", sa.Date(), nullable=False),
        sa.Column("servings_count", sa.Integer(), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["meal_id"], ["meals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_meal_logs_branch_id", "meal_logs", ["branch_id"])
    op.create_index("ix_meal_logs_meal_id", "meal_logs", ["meal_id"])
    op.create_index("ix_meal_logs_serving_date", "meal_logs", ["serving_date"])

    op.create_table(
        "food_stock_movements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("movement_type", sa.String(8), nullable=False),
        sa.Column("quantity", _QTY, nullable=False),
        sa.Column("reason", sa.String(16), nullable=False),
        sa.Column("unit_cost", _MONEY, nullable=True),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("meal_log_id", sa.Uuid(), nullable=True),
        sa.Column("recorded_by", sa.Uuid(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["product_id"], ["food_products.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["meal_log_id"], ["meal_logs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_food_stock_movements_branch_id", "food_stock_movements", ["branch_id"]
    )
    op.create_index(
        "ix_food_stock_movements_product_id", "food_stock_movements", ["product_id"]
    )
    op.create_index(
        "ix_food_stock_movements_occurred_at",
        "food_stock_movements",
        ["occurred_at"],
    )


def downgrade() -> None:
    op.drop_table("food_stock_movements")
    op.drop_table("meal_logs")
    op.drop_table("meal_ingredients")
    op.drop_table("meals")
    op.drop_table("food_products")
