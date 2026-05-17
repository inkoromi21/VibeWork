"""
Rutube: поиск видео и витрины (Showcase API).

Документация витрин: https://github.com/rutube/ShowcaseTutorial
Поиск: GET https://rutube.ru/api/search/video/?query=...&page=1
Витрина «Обучение»: GET https://rutube.ru/api/feeds/education?format=json
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

_log = logging.getLogger(__name__)
_TIMEOUT = 12
_UA = {"User-Agent": "VibeWork/1.0 (career learning; contact@localhost)"}

_COURSE_MARKERS = (
    "курс",
    "плейлист",
    "урок",
    "лекц",
    "обучен",
    "вебинар",
    "марафон",
    "туториал",
    "с нуля",
    "полный",
    "разбор",
)

_TRACK_SEARCH_QUERIES: Dict[str, str] = {
    "backend": "python backend разработка курс",
    "frontend": "javascript frontend веб курс",
    "devops": "devops docker kubernetes курс",
    "data": "sql python аналитика данных курс",
    "qa": "тестирование qa автоматизация курс",
    "design": "figma ux ui дизайн курс",
    "marketing": "маркетинг smm курс",
    "sales": "продажи b2b курс",
}

_FEED_BY_SPHERE: Dict[str, str] = {
    "it_dev": "education",
    "data": "education",
    "design": "education",
    "marketing": "education",
    "sales": "education",
    "education": "education",
}


def _get_json(url: str, *, params: Optional[dict] = None) -> Any:
    r = requests.get(url, params=params, timeout=_TIMEOUT, headers=_UA)
    r.raise_for_status()
    return r.json()


def _video_id_from_item(item: Dict[str, Any]) -> str:
    vid = str(item.get("id") or "").strip()
    if vid:
        return vid
    url = str(item.get("video_url") or item.get("url") or "")
    m = re.search(r"/video/([a-f0-9]{32})", url)
    return m.group(1) if m else ""


def _video_page_url(item: Dict[str, Any]) -> str:
    u = str(item.get("video_url") or "").strip()
    if u:
        return u if u.endswith("/") else u + "/"
    vid = _video_id_from_item(item)
    return f"https://rutube.ru/video/{vid}/" if vid else ""


def _course_score(title: str, query: str) -> float:
    t = (title or "").lower()
    q = (query or "").lower()
    score = 0.0
    for w in re.split(r"\s+", q):
        if len(w) > 2 and w in t:
            score += 2.5
    for m in _COURSE_MARKERS:
        if m in t:
            score += 6.0
    if "полный курс" in t or "курс с нуля" in t or "плейлист" in t:
        score += 4.0
    return score


def _item_to_card(item: Dict[str, Any], *, query: str = "") -> Optional[Dict[str, Any]]:
    url = _video_page_url(item)
    if not url:
        return None
    title = str(item.get("title") or "Видео на Rutube").strip()
    desc = str(item.get("description") or "")[:300]
    kind = "курс" if _course_score(title, query) >= 8 else "видео"
    return {
        "title": title[:200],
        "url": url,
        "kind": kind,
        "description": desc,
        "provider": "rutube",
        "source_type": "api",
        "is_free": True,
        "language": "ru",
        "_score": _course_score(title, query),
    }


def rutube_search_videos(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    try:
        data = _get_json(
            "https://rutube.ru/api/search/video/",
            params={"query": q, "page": 1},
        )
        items = list(data.get("results") or [])
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for item in items:
            card = _item_to_card(item, query=q)
            if card:
                scored.append((float(card.pop("_score", 0)), card))
        scored.sort(key=lambda x: -x[0])
        out: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for _, card in scored:
            if card["url"] in seen:
                continue
            seen.add(card["url"])
            out.append(card)
            if len(out) >= limit:
                break
        return out
    except Exception as e:
        _log.debug("rutube_search_videos failed: %s", e)
        return []


def rutube_showcase_feed_videos(
    feed_slug: str,
    query: str,
    limit: int = 3,
    *,
    max_resource_fetches: int = 4,
) -> List[Dict[str, Any]]:
    """
    Витрина Rutube (Showcase API): обход resources[].url и отбор по заголовку.
    См. https://github.com/rutube/ShowcaseTutorial
    """
    slug = (feed_slug or "education").strip()
    q = (query or "").strip()
    if not slug:
        return []
    try:
        feed = _get_json(f"https://rutube.ru/api/feeds/{slug}", params={"format": "json"})
    except Exception as e:
        _log.debug("rutube feed %s failed: %s", slug, e)
        return []

    resource_urls: List[str] = []
    for tab in feed.get("tabs") or []:
        for res in tab.get("resources") or []:
            url = res.get("url")
            if url and isinstance(url, str):
                resource_urls.append(url)
            if len(resource_urls) >= max_resource_fetches:
                break
        if len(resource_urls) >= max_resource_fetches:
            break

    scored: List[Tuple[float, Dict[str, Any]]] = []
    seen_ids: Set[str] = set()
    for res_url in resource_urls:
        try:
            page = _get_json(res_url)
        except Exception:
            continue
        for item in page.get("results") or []:
            vid = _video_id_from_item(item)
            if not vid or vid in seen_ids:
                continue
            seen_ids.add(vid)
            card = _item_to_card(item, query=q)
            if card:
                scored.append((float(card.pop("_score", 0)), card))

    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:limit]]


def rutube_search_for_learning(
    query: str,
    *,
    track: Optional[str] = None,
    sphere: Optional[str] = None,
    limit: int = 3,
    prefer_course: bool = True,
) -> List[Dict[str, Any]]:
    """Поиск + витрина «Обучение»; приоритет заголовкам с «курс» / «урок»."""
    q = (query or "").strip()
    if track and track in _TRACK_SEARCH_QUERIES and not q:
        q = _TRACK_SEARCH_QUERIES[track]
    if not q:
        q = "обучение курс"

    merged: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    def add_cards(cards: List[Dict[str, Any]]) -> None:
        for c in cards:
            u = c.get("url") or ""
            if u and u not in seen:
                seen.add(u)
                merged.append(c)

    search_limit = limit + 2 if prefer_course else limit
    add_cards(rutube_search_videos(q, limit=search_limit))

    feed_slug = _FEED_BY_SPHERE.get((sphere or "").strip(), "education")
    if prefer_course and len(merged) < limit:
        add_cards(
            rutube_showcase_feed_videos(feed_slug, q, limit=limit, max_resource_fetches=5)
        )

    if prefer_course:
        merged.sort(
            key=lambda c: _course_score(str(c.get("title") or ""), q),
            reverse=True,
        )
    return merged[:limit]


def video_search_preferred(
    query: str,
    limit: int = 3,
    *,
    track: Optional[str] = None,
    sphere: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Видео для пути обучения: Rutube (без ключа), при VK_ACCESS_TOKEN — доп. VK Video."""
    from wibe_work.config import VK_ACCESS_TOKEN

    rutube_cards = rutube_search_for_learning(
        query, track=track, sphere=sphere, limit=limit, prefer_course=True
    )
    if not VK_ACCESS_TOKEN:
        return rutube_cards

    merged: List[Dict[str, Any]] = list(rutube_cards)
    seen: Set[str] = {c.get("url") or "" for c in merged}
    need = max(0, limit - len(merged))
    if need > 0:
        from wibe_work.services.learning.vk_video import vk_search_for_learning

        for c in vk_search_for_learning(
            query, track=track, sphere=sphere, limit=need, prefer_course=True
        ):
            u = c.get("url") or ""
            if u and u not in seen:
                seen.add(u)
                merged.append(c)
    return merged[:limit]
