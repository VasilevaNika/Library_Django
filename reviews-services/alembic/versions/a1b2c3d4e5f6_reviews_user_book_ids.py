"""reviews user_id book_id for cross-service links

Revision ID: a1b2c3d4e5f6
Revises: 1f0a8f4d8b2c
Create Date: 2026-04-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "1f0a8f4d8b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reviews",
        sa.Column("user_id", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "reviews",
        sa.Column("book_id", sa.Integer(), nullable=True),
    )
    op.create_index(op.f("ix_reviews_user_id"), "reviews", ["user_id"], unique=False)
    op.create_index(op.f("ix_reviews_book_id"), "reviews", ["book_id"], unique=False)
    op.alter_column("reviews", "user_id", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_reviews_book_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_user_id"), table_name="reviews")
    op.drop_column("reviews", "book_id")
    op.drop_column("reviews", "user_id")
