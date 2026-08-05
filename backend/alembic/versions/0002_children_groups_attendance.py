"""2-bosqich: bolalar, guruhlar, enrollment, davomat, taklif kodlari

Revision ID: 0002_operations
Revises: 0001_initial
Create Date: 2026-07-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_operations"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "children",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(16), nullable=True),
        sa.Column("medical_notes_encrypted", sa.String(2048), nullable=True),
        sa.Column("photo_file_id", sa.Uuid(), nullable=True),
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
    )

    op.create_table(
        "child_guardians",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("guardian_user_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(16), nullable=False),
        sa.Column(
            "is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "can_pick_up", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "receives_notifications",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guardian_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "child_id", "guardian_user_id", name="uq_child_guardian_pair"
        ),
    )
    op.create_index("ix_child_guardians_child_id", "child_guardians", ["child_id"])
    op.create_index(
        "ix_child_guardians_guardian_user_id",
        "child_guardians",
        ["guardian_user_id"],
    )

    op.create_table(
        "groups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("min_age_months", sa.Integer(), nullable=True),
        sa.Column("max_age_months", sa.Integer(), nullable=True),
        sa.Column(
            "capacity", sa.Integer(), nullable=False, server_default=sa.text("20")
        ),
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
        sa.CheckConstraint("capacity > 0", name="ck_groups_capacity_positive"),
        sa.CheckConstraint(
            "min_age_months IS NULL OR max_age_months IS NULL "
            "OR min_age_months <= max_age_months",
            name="ck_groups_age_range",
        ),
    )
    op.create_index("ix_groups_branch_id", "groups", ["branch_id"])

    op.create_table(
        "group_teachers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("teacher_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_group_teachers_group_id", "group_teachers", ["group_id"])
    op.create_index(
        "ix_group_teachers_teacher_user_id", "group_teachers", ["teacher_user_id"]
    )

    op.create_table(
        "enrollments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="PLANNED",
        ),
        sa.Column("fee_plan_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
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
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_enrollments_date_range",
        ),
    )
    op.create_index("ix_enrollments_child_id", "enrollments", ["child_id"])
    op.create_index("ix_enrollments_branch_id", "enrollments", ["branch_id"])
    op.create_index("ix_enrollments_group_id", "enrollments", ["group_id"])
    # Bir bolada faqat bitta ACTIVE enrollment (partial unique index).
    op.create_index(
        "uq_enrollments_one_active_per_child",
        "enrollments",
        ["child_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        sqlite_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "attendance",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("marked_by", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["marked_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "child_id", "attendance_date", name="uq_attendance_child_date"
        ),
        sa.CheckConstraint(
            "check_out_at IS NULL OR check_in_at IS NULL "
            "OR check_out_at >= check_in_at",
            name="ck_attendance_checkout_after_checkin",
        ),
    )
    op.create_index("ix_attendance_branch_id", "attendance", ["branch_id"])
    op.create_index("ix_attendance_child_id", "attendance", ["child_id"])
    op.create_index("ix_attendance_attendance_date", "attendance", ["attendance_date"])

    op.create_table(
        "telegram_invitations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("code_hash", name="uq_telegram_invitations_code_hash"),
    )
    op.create_index(
        "ix_telegram_invitations_user_id", "telegram_invitations", ["user_id"]
    )


def downgrade() -> None:
    op.drop_table("telegram_invitations")
    op.drop_table("attendance")
    op.drop_index("uq_enrollments_one_active_per_child", table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_table("group_teachers")
    op.drop_table("groups")
    op.drop_table("child_guardians")
    op.drop_table("children")
