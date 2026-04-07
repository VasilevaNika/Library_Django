"""
После сохранения в админке сразу обновляем таблицы books / library_users для микросервисов.
on_commit — чтобы жанры (M2M) уже были записаны к моменту зеркалирования.
"""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from library.microservice_catalog_mirror import (
    delete_book_row,
    delete_library_user_row,
    postgres_mirror_active,
    upsert_book_row,
    upsert_library_user_id,
)
from library.models import Book

User = get_user_model()
logger = logging.getLogger(__name__)


def _load_book_for_mirror(pk: int):
    return Book.objects.select_related("author").prefetch_related("genres").get(pk=pk)


def _schedule_book_mirror(pk: int) -> None:
    if not postgres_mirror_active():
        return

    def run():
        try:
            book = _load_book_for_mirror(pk)
            upsert_book_row(book)
        except Exception:
            logger.exception(
                "Не удалось записать книгу %s в таблицу books для микросервисов",
                pk,
            )

    transaction.on_commit(run)


@receiver(post_save, sender=Book, dispatch_uid="library.mirror_book_post_save")
def mirror_book_after_save(sender, instance, **kwargs):
    _schedule_book_mirror(instance.pk)


@receiver(
    m2m_changed,
    sender=Book.genres.through,
    dispatch_uid="library.mirror_book_m2m_genres",
)
def mirror_book_after_genres_change(sender, instance, action, **kwargs):
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    if not isinstance(instance, Book):
        return
    _schedule_book_mirror(instance.pk)


@receiver(post_delete, sender=Book, dispatch_uid="library.mirror_book_post_delete")
def mirror_book_after_delete(sender, instance, **kwargs):
    if not postgres_mirror_active():
        return
    pk = instance.pk

    def run():
        try:
            delete_book_row(pk)
        except Exception:
            logger.exception(
                "Не удалось удалить книгу %s из таблицы books для микросервисов",
                pk,
            )

    transaction.on_commit(run)


@receiver(post_save, sender=User, dispatch_uid="library.mirror_user_post_save")
def mirror_user_after_save(sender, instance, **kwargs):
    if not postgres_mirror_active():
        return
    uid = instance.pk

    def run():
        try:
            upsert_library_user_id(uid)
        except Exception:
            logger.exception(
                "Не удалось записать пользователя %s в library_users",
                uid,
            )

    transaction.on_commit(run)


@receiver(post_delete, sender=User, dispatch_uid="library.mirror_user_post_delete")
def mirror_user_after_delete(sender, instance, **kwargs):
    if not postgres_mirror_active():
        return
    uid = instance.pk

    def run():
        try:
            delete_library_user_row(uid)
        except Exception:
            logger.exception(
                "Не удалось удалить пользователя %s из library_users",
                uid,
            )

    transaction.on_commit(run)
