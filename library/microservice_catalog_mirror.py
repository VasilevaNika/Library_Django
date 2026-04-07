"""
Зеркалирование каталога в таблицы books / library_users (PostgreSQL), которые читает recommendations-service.
"""

from django.db import connection


def postgres_mirror_active() -> bool:
    return connection.vendor == "postgresql"


def upsert_library_user_id(user_id: int) -> None:
    if not postgres_mirror_active():
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO library_users (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
            [user_id],
        )


def upsert_book_row(book, *, update_sequence: bool = True) -> None:
    """
    book — library.models.Book с загруженным author (select_related) и genres (prefetch_related).
    update_sequence=False — для пакетного sync без лишних setval на каждой строке.
    """
    if not postgres_mirror_active():
        return
    g = book.genres.first()
    cover_str = book.cover.name if book.cover else None
    created = book.created_at
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO books (
                id, title, author, author_id, genre_id, genre_name,
                year, cover, rating, rating_count, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                author = EXCLUDED.author,
                author_id = EXCLUDED.author_id,
                genre_id = EXCLUDED.genre_id,
                genre_name = EXCLUDED.genre_name,
                year = EXCLUDED.year,
                cover = EXCLUDED.cover,
                rating = EXCLUDED.rating,
                rating_count = EXCLUDED.rating_count,
                created_at = EXCLUDED.created_at
            """,
            [
                book.id,
                book.title,
                book.author.name,
                book.author_id,
                g.id if g else None,
                g.name if g else None,
                None,
                cover_str,
                None,
                None,
                created,
            ],
        )
        if update_sequence:
            cursor.execute(
                "SELECT setval('books_id_seq', (SELECT COALESCE(MAX(id), 1) FROM books))"
            )


def delete_book_row(book_id: int) -> None:
    if not postgres_mirror_active():
        return
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM books WHERE id = %s", [book_id])
        cursor.execute(
            "SELECT setval('books_id_seq', (SELECT COALESCE(MAX(id), 1) FROM books))"
        )


def delete_library_user_row(user_id: int) -> None:
    if not postgres_mirror_active():
        return
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM library_users WHERE id = %s", [user_id])
