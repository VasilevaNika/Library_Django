"""extra demo users and books

Revision ID: f0a1b2c3d4e5
Revises: ee11aa22bb33
Create Date: 2026-04-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, None] = "ee11aa22bb33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.bulk_insert(
        sa.table("library_users", sa.column("id", sa.Integer)),
        [{"id": 100}, {"id": 101}],
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
                "id": 6,
                "title": "Евгений Онегин",
                "author": "Александр Пушкин",
                "author_id": 5,
                "genre_id": 1,
                "genre_name": "Классика",
                "year": 1833,
                "cover": None,
                "rating": 4.6,
                "rating_count": 1200,
            },
            {
                "id": 7,
                "title": "Собачье сердце",
                "author": "Михаил Булгаков",
                "author_id": 3,
                "genre_id": 1,
                "genre_name": "Классика",
                "year": 1925,
                "cover": None,
                "rating": 4.7,
                "rating_count": 2100,
            },
        ],
    )
    op.execute(
        sa.text(
            "SELECT setval('books_id_seq', (SELECT COALESCE(MAX(id), 1) FROM books))"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM books WHERE id IN (6, 7)"))
    op.execute(sa.text("DELETE FROM library_users WHERE id IN (100, 101)"))
    op.execute(
        sa.text(
            "SELECT setval('books_id_seq', (SELECT COALESCE(MAX(id), 1) FROM books))"
        )
    )
