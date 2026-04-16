"""add FK constraint on sentiment_scores.article_id

Revision ID: 823bee92cc2e
Revises: c4007f49f9a7
Create Date: 2026-04-16 10:08:13.245422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '823bee92cc2e'
down_revision: Union[str, None] = 'c4007f49f9a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_sentiment_scores_article_id",
        "sentiment_scores",
        "news_articles",
        ["article_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_sentiment_scores_article_id",
        "sentiment_scores",
        type_="foreignkey",
    )
