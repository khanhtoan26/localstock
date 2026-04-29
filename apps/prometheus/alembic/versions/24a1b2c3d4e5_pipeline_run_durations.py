"""add pipeline_run per-step duration columns

Revision ID: 24a1b2c3d4e5
Revises: f11a1b2c3d4e
Create Date: 2026-04-30 09:00:00.000000

Phase 24 D-07 / OBS-17 — adds 4 nullable Integer columns to pipeline_runs
(crawl_duration_ms, analyze_duration_ms, score_duration_ms, report_duration_ms)
so per-step pipeline timing can be persisted alongside the run row.
Population logic is delivered in 24-06.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "24a1b2c3d4e5"
down_revision: Union[str, None] = "f11a1b2c3d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipeline_runs",
        sa.Column("crawl_duration_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column("analyze_duration_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column("score_duration_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column("report_duration_ms", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipeline_runs", "report_duration_ms")
    op.drop_column("pipeline_runs", "score_duration_ms")
    op.drop_column("pipeline_runs", "analyze_duration_ms")
    op.drop_column("pipeline_runs", "crawl_duration_ms")
