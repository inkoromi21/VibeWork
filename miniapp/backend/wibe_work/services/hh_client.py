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
