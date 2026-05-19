"""
HTTP-вызовы микросервисов отзывов (POST /reviews) и уведомлений (POST /notifications).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


def _post_json(url: str, payload: Dict[str, Any], *, timeout: float = 10.0) -> Tuple[int, Optional[Any]]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            code = resp.status
    except HTTPError as e:
        raw = e.read().decode()
        code = e.code
    except (URLError, TimeoutError, OSError) as e:
        logger.warning("HTTP ошибка к %s: %s", url, e)
        return 0, None

    if not raw.strip():
        return code, None
    try:
        return code, json.loads(raw)
    except json.JSONDecodeError:
        return code, {"raw": raw[:500]}


def format_service_error(parsed: Optional[Any]) -> str:
    if parsed is None:
        return "Сервис недоступен или вернул пустой ответ."
    if not isinstance(parsed, dict):
        return str(parsed)
    if "error" in parsed:
        return str(parsed["error"])
    detail = parsed.get("detail")
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                parts.append(str(item.get("msg", item)))
            else:
                parts.append(str(item))
        return "; ".join(parts) if parts else "Ошибка валидации."
    if detail is not None:
        return str(detail)
    return "Неизвестная ошибка сервиса."


def fetch_book_reviews(book_id: int) -> list:
    """Получить опубликованные отзывы о книге из микросервиса."""
    base = (getattr(settings, "REVIEWS_SERVICE_URL", None) or "").strip().rstrip("/")
    if not base:
        return []
    url = f"{base}/reviews?book_id={book_id}"
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
        if not isinstance(data, list):
            return []
        return [r for r in data if isinstance(r, dict) and r.get("is_published")]
    except (URLError, HTTPError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as e:
        logger.warning("reviews-service недоступен при получении отзывов: %s", e)
        return []


def create_review_via_service(
    *,
    user_id: int,
    book_id: int,
    title: str,
    content: str,
    is_published: bool,
) -> Tuple[int, Optional[Any]]:
    base = (getattr(settings, "REVIEWS_SERVICE_URL", None) or "").strip().rstrip("/")
    if not base:
        return 0, None
    url = f"{base}/reviews"
    payload = {
        "user_id": user_id,
        "book_id": book_id,
        "title": title,
        "content": content or None,
        "is_published": is_published,
    }
    return _post_json(url, payload)


def build_review_saved_notification_message(book_title: str, review_title: str) -> str:
    return (
        f"Ваш отзыв «{review_title}» по книге «{book_title}» успешно создан "
        "через сервис отзывов."
    )


def create_review_saved_notification_via_service(
    *,
    user_id: int,
    book_id: int,
    book_title: str,
    review_title: str,
) -> Tuple[int, Optional[Any]]:
    base = (getattr(settings, "NOTIFICATIONS_SERVICE_URL", None) or "").strip().rstrip("/")
    if not base:
        return 0, None
    url = f"{base}/notifications"
    payload = {
        "user_id": user_id,
        "type": "review",
        "title": "Отзыв сохранён",
        "message": build_review_saved_notification_message(book_title, review_title),
        "priority": "medium",
        "channel": "in_app",
        "related_data": {"book_id": book_id, "book_title": book_title},
    }
    return _post_json(url, payload)
