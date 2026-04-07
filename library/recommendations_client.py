"""
HTTP-клиент к микросервису рекомендаций: те же «новинки», что GET /recommendations/new.
"""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from typing import Any, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


class _FakeGenres:
    __slots__ = ("_name",)

    def __init__(self, name: Optional[str]):
        self._name = name

    def all(self):
        if not self._name:
            return []
        return [SimpleNamespace(name=self._name)]


class _FakeCover:
    __slots__ = ("url",)

    def __init__(self, url: str):
        self.url = url

    def __bool__(self):
        return bool(self.url)


def _cover_url(path: Optional[Any]) -> Optional[str]:
    if path is None:
        return None
    path = str(path).strip()
    if not path:
        return None
    if path.startswith(("http://", "https://", "/")):
        return path
    media = settings.MEDIA_URL
    if not media.endswith("/"):
        media += "/"
    return media + path.lstrip("/")


def book_from_recommendation_api(item: dict) -> SimpleNamespace:
    """Поля, совместимые с шаблоном home.html (author.name, genres.all, cover.url)."""
    cid = item.get("id")
    title = item.get("title") or ""
    author_s = item.get("author") or ""
    cu = _cover_url(item.get("cover"))
    genre_name = item.get("genre_name") or ""

    obj = SimpleNamespace(
        pk=cid,
        id=cid,
        title=title,
        author=SimpleNamespace(name=author_s),
        genres=_FakeGenres(genre_name),
    )
    obj.cover = _FakeCover(cu) if cu else None
    return obj


def fetch_new_books_from_recommendations_service(*, limit: int = 6) -> List[SimpleNamespace]:
    base = (getattr(settings, "RECOMMENDATIONS_SERVICE_URL", None) or "").strip().rstrip("/")
    if not base:
        return []
    url = f"{base}/recommendations/new?limit={int(limit)}"
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=4) as resp:
            raw = resp.read().decode()
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return [
            book_from_recommendation_api(x)
            for x in data
            if isinstance(x, dict)
        ]
    except (URLError, HTTPError, TimeoutError, OSError, ValueError, TypeError, json.JSONDecodeError) as e:
        logger.warning(
            "recommendations-service недоступен (%s), блок «Новинки библиотеки» из ORM",
            e,
        )
        return []
