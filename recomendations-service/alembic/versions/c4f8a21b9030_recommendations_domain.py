"""recommendations domain: books, users, ignore & reading lists

Revision ID: c4f8a21b9030
Revises: 02cc4ea1e770
Create Date: 2026-03-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4f8a21b9030"
down_revision: Union[str, Sequence[str], None] = "02cc4ea1e770"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_tasks_id"), table_name="tasks")
    op.drop_table("tasks")

    op.create_table(
        "library_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_library_users_id"), "library_users", ["id"], unique=False)

    op.execute(sa.text("CREATE SEQUENCE books_id_seq"))
    op.create_table(
        "books",
        sa.Column(
            "id",
            sa.Integer(),
            server_default=sa.text("nextval('books_id_seq')"),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("genre_id", sa.Integer(), nullable=True),
        sa.Column("genre_name", sa.String(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("cover", sa.String(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_books_id"), "books", ["id"], unique=False)
    op.create_index(op.f("ix_books_author_id"), "books", ["author_id"], unique=False)
    op.create_index(op.f("ix_books_genre_id"), "books", ["genre_id"], unique=False)
    op.execute(sa.text("ALTER SEQUENCE books_id_seq OWNED BY books.id"))

    op.create_table(
        "ignored_books",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["library_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "book_id", name="uq_ignored_user_book"),
    )
    op.create_index(op.f("ix_ignored_books_user_id"), "ignored_books", ["user_id"], unique=False)
    op.create_index(op.f("ix_ignored_books_book_id"), "ignored_books", ["book_id"], unique=False)

    op.create_table(
        "reading_list_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["library_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "book_id", name="uq_reading_user_book"),
    )
    op.create_index(
        op.f("ix_reading_list_entries_user_id"),
        "reading_list_entries",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reading_list_entries_book_id"),
        "reading_list_entries",
        ["book_id"],
        unique=False,
    )

    op.bulk_insert(
        sa.table("library_users", sa.column("id", sa.Integer)),
        [{"id": 42}],
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
                "id": 1,
                "title": "Война и мир",
                "author": "Лев Толстой",
                "author_id": 1,
                "genre_id": 1,
                "genre_name": "Классика",
                "year": 1869,
                "cover": None,
                "rating": 4.7,
                "rating_count": 2345,
            },
            {
                "id": 2,
                "title": "Преступление и наказание",
                "author": "Фёдор Достоевский",
                "author_id": 2,
                "genre_id": 1,
                "genre_name": "Классика",
                "year": 1866,
                "cover": None,
                "rating": 4.8,
                "rating_count": 1892,
            },
            {
                "id": 3,
                "title": "Мастер и Маргарита",
                "author": "Михаил Булгаков",
                "author_id": 3,
                "genre_id": 1,
                "genre_name": "Классика",
                "year": 1967,
                "cover": None,
                "rating": 4.9,
                "rating_count": 3120,
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
        [{"user_id": 42, "book_id": 3, "reason": "already_read"}],
    )

    op.bulk_insert(
        sa.table(
            "reading_list_entries",
            sa.column("user_id", sa.Integer),
            sa.column("book_id", sa.Integer),
            sa.column("priority", sa.String),
        ),
        [
            {"user_id": 42, "book_id": 1, "priority": "high"},
            {"user_id": 42, "book_id": 2, "priority": "medium"},
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_reading_list_entries_book_id"), table_name="reading_list_entries")
    op.drop_index(op.f("ix_reading_list_entries_user_id"), table_name="reading_list_entries")
    op.drop_table("reading_list_entries")

    op.drop_index(op.f("ix_ignored_books_book_id"), table_name="ignored_books")
    op.drop_index(op.f("ix_ignored_books_user_id"), table_name="ignored_books")
    op.drop_table("ignored_books")

    op.drop_index(op.f("ix_books_genre_id"), table_name="books")
    op.drop_index(op.f("ix_books_author_id"), table_name="books")
    op.drop_index(op.f("ix_books_id"), table_name="books")
    op.drop_table("books")
    op.execute(sa.text("DROP SEQUENCE IF EXISTS books_id_seq"))

    op.drop_index(op.f("ix_library_users_id"), table_name="library_users")
    op.drop_table("library_users")

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_id"), "tasks", ["id"], unique=False)
