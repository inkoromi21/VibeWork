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


def _course_score(
    title: str,
    query: str,
    *,
    description: str = "",
    track: Optional[str] = None,
) -> float:
    from wibe_work.services.learning.material_relevance import (
        _TRACK_POSITIVE,
        is_entertainment_or_sport,
    )

    t = (title or "").lower()
    desc = (description or "").lower()
    blob = f"{t} {desc}"
    if is_entertainment_or_sport({"title": title, "description": description}):
        return -100.0
    q = (query or "").lower()
    score = 0.0
    q_hits = 0
    for w in re.split(r"\s+", q):
        if len(w) > 3 and w in blob:
            score += 3.0
            q_hits += 1
        elif len(w) > 2 and w in t:
            score += 1.5
            q_hits += 1
    tr = (track or "").strip().lower()
    track_hits = 0
    if tr:
        for kw in _TRACK_POSITIVE.get(tr, ()):
            if kw in blob:
                track_hits += 1
                score += 2.0
    edu_markers = 0
    for m in _COURSE_MARKERS:
        if m in t:
            edu_markers += 1
            score += 2.0
    if "полный курс" in t or "курс с нуля" in t or "плейлист" in t:
        score += 3.0
    if "разбор" in t and q_hits == 0 and track_hits == 0:
        score -= 12.0
    # Минимум: 2 совпадения с запросом ИЛИ (1 + маркер курса + трек)
    if q_hits >= 2 or (q_hits >= 1 and edu_markers >= 1 and track_hits >= 1):
        return score
    if q_hits >= 1 and edu_markers >= 2 and track_hits >= 1:
        return score
    if q and q_hits == 0 and track_hits == 0:
        return -50.0
    if edu_markers >= 1 and track_hits >= 2:
        return score
    return -20.0


def _item_to_card(
    item: Dict[str, Any],
    *,
    query: str = "",
    track: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    url = _video_page_url(item)
    if not url:
        return None
    title = str(item.get("title") or "Видео на Rutube").strip()
    desc = str(item.get("description") or "").strip()[:300]
    if not desc and query:
        desc = (
            f"Видео по теме «{query[:60]}» — посмотрите начало и решите, "
            "подходит ли формат и темп."
        )
    elif not desc:
        desc = "Видеоурок на Rutube — кратко просмотрите и выпишите главную мысль для шага."
    sc = _course_score(title, query, description=desc, track=track)
    if sc < 6:
        return None
    kind = "курс" if sc >= 8 else "видео"
    return {
        "title": title[:200],
        "url": url,
        "kind": kind,
        "description": desc,
        "provider": "rutube",
        "source_type": "api",
        "is_free": True,
        "language": "ru",
        "_score": sc,
    }


def rutube_search_videos(
    query: str,
    limit: int = 3,
    *,
    track: Optional[str] = None,
) -> List[Dict[str, Any]]:
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
            card = _item_to_card(item, query=q, track=track)
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
    track: Optional[str] = None,
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
            card = _item_to_card(item, query=q, track=track)
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
    plan_direction: str = "",
    step_title: str = "",
) -> List[Dict[str, Any]]:
    """Поиск Rutube; витрина только если поиск пустой."""
    from wibe_work.services.learning.material_relevance import (
        build_learning_search_query,
        filter_materials_for_context,
    )
    from wibe_work.services.llm_client import llm_configured

    q = build_learning_search_query(
        query,
        track=track,
        sphere=sphere or "",
        step_title=step_title,
    )
    plan_hint = (plan_direction or step_title or "").strip()

    merged: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    def add_cards(cards: List[Dict[str, Any]]) -> None:
        for c in cards:
            u = c.get("url") or ""
            if u and u not in seen:
                seen.add(u)
                merged.append(c)

    search_limit = max(limit + 3, limit * 2) if prefer_course else limit
    add_cards(rutube_search_videos(q, limit=search_limit, track=track))

    if prefer_course and len(merged) < limit and track:
        feed_slug = _FEED_BY_SPHERE.get((sphere or "").strip(), "education")
        add_cards(
            rutube_showcase_feed_videos(
                feed_slug,
                q,
                limit=limit,
                track=track,
                max_resource_fetches=3,
            )
        )

    if prefer_course:
        merged.sort(
            key=lambda c: _course_score(
                str(c.get("title") or ""),
                q,
                description=str(c.get("description") or ""),
                track=track,
            ),
            reverse=True,
        )
    return filter_materials_for_context(
        merged[: limit + 6],
        track=track,
        sphere=sphere or "",
        plan_direction=plan_hint,
        use_llm=llm_configured(),
    )[:limit]


def video_search_preferred(
    query: str,
    limit: int = 3,
    *,
    track: Optional[str] = None,
    sphere: Optional[str] = None,
    plan_direction: str = "",
    step_title: str = "",
) -> List[Dict[str, Any]]:
    """Видео для пути обучения: Rutube (без ключа), при VK_ACCESS_TOKEN — доп. VK Video."""
    from wibe_work.config import VK_ACCESS_TOKEN

    rutube_cards = rutube_search_for_learning(
        query,
        track=track,
        sphere=sphere,
        limit=limit,
        prefer_course=True,
        plan_direction=plan_direction,
        step_title=step_title,
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
