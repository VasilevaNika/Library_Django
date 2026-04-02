"""second demo user, extra books for CRUD demo

Revision ID: ee11aa22bb33
Revises: c4f8a21b9030
Create Date: 2026-03-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ee11aa22bb33"
down_revision: Union[str, Sequence[str], None] = "c4f8a21b9030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.bulk_insert(
        sa.table("library_users", sa.column("id", sa.Integer)),
        [{"id": 7}],
    )

    books = sa.table(
        "books",
        sa.column("id", sa.Integer),
        sa.column("title", sa.String),
        sa.column("author", sa.String),
        sa.column("author_id", sa.Integer),
        sa.column("genre_id", sa.Integer),
        sa.column("genre_name", sa.String),
        sa.column("year", sa.Integer),
        sa.column("cover", sa.String),
        sa.column("rating", sa.Float),
        sa.column("rating_count", sa.Integer),
    )
    op.bulk_insert(
        books,
        [
            {
                "id": 4,
                "title": "1984",
                "author": "Джордж Оруэлл",
                "author_id": 4,
                "genre_id": 2,
                "genre_name": "Антиутопия",
                "year": 1949,
                "cover": None,
                "rating": 4.6,
                "rating_count": 4100,
            },
            {
                "id": 5,
                "title": "Анна Каренина",
                "author": "Лев Толстой",
                "author_id": 1,
                "genre_id": 1,
                "genre_name": "Классика",
                "year": 1877,
                "cover": None,
                "rating": 4.5,
                "rating_count": 980,
            },
        ],
    )
    op.execute(
        sa.text(
            "SELECT setval('books_id_seq', (SELECT COALESCE(MAX(id), 1) FROM books))"
        )
    )

    op.bulk_insert(
        sa.table(
            "ignored_books",
            sa.column("user_id", sa.Integer),
            sa.column("book_id", sa.Integer),
            sa.column("reason", sa.String),
        ),
        [{"user_id": 7, "book_id": 1, "reason": "not_interesting"}],
    )

    op.bulk_insert(
        sa.table(
            "reading_list_entries",
            sa.column("user_id", sa.Integer),
            sa.column("book_id", sa.Integer),
            sa.column("priority", sa.String),
        ),
        [
            {"user_id": 7, "book_id": 4, "priority": "high"},
            {"user_id": 7, "book_id": 5, "priority": "low"},
        ],
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM reading_list_entries WHERE user_id = 7"))
    op.execute(sa.text("DELETE FROM ignored_books WHERE user_id = 7"))
    op.execute(sa.text("DELETE FROM books WHERE id IN (4, 5)"))
    op.execute(sa.text("DELETE FROM library_users WHERE id = 7"))
    op.execute(
        sa.text(
            "SELECT setval('books_id_seq', (SELECT COALESCE(MAX(id), 1) FROM books))"
        )
    )
