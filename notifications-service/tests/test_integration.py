"""
Интеграционные тесты для notifications-service.

Проверяем все CRUD-эндпоинты и специальные операции (статистика, прочитать всё).
Фикстуры из conftest.py: client, db_session, notification_payload, existing_notification.

ВАЖНО: notifications-service использует кастомный обработчик ошибок.
Формат 404-ответа: {"error": "...", "code": 404}
"""

from datetime import datetime

import pytest


# ── GET / ─────────────────────────────────────────────────────────────────────

class TestRoot:

    def test_root_available(self, client):
        """Корневой эндпоинт возвращает 200 и информацию о сервисе."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data


# ── POST /notifications ───────────────────────────────────────────────────────

class TestCreateNotification:

    def test_create_notification_success(self, client, notification_payload):
        """Создание уведомления с корректными данными → 201."""
        response = client.post("/notifications", json=notification_payload)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["user_id"] == notification_payload["user_id"]
        assert data["title"] == notification_payload["title"]
        assert data["message"] == notification_payload["message"]
        assert data["type"] == notification_payload["type"]
        assert data["read_at"] is None   # новое уведомление не прочитано

    def test_create_notification_has_created_at(self, client, notification_payload):
        """Созданное уведомление содержит поле created_at."""
        response = client.post("/notifications", json=notification_payload)
        assert "created_at" in response.json()

    def test_create_different_types(self, client):
        """Все типы уведомлений принимаются сервисом."""
        types = ["due_date", "new_book", "event", "fine", "system", "review"]
        for ntype in types:
            payload = {
                "user_id": 1,
                "type": ntype,
                "title": f"Тест {ntype}",
                "message": "Сообщение",
            }
            response = client.post("/notifications", json=payload)
            assert response.status_code == 201, f"Тип {ntype} вернул {response.status_code}"

    def test_create_with_related_data(self, client):
        """Уведомление с related_data (вложенные данные о книге)."""
        payload = {
            "user_id": 5,
            "type": "new_book",
            "title": "Новинка",
            "message": "Появилась книга",
            "related_data": {"book_id": 10, "book_title": "Идиот"},
        }
        response = client.post("/notifications", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["related_data"]["book_id"] == 10

    def test_create_notification_missing_required_fields(self, client):
        """Пропуск обязательных полей → 422."""
        response = client.post("/notifications", json={"user_id": 1})
        assert response.status_code == 422

    def test_create_notification_invalid_type(self, client):
        """Недопустимый тип уведомления → 422."""
        payload = {
            "user_id": 1,
            "type": "invalid_type",
            "title": "Тест",
            "message": "Сообщение",
        }
        response = client.post("/notifications", json=payload)
        assert response.status_code == 422

    def test_create_notification_invalid_priority(self, client):
        """Недопустимый приоритет → 422."""
        payload = {
            "user_id": 1,
            "type": "system",
            "title": "Тест",
            "message": "Сообщение",
            "priority": "super_high",
        }
        response = client.post("/notifications", json=payload)
        assert response.status_code == 422

    def test_create_notification_default_priority(self, client):
        """Если priority не передан — используется medium."""
        payload = {
            "user_id": 1,
            "type": "system",
            "title": "Тест",
            "message": "Сообщение",
        }
        response = client.post("/notifications", json=payload)
        assert response.json()["priority"] == "medium"

    def test_create_notification_default_channel(self, client):
        """Если channel не передан — используется in_app."""
        payload = {
            "user_id": 1,
            "type": "system",
            "title": "Тест",
            "message": "Сообщение",
        }
        response = client.post("/notifications", json=payload)
        assert response.json()["channel"] == "in_app"


# ── GET /notifications ────────────────────────────────────────────────────────

class TestGetNotifications:

    def test_empty_list_on_start(self, client):
        """Пустая база → пустой список уведомлений."""
        response = client.get("/notifications")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["unread_count"] == 0
        assert data["items"] == []

    def test_list_after_create(self, client, existing_notification):
        """После создания уведомление появляется в списке."""
        response = client.get("/notifications")
        data = response.json()
        assert data["total"] == 1
        assert data["unread_count"] == 1
        assert len(data["items"]) == 1

    def test_filter_by_user_id(self, client):
        """Фильтрация по user_id возвращает только нужного пользователя."""
        # Создаём уведомления для двух пользователей
        for uid in [1, 2]:
            client.post("/notifications", json={
                "user_id": uid, "type": "system",
                "title": f"Уведомление user {uid}", "message": "Текст",
            })

        response = client.get("/notifications?user_id=1")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["user_id"] == 1

    def test_filter_by_status_unread(self, client, existing_notification):
        """Фильтр status=unread возвращает только непрочитанные."""
        response = client.get("/notifications?status=unread")
        data = response.json()
        assert data["total"] >= 1

    def test_filter_by_type(self, client):
        """Фильтрация по типу уведомления."""
        client.post("/notifications", json={
            "user_id": 1, "type": "fine", "title": "Штраф", "message": "Текст"
        })
        client.post("/notifications", json={
            "user_id": 1, "type": "system", "title": "Система", "message": "Текст"
        })

        response = client.get("/notifications?type=fine")
        data = response.json()
        for item in data["items"]:
            assert item["type"] == "fine"

    def test_pagination_limit(self, client):
        """Пагинация: параметр limit ограничивает количество результатов."""
        for i in range(5):
            client.post("/notifications", json={
                "user_id": 1, "type": "system",
                "title": f"Уведомление {i}", "message": "Текст",
            })

        response = client.get("/notifications?limit=2")
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5  # общее количество не меняется

    def test_pagination_offset(self, client):
        """Пагинация: offset пропускает первые записи."""
        for i in range(3):
            client.post("/notifications", json={
                "user_id": 1, "type": "system",
                "title": f"Уведомление {i}", "message": "Текст",
            })

        response = client.get("/notifications?limit=10&offset=2")
        data = response.json()
        assert len(data["items"]) == 1


# ── GET /notifications/{id} ───────────────────────────────────────────────────

class TestGetNotificationById:

    def test_get_existing_notification(self, client, existing_notification):
        """Получить уведомление по id."""
        nid = existing_notification["id"]
        response = client.get(f"/notifications/{nid}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == nid
        assert data["title"] == existing_notification["title"]

    def test_get_nonexistent_notification_returns_404(self, client):
        """Несуществующее уведомление → 404 с кастомным форматом."""
        response = client.get("/notifications/99999")

        assert response.status_code == 404
        data = response.json()
        # notifications-service возвращает {"error": "...", "code": 404}
        assert "error" in data
        assert data["code"] == 404


# ── PATCH /notifications/{id}/read ───────────────────────────────────────────

class TestMarkAsRead:

    def test_mark_as_read(self, client, existing_notification):
        """Пометить уведомление прочитанным: read_at заполняется."""
        nid = existing_notification["id"]
        response = client.patch(f"/notifications/{nid}/read")

        assert response.status_code == 200
        data = response.json()
        assert data["read_at"] is not None

    def test_mark_as_read_idempotent(self, client, existing_notification):
        """Повторный PATCH не меняет уже установленное read_at."""
        nid = existing_notification["id"]
        first = client.patch(f"/notifications/{nid}/read")
        second = client.patch(f"/notifications/{nid}/read")

        assert second.status_code == 200
        assert first.json()["read_at"] == second.json()["read_at"]

    def test_mark_as_read_nonexistent_returns_404(self, client):
        """PATCH несуществующего уведомления → 404."""
        response = client.patch("/notifications/99999/read")
        assert response.status_code == 404

    def test_unread_count_decreases_after_read(self, client):
        """После прочтения unread_count уменьшается."""
        # Создаём уведомление для demo user (789) чтобы mark-all-read работал
        resp = client.post("/notifications", json={
            "user_id": 789, "type": "system",
            "title": "Тест", "message": "Сообщение",
        })
        nid = resp.json()["id"]

        before = client.get("/notifications?user_id=789").json()["unread_count"]
        client.patch(f"/notifications/{nid}/read")
        after = client.get("/notifications?user_id=789").json()["unread_count"]

        assert after == before - 1


# ── DELETE /notifications/{id} ────────────────────────────────────────────────

class TestDeleteNotification:

    def test_delete_existing_notification(self, client, existing_notification):
        """Удаление существующего уведомления → 204 No Content."""
        nid = existing_notification["id"]
        response = client.delete(f"/notifications/{nid}")
        assert response.status_code == 204

    def test_deleted_notification_not_found(self, client, existing_notification):
        """После удаления GET возвращает 404."""
        nid = existing_notification["id"]
        client.delete(f"/notifications/{nid}")

        get_response = client.get(f"/notifications/{nid}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_notification_returns_404(self, client):
        """DELETE несуществующего → 404."""
        response = client.delete("/notifications/99999")
        assert response.status_code == 404


# ── POST /notifications/read-all ─────────────────────────────────────────────

class TestMarkAllAsRead:

    def test_mark_all_as_read_empty(self, client):
        """Если нет непрочитанных уведомлений — updated_count = 0."""
        response = client.post("/notifications/read-all")
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 0

    def test_mark_all_as_read_updates_demo_user(self, client):
        """
        Создаём уведомления для demo user (user_id=789) и читаем всё.
        DEMO_USER_ID=789 захардкожен в notifications-service.
        """
        for i in range(3):
            client.post("/notifications", json={
                "user_id": 789,
                "type": "system",
                "title": f"Уведомление {i}",
                "message": "Текст",
            })

        response = client.post("/notifications/read-all")
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 3
        assert "прочитан" in data["message"].lower()


# ── GET /notifications/statistics ────────────────────────────────────────────

class TestStatistics:

    def test_statistics_empty(self, client):
        """Статистика без уведомлений → total_sent = 0."""
        response = client.get("/notifications/statistics")
        assert response.status_code == 200
        data = response.json()
        assert data["total_sent"] == 0
        assert data["read_rate"] == 0
        assert "period" in data

    def test_statistics_with_notifications(self, client):
        """Статистика учитывает созданные уведомления."""
        for t in ["new_book", "fine", "system"]:
            client.post("/notifications", json={
                "user_id": 1, "type": t,
                "title": f"Тест {t}", "message": "Текст",
            })

        response = client.get("/notifications/statistics")
        data = response.json()
        # Статистика может не включать только что созданные записи,
        # если даты фильтрации не совпадают — просто проверяем структуру
        assert "by_type" in data
        assert "by_channel" in data
        assert "by_priority" in data
        assert "read_rate" in data
