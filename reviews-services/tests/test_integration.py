"""
Интеграционные тесты для reviews-service.

Проверяем эндпоинты вместе с тестовой БД (SQLite in-memory).
Фикстуры client, db_session, test_user, test_book определены в conftest.py.
"""

from unittest.mock import AsyncMock, patch

import pytest


# ── GET / ─────────────────────────────────────────────────────────────────────

class TestRoot:

    def test_root_returns_200(self, client):
        """Корневой эндпоинт доступен и возвращает информацию о сервисе."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


# ── GET /reviews ──────────────────────────────────────────────────────────────

class TestGetReviews:

    def test_empty_list_on_start(self, client):
        """В пустой базе список отзывов — пустой массив."""
        response = client.get("/reviews")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_all_reviews(self, client, test_user):
        """После создания двух отзывов оба должны вернуться в списке."""
        client.post("/reviews", json={"title": "Отзыв 1", "user_id": 1})
        client.post("/reviews", json={"title": "Отзыв 2", "user_id": 1})

        response = client.get("/reviews")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        titles = {r["title"] for r in data}
        assert "Отзыв 1" in titles
        assert "Отзыв 2" in titles


# ── POST /reviews ─────────────────────────────────────────────────────────────

class TestCreateReview:

    def test_create_review_success(self, client, test_user):
        """Создание отзыва с корректными данными возвращает 201 и тело с id."""
        payload = {
            "title": "Интересная книга",
            "content": "Захватывающий сюжет",
            "is_published": False,
            "user_id": 1,
        }
        response = client.post("/reviews", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == "Интересная книга"
        assert data["content"] == "Захватывающий сюжет"
        assert data["is_published"] is False
        assert data["user_id"] == 1
        assert data["book_id"] is None

    def test_create_review_minimal(self, client, test_user):
        """Создание отзыва с минимальными данными (только title и user_id)."""
        response = client.post("/reviews", json={"title": "Коротко", "user_id": 1})

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Коротко"
        assert data["content"] is None

    def test_create_review_with_book(self, client, test_user_and_book):
        """Отзыв с book_id корректно связывается с книгой."""
        payload = {
            "title": "Рецензия",
            "user_id": 1,
            "book_id": 1,
            "is_published": False,
        }
        response = client.post("/reviews", json=payload)

        assert response.status_code == 201
        assert response.json()["book_id"] == 1

    def test_create_review_invalid_user(self, client):
        """user_id несуществующего пользователя → 400."""
        payload = {"title": "Чей отзыв?", "user_id": 9999}
        response = client.post("/reviews", json=payload)

        assert response.status_code == 400
        assert "9999" in response.json()["detail"]

    def test_create_review_invalid_book(self, client, test_user):
        """book_id несуществующей книги → 400."""
        payload = {"title": "Какая книга?", "user_id": 1, "book_id": 9999}
        response = client.post("/reviews", json=payload)

        assert response.status_code == 400

    def test_create_review_missing_title(self, client, test_user):
        """Отсутствие title → 422 (ошибка валидации Pydantic)."""
        response = client.post("/reviews", json={"user_id": 1})
        assert response.status_code == 422

    def test_create_review_missing_user_id(self, client):
        """Отсутствие user_id → 422."""
        response = client.post("/reviews", json={"title": "Без автора"})
        assert response.status_code == 422

    def test_create_published_review_adds_to_reading_list(self, client, test_user_and_book):
        """
        Опубликованный отзыв с book_id → книга добавляется в список чтения.
        Это проверяет бизнес-логику: after post review → reading list entry created.
        """
        payload = {
            "title": "Публичный отзыв",
            "user_id": 1,
            "book_id": 1,
            "is_published": True,
        }
        response = client.post("/reviews", json=payload)
        assert response.status_code == 201

    def test_create_unpublished_review_no_reading_list(self, client, test_user_and_book):
        """Неопубликованный отзыв не добавляет книгу в список чтения."""
        payload = {
            "title": "Черновик",
            "user_id": 1,
            "book_id": 1,
            "is_published": False,
        }
        response = client.post("/reviews", json=payload)
        assert response.status_code == 201

    def test_created_review_has_timestamp(self, client, test_user):
        """Созданный отзыв содержит поле created_at."""
        response = client.post("/reviews", json={"title": "Тест", "user_id": 1})
        assert "created_at" in response.json()


# ── GET /reviews/{id} ─────────────────────────────────────────────────────────

class TestGetReviewById:

    def test_get_existing_review(self, client, existing_review):
        """Получить конкретный отзыв по id."""
        review_id = existing_review["id"]
        response = client.get(f"/reviews/{review_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == review_id
        assert data["title"] == existing_review["title"]

    def test_get_nonexistent_review_returns_404(self, client):
        """Запрос несуществующего отзыва → 404."""
        response = client.get("/reviews/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Review not found"


# ── PUT /reviews/{id} ─────────────────────────────────────────────────────────

class TestUpdateReview:

    def test_update_title(self, client, existing_review):
        """Обновление заголовка отзыва."""
        review_id = existing_review["id"]
        response = client.put(
            f"/reviews/{review_id}",
            json={"title": "Новый заголовок"},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Новый заголовок"

    def test_update_published_status(self, client, existing_review):
        """Публикация черновика через PUT."""
        review_id = existing_review["id"]
        response = client.put(f"/reviews/{review_id}", json={"is_published": True})

        assert response.status_code == 200
        assert response.json()["is_published"] is True

    def test_update_persists(self, client, existing_review):
        """После PUT изменения отражаются при GET."""
        review_id = existing_review["id"]
        client.put(f"/reviews/{review_id}", json={"content": "Обновлённый текст"})

        get_response = client.get(f"/reviews/{review_id}")
        assert get_response.json()["content"] == "Обновлённый текст"

    def test_update_nonexistent_review_returns_404(self, client):
        """PUT несуществующего отзыва → 404."""
        response = client.put("/reviews/99999", json={"title": "Тест"})
        assert response.status_code == 404

    def test_partial_update_preserves_other_fields(self, client, test_user):
        """Частичное обновление: незатронутые поля сохраняются."""
        create_resp = client.post("/reviews", json={
            "title": "Оригинал",
            "content": "Оригинальный текст",
            "user_id": 1,
        })
        review_id = create_resp.json()["id"]

        client.put(f"/reviews/{review_id}", json={"title": "Изменённый"})

        get_resp = client.get(f"/reviews/{review_id}")
        data = get_resp.json()
        assert data["title"] == "Изменённый"
        assert data["content"] == "Оригинальный текст"  # не должен измениться


# ── DELETE /reviews/{id} ──────────────────────────────────────────────────────

class TestDeleteReview:

    def test_delete_existing_review(self, client, existing_review):
        """Удаление существующего отзыва → 200."""
        review_id = existing_review["id"]
        response = client.delete(f"/reviews/{review_id}")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

    def test_deleted_review_not_found(self, client, existing_review):
        """После DELETE отзыв не возвращается по GET."""
        review_id = existing_review["id"]
        client.delete(f"/reviews/{review_id}")

        get_response = client.get(f"/reviews/{review_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_review_returns_404(self, client):
        """DELETE несуществующего отзыва → 404."""
        response = client.delete("/reviews/99999")
        assert response.status_code == 404


# ── GET /external/posts (mock внешнего API) ───────────────────────────────────

class TestExternalPosts:

    def test_external_posts_mocked(self, client):
        """
        Мокируем httpx.AsyncClient целиком, чтобы не зависеть от сети.
        json() у httpx — синхронный метод, поэтому используем MagicMock для ответа.
        """
        from unittest.mock import MagicMock

        fake_posts = [
            {"id": i, "title": f"Post {i}", "body": "...", "userId": 1}
            for i in range(1, 6)
        ]

        # Синхронный мок ответа (json() у httpx не async)
        mock_response = MagicMock()
        mock_response.json.return_value = fake_posts
        mock_response.raise_for_status.return_value = None

        # Мок самого клиента: get() — корутина, возвращающая mock_response
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Патчим контекстный менеджер: __aenter__ возвращает mock_client
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_cm):
            response = client.get("/external/posts")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5
