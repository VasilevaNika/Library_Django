"""
Дублирует пользователей и книги из моделей Django в таблицы library_users и books,
которые читают микросервисы (общая PostgreSQL).

Запуск после миграций Django и Alembic (recommendations):
  python manage.py sync_microservice_mirror
  python manage.py sync_microservice_mirror --prune   # убрать сиды Alembic, оставить только данные из админки

Идентификаторы совпадают: auth_user.id → library_users.id, library_book.id → books.id.

В обычной работе зеркало обновляется сигналами (см. library.signals); команда — для полного пересчёта.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from library.microservice_catalog_mirror import (
    upsert_book_row,
    upsert_library_user_id,
)
from library.models import Book

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Синхронизирует пользователей и книги в таблицы для микросервисов (library_users, books). "
        "Флаг --prune удаляет строки, которых нет в Django (демо-данные из миграций Alembic)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--prune",
            action="store_true",
            help="Удалить из books и library_users записи, отсутствующие в монолите (после синка)",
        )

    def handle(self, *args, **options):
        prune = options["prune"]
        if connection.vendor != "postgresql":
            self.stderr.write(
                "Команда рассчитана на главную общую PostgreSQL (DATABASE_URL или DB_* в settings). "
                "Без неё используется SQLite — зеркалирование в таблицы микросервисов недоступно."
            )
            return

        book_count = 0
        django_user_ids = list(User.objects.order_by("id").values_list("id", flat=True))
        django_book_ids = list(Book.objects.order_by("id").values_list("id", flat=True))

        with transaction.atomic():
            with connection.cursor() as cursor:
                for uid in django_user_ids:
                    upsert_library_user_id(uid)

                for book in Book.objects.select_related("author").prefetch_related("genres").order_by(
                    "id"
                ):
                    upsert_book_row(book, update_sequence=False)
                    book_count += 1

                if prune:
                    self._delete_ids_not_in(cursor, "books", django_book_ids)
                    self._delete_ids_not_in(cursor, "library_users", django_user_ids)

                cursor.execute(
                    "SELECT setval('books_id_seq', (SELECT COALESCE(MAX(id), 1) FROM books))"
                )

        msg = (
            f"Готово: пользователей в Django: {len(django_user_ids)}, "
            f"книг записано в books: {book_count}."
        )
        if prune:
            msg += " Лишние строки в books/library_users (сиды Alembic) удалены."
        self.stdout.write(self.style.SUCCESS(msg))

    @staticmethod
    def _delete_ids_not_in(cursor, table: str, keep_ids: list) -> None:
        """Удаляет строки, id которых нет в keep_ids (CASCADE снимет зависимые ignored_books / reading_list_entries)."""
        if keep_ids:
            placeholders = ",".join(["%s"] * len(keep_ids))
            cursor.execute(
                f"DELETE FROM {table} WHERE id NOT IN ({placeholders})",
                keep_ids,
            )
        else:
            cursor.execute(f"DELETE FROM {table}")
