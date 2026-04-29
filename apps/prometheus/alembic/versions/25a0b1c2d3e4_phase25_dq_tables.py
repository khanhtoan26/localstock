"""phase25 dq tables — quarantine_rows + pipeline_runs.stats

Revision ID: 25a0b1c2d3e4
Revises: 24a1b2c3d4e5
Create Date: 2026-04-29 12:00:00.000000

Phase 25 D-02 + D-07. Adds ``quarantine_rows`` polymorphic table for
rejected OHLCV / financial / indicator rows (30-day retention via APScheduler
cron in 25-03) and ``pipeline_runs.stats JSONB`` for the
succeeded/failed/skipped/failed_symbols dict (dual-write helper in 25-04).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "25a0b1c2d3e4"
down_revision: Union[str, None] = "24a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- D-02: quarantine_rows polymorphic table ---
    op.create_table(
        "quarantine_rows",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(16), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("rule", sa.String(64), nullable=False),
        sa.Column("tier", sa.String(16), nullable=False),
        sa.Column(
            "quarantined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_quarantine_rows_source_qa",
        "quarantine_rows",
        ["source", "quarantined_at"],
    )
    op.create_index(
        "ix_quarantine_rows_symbol",
        "quarantine_rows",
        ["symbol"],
    )

    # --- D-07: pipeline_runs.stats JSONB (nullable; dual-write in 25-04) ---
    op.add_column(
        "pipeline_runs",
        sa.Column(
            "stats",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("pipeline_runs", "stats")
    op.drop_index("ix_quarantine_rows_symbol", table_name="quarantine_rows")
    op.drop_index("ix_quarantine_rows_source_qa", table_name="quarantine_rows")
    op.drop_table("quarantine_rows")
