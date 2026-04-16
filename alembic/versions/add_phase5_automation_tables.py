"""add phase5 automation tables

Revision ID: b5c6d7e8f901
Revises: 823bee92cc2e, a1b2c3d4e5f6
Create Date: 2026-04-16 07:45:00.000000

Merge migration: combines FK constraint and Phase 4 macro/report heads,
then adds Phase 5 automation tables (score_change_alerts, sector_snapshots,
notification_logs).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b5c6d7e8f901"
down_revision: Union[str, tuple[str, ...], None] = ("823bee92cc2e", "a1b2c3d4e5f6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- score_change_alerts ---
    op.create_table(
        "score_change_alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("previous_score", sa.Float(), nullable=False),
        sa.Column("current_score", sa.Float(), nullable=False),
        sa.Column("delta", sa.Float(), nullable=False),
        sa.Column("previous_grade", sa.String(length=2), nullable=False),
        sa.Column("current_grade", sa.String(length=2), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("notified", sa.Boolean(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "date", name="uq_score_change_alert"),
    )
    op.create_index(
        op.f("ix_score_change_alerts_symbol"), "score_change_alerts", ["symbol"], unique=False
    )
    op.create_index(
        op.f("ix_score_change_alerts_date"), "score_change_alerts", ["date"], unique=False
    )

    # --- sector_snapshots ---
    op.create_table(
        "sector_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("group_code", sa.String(length=20), nullable=False),
        sa.Column("avg_score", sa.Float(), nullable=False),
        sa.Column("avg_volume", sa.Float(), nullable=False),
        sa.Column("total_volume", sa.BigInteger(), nullable=False),
        sa.Column("stock_count", sa.Integer(), nullable=False),
        sa.Column("avg_score_change", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", "group_code", name="uq_sector_snapshot"),
    )
    op.create_index(
        op.f("ix_sector_snapshots_date"), "sector_snapshots", ["date"], unique=False
    )
    op.create_index(
        op.f("ix_sector_snapshots_group_code"), "sector_snapshots", ["group_code"], unique=False
    )

    # --- notification_logs ---
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("notification_type", sa.String(length=30), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", "notification_type", name="uq_notification_log"),
    )
    op.create_index(
        op.f("ix_notification_logs_date"), "notification_logs", ["date"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_logs_date"), table_name="notification_logs")
    op.drop_table("notification_logs")
    op.drop_index(op.f("ix_sector_snapshots_group_code"), table_name="sector_snapshots")
    op.drop_index(op.f("ix_sector_snapshots_date"), table_name="sector_snapshots")
    op.drop_table("sector_snapshots")
    op.drop_index(op.f("ix_score_change_alerts_date"), table_name="score_change_alerts")
    op.drop_index(op.f("ix_score_change_alerts_symbol"), table_name="score_change_alerts")
    op.drop_table("score_change_alerts")
