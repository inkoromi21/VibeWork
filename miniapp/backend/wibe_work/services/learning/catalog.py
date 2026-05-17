"""Загрузка каталога ресурсов и путей обучения."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from wibe_work.miniapp_paths import data_file

_CATALOG_PATH = data_file("learning_catalog.json")
_PATHS_PATH = data_file("learning_paths.json")


@lru_cache(maxsize=1)
def load_catalog() -> Dict[str, Any]:
    if not _CATALOG_PATH.is_file():
        return {"resources": []}
    with _CATALOG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_paths() -> Dict[str, Any]:
    if not _PATHS_PATH.is_file():
        return {"paths": []}
    with _PATHS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def resources_by_id() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in load_catalog().get("resources") or []:
        rid = str(r.get("id") or "")
        if rid:
            out[rid] = r
    return out


def get_resource(resource_id: str) -> Optional[Dict[str, Any]]:
    return resources_by_id().get(resource_id)


def resource_to_card(r: Dict[str, Any], *, source_type: str = "curated") -> Dict[str, Any]:
    return {
        "id": r.get("id"),
        "title": r.get("title") or "Материал",
        "url": r.get("url") or "#",
        "kind": r.get("kind") or r.get("format") or "ресурс",
        "description": r.get("description") or "",
        "provider": r.get("provider") or "curated",
        "source_type": source_type,
        "is_free": bool(r.get("is_free", True)),
        "language": r.get("language") or "ru",
    }


def pick_path(
    sphere: str,
    track: Optional[str],
    preparation: str,
) -> Optional[Dict[str, Any]]:
    paths = load_paths().get("paths") or []
    sphere = (sphere or "other").strip()
    track = (track or "").strip().lower()
    prep = preparation if preparation in ("weak", "medium", "strong") else "medium"

    scored: List[tuple[int, Dict[str, Any]]] = []
    for p in paths:
        spheres = p.get("spheres") or []
        tracks = [str(t).lower() for t in (p.get("tracks") or [])]
        levels = p.get("levels") or ["weak", "medium", "strong"]
        if sphere not in spheres and "other" not in spheres:
            continue
        if prep not in levels:
            continue
        score = 0
        if sphere in spheres:
            score += 10
        if track and track in tracks:
            score += 25
        if not tracks and p.get("id") == "general_career":
            score += 1
        if p.get("id", "").startswith("it_dev") and sphere == "it_dev":
            score += 5
        scored.append((score, p))

    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    best_score, best = scored[0]
    if track and best_score < 25:
        for score, p in scored:
            if track in [str(t).lower() for t in (p.get("tracks") or [])]:
                return p
    return best
