"""add phase11 admin tables

Revision ID: f11a1b2c3d4e
Revises: b5c6d7e8f901
Create Date: 2026-07-17 10:00:00.000000

Adds is_tracked column to stocks table (D-03) and creates admin_jobs table (D-02)
for Phase 11 Admin API Endpoints.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f11a1b2c3d4e"
down_revision: Union[str, None] = "b5c6d7e8f901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_tracked to stocks table (D-03, with server_default for existing rows)
    op.add_column(
        "stocks",
        sa.Column("is_tracked", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )

    # Create admin_jobs table (D-02)
    op.create_table(
        "admin_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_jobs_status", "admin_jobs", ["status"])
    op.create_index("ix_admin_jobs_created_at", "admin_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_admin_jobs_created_at", table_name="admin_jobs")
    op.drop_index("ix_admin_jobs_status", table_name="admin_jobs")
    op.drop_table("admin_jobs")
    op.drop_column("stocks", "is_tracked")
