from typing import Any, Dict, List, Optional

import requests

from wibe_work.config import HH_API_BASE, HH_USER_AGENT


def _headers() -> Dict[str, str]:
    return {
        "User-Agent": HH_USER_AGENT,
        "Accept": "application/json",
    }


def suggest_area_id(city: str) -> Optional[str]:
    if not city or not str(city).strip():
        return None
    r = requests.get(
        f"{HH_API_BASE}/suggests/areas",
        params={"text": str(city).strip()},
        headers=_headers(),
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    items = data.get("items") or []
    if not items:
        return None
    return str(items[0].get("id"))


def suggest_areas(text: str, *, limit: int = 15) -> List[Dict[str, str]]:
    """
    Подсказки городов и регионов через API hh.ru (/suggests/areas).
    Сначала показываем варианты, у которых название начинается с запроса (как на hh.ru),
    при нехватке — остальные из ответа API.
    """
    t = (text or "").strip()
    if len(t) < 2:
        return []
    try:
        r = requests.get(
            f"{HH_API_BASE}/suggests/areas",
            params={"text": t},
            headers=_headers(),
            timeout=12,
        )
        r.raise_for_status()
        data = r.json()
    except requests.RequestException:
        return []

    raw_items = data.get("items") or []
    out: List[Dict[str, str]] = []
    seen: set[str] = set()
    for it in raw_items:
        tid = it.get("id")
        name = (it.get("text") or "").strip()
        if tid is None or not name:
            continue
        sid = str(tid)
        key = sid + "\n" + name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": sid, "text": name})

    prefix = t.lower()
    pref_match = [x for x in out if x["text"].lower().startswith(prefix)]
    chosen = pref_match[:limit] if pref_match else out[:limit]
    return chosen


def search_vacancies(params: Dict[str, Any]) -> Dict[str, Any]:
    """GET /vacancies — параметры как в OpenAPI hh.ru."""
    clean = {k: v for k, v in params.items() if v is not None and v != ""}
    r = requests.get(
        f"{HH_API_BASE}/vacancies",
        params=clean,
        headers=_headers(),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def slim_vacancy_items(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for it in raw.get("items") or []:
        emp = it.get("employer") or {}
        area = it.get("area") or {}
        out.append(
            {
                "id": it.get("id"),
                "name": it.get("name"),
                "alternate_url": it.get("alternate_url"),
                "employer_name": emp.get("name"),
                "area_name": area.get("name"),
                "salary": it.get("salary"),
                "published_at": it.get("published_at"),
                "snippet": it.get("snippet"),
                "experience": (it.get("experience") or {}).get("name"),
                "employment": (it.get("employment") or {}).get("name"),
                "schedule": (it.get("schedule") or {}).get("name"),
            }
        )
    return out
