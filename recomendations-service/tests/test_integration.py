"""
Интеграционные тесты для recomendations-service.

Проверяем все эндпоинты рекомендаций и личных списков (игнор / список чтения).
Фикстуры из conftest.py: client, db_session, test_user, test_book, two_books.
"""

import json as json_lib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── GET / ─────────────────────────────────────────────────────────────────────

class TestRoot:

    def test_root_returns_200(self, client):
        """Корневой эндпоинт работает."""
        response = client.get("/")
        assert response.status_code == 999
        data = response.json()
        assert "message" in data
        assert "status" in data


# ── GET /recommendations/popular ─────────────────────────────────────────────

class TestPopularBooks:

    def test_popular_empty_db(self, client):
        """Пустая БД → пустой список популярных книг."""
        response = client.get("/recommendations/popular")
        assert response.status_code == 200
        assert response.json() == []

    def test_popular_with_books(self, client, two_books):
        """С книгами в БД возвращается список, отсортированный по рейтингу."""
        response = client.get("/recommendations/popular")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Первая книга должна иметь рейтинг >= второй (сортировка по убыванию)
        assert data[0]["rating"] >= data[1]["rating"]

    def test_popular_limit_parameter(self, client, two_books):
        """Параметр limit ограничивает количество результатов."""
        response = client.get("/recommendations/popular?limit=1")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_popular_limit_too_large_returns_422(self, client):
        """limit > 50 не разрешён (Query le=50)."""
        response = client.get("/recommendations/popular?limit=100")
        assert response.status_code == 422

    def test_popular_returns_book_fields(self, client, test_book):
        """Ответ содержит все обязательные поля BookRecommendation."""
        response = client.get("/recommendations/popular")
        data = response.json()
        assert len(data) == 1
        book = data[0]
        assert "id" in book
        assert "title" in book
        assert "author" in book


# ── GET /recommendations/new ──────────────────────────────────────────────────

class TestNewBooks:

    def test_new_empty_db(self, client):
        """Пустая БД → пустой список новинок."""
        response = client.get("/recommendations/new")
        assert response.status_code == 200
        assert response.json() == []

    def test_new_with_books(self, client, two_books):
        """С книгами в БД возвращается список."""
        response = client.get("/recommendations/new")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_new_limit_parameter(self, client, two_books):
        """Параметр limit работает."""
        response = client.get("/recommendations/new?limit=1")
        assert len(response.json()) == 1


# ── GET /recommendations/genre/{genreId} ─────────────────────────────────────

class TestGenreBooks:

    def test_genre_with_books(self, client, test_book):
        """Книги в жанре genre_id=1 возвращаются."""
        response = client.get("/recommendations/genre/1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["genre_id"] == 1

    def test_genre_empty_for_unknown_genre(self, client, test_book):
        """Жанр без книг с нужным рейтингом → пустой список."""
        response = client.get("/recommendations/genre/2")
        assert response.status_code == 200
        assert response.json() == []

    def test_genre_id_too_large_returns_404(self, client):
        """genreId > 5 → 404 (бизнес-правило сервиса)."""
        response = client.get("/recommendations/genre/6")
        assert response.status_code == 404

    def test_genre_min_rating_filter(self, client, db_session):
        """Параметр min_rating фильтрует книги по рейтингу."""
        from app import models

        # Добавляем книгу с низким рейтингом
        low_rated = models.Book(id=5, title="Слабая книга", author="Автор", genre_id=1, rating=2.0)
        db_session.add(low_rated)
        db_session.commit()

        response = client.get("/recommendations/genre/1?min_rating=4.0")
        data = response.json()
        # Книга с рейтингом 2.0 не должна попасть в результат
        for book in data:
            assert book["rating"] >= 4.0


# ── GET /recommendations/author/{authorId} ────────────────────────────────────

class TestAuthorBooks:

    def test_author_with_books(self, client, test_book):
        """Книги автора author_id=1 возвращаются."""
        response = client.get("/recommendations/author/1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_author_empty_for_unknown_author(self, client, test_book):
        """Автор без книг в БД → пустой список."""
        response = client.get("/recommendations/author/2")
        assert response.status_code == 200
        assert response.json() == []

    def test_author_id_too_large_returns_404(self, client):
        """authorId > 10 → 404 (бизнес-правило)."""
        response = client.get("/recommendations/author/11")
        assert response.status_code == 404

    def test_author_limit_parameter(self, client, two_books):
        """Параметр limit работает."""
        response = client.get("/recommendations/author/1?limit=1")
        assert response.status_code == 200
        assert len(response.json()) <= 1


# ── GET /recommendations/similar/{bookId} ─────────────────────────────────────

class TestSimilarBooks:

    def test_similar_books_found(self, client, two_books):
        """Похожие книги для существующей книги."""
        response = client.get("/recommendations/similar/1")
        assert response.status_code == 200
        data = response.json()
        # Должна вернуться книга 2 (не книга 1 сама по себе)
        for book in data:
            assert book["id"] != 1

    def test_similar_book_not_found(self, client):
        """Несуществующая книга → 404."""
        response = client.get("/recommendations/similar/99999")
        assert response.status_code == 404

    def test_similar_limit_parameter(self, client, two_books):
        """Параметр limit ограничивает количество похожих."""
        response = client.get("/recommendations/similar/1?limit=1")
        assert len(response.json()) <= 1


# ── GET /recommendations/random ──────────────────────────────────────────────

class TestRandomBook:

    def test_random_book_empty_db(self, client):
        """Нет книг → 404."""
        response = client.get("/recommendations/random")
        assert response.status_code == 404

    def test_random_book_returns_one(self, client, two_books):
        """Случайная книга возвращает один объект."""
        response = client.get("/recommendations/random")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "title" in data

    def test_random_book_with_genre_filter(self, client, test_book):
        """Фильтрация случайной книги по genre_id."""
        response = client.get("/recommendations/random?genre_id=1")
        assert response.status_code == 200

    def test_random_book_genre_not_found(self, client, test_book):
        """Нет книг с указанным genre_id → 404."""
        response = client.get("/recommendations/random?genre_id=999")
        assert response.status_code == 404


# ── GET /recommendations/quotes (mock внешнего API) ───────────────────────────

class TestQuotes:

    def test_quotes_endpoint_mocked(self, client):
        """
        Мокируем httpx.AsyncClient целиком, чтобы не зависеть от сети.
        json() у httpx — синхронный метод, поэтому используем MagicMock для ответа.
        """
        fake_post = {
            "id": 7,
            "title": "Читайте книги",
            "body": "Чтение развивает воображение и интеллект.",
            "userId": 1,
        }

        # Синхронный мок ответа (json() у httpx не async)
        mock_response = MagicMock()
        mock_response.json.return_value = fake_post
        mock_response.raise_for_status.return_value = None

        # Мок клиента: get() — корутина, возвращающая mock_response
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Патчим контекстный менеджер AsyncClient
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_cm):
            response = client.get("/recommendations/quotes")

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "jsonplaceholder"
        assert data["quote_id"] == 7
        assert data["author"] == "Demo Author"


# ── GET /user/{userId}/ignore ─────────────────────────────────────────────────

class TestIgnoreList:

    def test_ignore_list_user_not_found(self, client):
        """Несуществующий пользователь → 404."""
        response = client.get("/user/99999/ignore")
        assert response.status_code == 404

    def test_ignore_list_empty(self, client, test_user):
        """У нового пользователя игнор-лист пустой."""
        response = client.get("/user/10/ignore")
        assert response.status_code == 200
        assert response.json() == []

    def test_add_and_get_ignore(self, client, test_user, test_book):
        """После добавления книга появляется в игнор-листе."""
        client.post("/user/10/ignore", json={"book_id": 1, "reason": "already_read"})
        response = client.get("/user/10/ignore")

        data = response.json()
        assert len(data) == 1
        assert data[0]["book_id"] == 1
        assert data[0]["reason"] == "already_read"


# ── POST /user/{userId}/ignore ────────────────────────────────────────────────

class TestAddToIgnore:

    def test_add_to_ignore_success(self, client, test_user, test_book):
        """Добавление книги в игнор-лист → 201."""
        response = client.post(
            "/user/10/ignore",
            json={"book_id": 1, "reason": "not_interesting"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["book_id"] == 1
        assert "рекомендоваться" in data["message"]

    def test_add_to_ignore_user_not_found(self, client, test_book):
        """Несуществующий пользователь → 404."""
        response = client.post("/user/99999/ignore", json={"book_id": 1})
        assert response.status_code == 404

    def test_add_to_ignore_book_not_found(self, client, test_user):
        """Несуществующая книга → 404."""
        response = client.post("/user/10/ignore", json={"book_id": 99999})
        assert response.status_code == 404

    def test_add_to_ignore_without_reason(self, client, test_user, test_book):
        """Можно добавить без причины."""
        response = client.post("/user/10/ignore", json={"book_id": 1})
        assert response.status_code == 201

    def test_add_to_ignore_idempotent(self, client, test_user, test_book):
        """Повторное добавление той же книги обновляет запись, не создаёт дубль."""
        client.post("/user/10/ignore", json={"book_id": 1, "reason": "already_read"})
        client.post("/user/10/ignore", json={"book_id": 1, "reason": "other"})

        get_resp = client.get("/user/10/ignore")
        data = get_resp.json()
        book_entries = [x for x in data if x["book_id"] == 1]
        assert len(book_entries) == 1  # нет дублей
        assert book_entries[0]["reason"] == "other"  # обновлено


# ── DELETE /user/{userId}/ignore ─────────────────────────────────────────────

def _delete_with_body(client, url: str, body: dict):
    """Вспомогательная функция: DELETE-запрос с JSON-телом."""
    return client.request(
        "DELETE",
        url,
        content=json_lib.dumps(body),
        headers={"Content-Type": "application/json"},
    )


class TestRemoveFromIgnore:

    def test_remove_from_ignore(self, client, test_user, test_book):
        """Удаление из игнор-листа."""
        client.post("/user/10/ignore", json={"book_id": 1})
        response = _delete_with_body(client, "/user/10/ignore", {"book_id": 1})

        assert response.status_code == 200
        assert "рекомендоваться" in response.json()["message"]

    def test_remove_from_ignore_user_not_found(self, client, test_book):
        """Несуществующий пользователь → 404."""
        response = _delete_with_body(client, "/user/99999/ignore", {"book_id": 1})
        assert response.status_code == 404

    def test_after_remove_book_gone_from_list(self, client, test_user, test_book):
        """После удаления книга исчезает из игнор-листа."""
        client.post("/user/10/ignore", json={"book_id": 1})
        _delete_with_body(client, "/user/10/ignore", {"book_id": 1})

        get_resp = client.get("/user/10/ignore")
        assert get_resp.json() == []


# ── GET /user/{userId}/reading-list ──────────────────────────────────────────

class TestReadingList:

    def test_reading_list_user_not_found(self, client):
        """Несуществующий пользователь → 404."""
        response = client.get("/user/99999/reading-list")
        assert response.status_code == 404

    def test_reading_list_empty(self, client, test_user):
        """У нового пользователя список чтения пустой."""
        response = client.get("/user/10/reading-list")
        assert response.status_code == 200
        assert response.json() == []

    def test_reading_list_after_add(self, client, test_user, test_book):
        """После добавления книга появляется в списке."""
        client.post("/user/10/reading-list", json={"book_id": 1, "priority": "high"})
        response = client.get("/user/10/reading-list")

        data = response.json()
        assert len(data) == 1
        assert data[0]["book_id"] == 1
        assert data[0]["priority"] == "high"


# ── POST /user/{userId}/reading-list ─────────────────────────────────────────

class TestAddToReadingList:

    def test_add_to_reading_list_success(self, client, test_user, test_book):
        """Добавление книги в список чтения → 201."""
        response = client.post(
            "/user/10/reading-list",
            json={"book_id": 1, "priority": "medium"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["book_id"] == 1
        assert "список" in data["message"].lower()

    def test_add_to_reading_list_user_not_found(self, client, test_book):
        """Несуществующий пользователь → 404."""
        response = client.post("/user/99999/reading-list", json={"book_id": 1, "priority": "low"})
        assert response.status_code == 404

    def test_add_to_reading_list_book_not_found(self, client, test_user):
        """Несуществующая книга → 404."""
        response = client.post("/user/10/reading-list", json={"book_id": 99999, "priority": "low"})
        assert response.status_code == 404

    def test_add_to_reading_list_default_priority(self, client, test_user, test_book):
        """Приоритет по умолчанию — medium."""
        response = client.post("/user/10/reading-list", json={"book_id": 1})
        assert response.status_code == 201

    def test_add_to_reading_list_idempotent(self, client, test_user, test_book):
        """Повторное добавление обновляет приоритет."""
        client.post("/user/10/reading-list", json={"book_id": 1, "priority": "low"})
        client.post("/user/10/reading-list", json={"book_id": 1, "priority": "high"})

        get_resp = client.get("/user/10/reading-list")
        data = get_resp.json()
        entries = [x for x in data if x["book_id"] == 1]
        assert len(entries) == 1  # нет дублей
        assert entries[0]["priority"] == "high"  # обновлён


# ── DELETE /user/{userId}/reading-list ───────────────────────────────────────

class TestRemoveFromReadingList:

    def test_remove_from_reading_list(self, client, test_user, test_book):
        """Удаление книги из списка чтения."""
        client.post("/user/10/reading-list", json={"book_id": 1, "priority": "medium"})
        response = _delete_with_body(
            client, "/user/10/reading-list", {"book_id": 1, "priority": "medium"}
        )
        assert response.status_code == 200
        assert "удалена" in response.json()["message"].lower()

    def test_remove_from_reading_list_user_not_found(self, client, test_book):
        """Несуществующий пользователь → 404."""
        response = _delete_with_body(
            client, "/user/99999/reading-list", {"book_id": 1, "priority": "medium"}
        )
        assert response.status_code == 404

    def test_after_remove_book_gone_from_list(self, client, test_user, test_book):
        """После удаления книга исчезает из списка."""
        client.post("/user/10/reading-list", json={"book_id": 1, "priority": "medium"})
        _delete_with_body(client, "/user/10/reading-list", {"book_id": 1, "priority": "medium"})

        get_resp = client.get("/user/10/reading-list")
        assert get_resp.json() == []
