"""Сборка пути обучения и карточек для разбора."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from wibe_work.services.learning.adapters import integration_status, run_dynamic_adapter
from wibe_work.services.learning.catalog import (
    get_resource,
    pick_path,
    resource_to_card,
    resources_by_id,
)
from wibe_work.services.learning.progress import (
    apply_progress_to_steps,
    compute_metrics,
    get_progress_map,
)


def _infer_track(scenarios: Optional[Dict[str, Any]]) -> Optional[str]:
    if not scenarios:
        return None
    inf = scenarios.get("inferred_profession") or {}
    tid = inf.get("track_id")
    return str(tid) if tid else None


def _resolve_sphere(interest: str, profile: Dict[str, Any]) -> str:
    from wibe_work.services.career_analysis import _resolve_effective_interest

    return _resolve_effective_interest(profile, interest)


def _enrich_step_resources(
    step: Dict[str, Any],
    *,
    sphere: Optional[str] = None,
    track: Optional[str] = None,
) -> List[Dict[str, Any]]:
    by_id = resources_by_id()
    seen_urls: set[str] = set()
    out: List[Dict[str, Any]] = []

    def add(card: Dict[str, Any]) -> None:
        url = (card.get("url") or "").strip()
        if not url or url in seen_urls:
            return
        seen_urls.add(url)
        out.append(card)

    for rid in step.get("resource_ids") or []:
        r = by_id.get(str(rid))
        if r:
            add(resource_to_card(r, source_type="curated"))

    for spec in step.get("dynamic") or []:
        dyn = dict(spec)
        if track and "track" not in dyn:
            dyn["track"] = track
        if sphere and "sphere" not in dyn:
            dyn["sphere"] = sphere
        for card in run_dynamic_adapter(dyn):
            add(card)

    return out[:8]


def build_learning_path_payload(
    *,
    user_id: Optional[str],
    profile: Dict[str, Any],
    interest: str,
    preparation_level: str,
    scenarios: Optional[Dict[str, Any]] = None,
    gap: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    sphere = _resolve_sphere(interest, profile)
    track = _infer_track(scenarios)
    path_def = pick_path(sphere, track, preparation_level)
    if not path_def:
        return {
            "path_id": None,
            "title": "Путь обучения",
            "steps": [],
            "metrics": compute_metrics([]),
            "integration": integration_status(),
        }

    path_id = str(path_def.get("id") or "")
    steps_out: List[Dict[str, Any]] = []
    for raw in sorted(path_def.get("steps") or [], key=lambda s: int(s.get("order") or 0)):
        resources = _enrich_step_resources(raw, sphere=sphere, track=track)
        steps_out.append(
            {
                "step_id": raw.get("id"),
                "order": raw.get("order"),
                "title": raw.get("title"),
                "goal": raw.get("goal"),
                "duration_hint": raw.get("duration_hint"),
                "skills": raw.get("skills") or [],
                "checkpoint": raw.get("goal"),
                "resources": resources,
                "status": "pending",
            }
        )

    progress: Dict[str, str] = {}
    if user_id and path_id:
        progress = get_progress_map(user_id, path_id)
    steps_out = apply_progress_to_steps(steps_out, progress)
    metrics = compute_metrics(steps_out)

    priority_skills: List[str] = []
    if gap:
        for bar in gap.get("bars") or []:
            lab = bar.get("label") or bar.get("key")
            if lab:
                priority_skills.append(str(lab))

    return {
        "path_id": path_id,
        "title": path_def.get("title") or "Путь обучения",
        "sphere": sphere,
        "track": track,
        "preparation_level": preparation_level,
        "steps": steps_out,
        "metrics": metrics,
        "priority_skills_from_gap": priority_skills[:5],
        "integration": integration_status(),
    }


def build_learning_for_analysis(
    *,
    user_id: Optional[str],
    profile: Dict[str, Any],
    interest: str,
    preparation_level: str,
    scenarios: Optional[Dict[str, Any]] = None,
    gap: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Карточки для блока «Обучение» + полный learning_path."""
    path_payload = build_learning_path_payload(
        user_id=user_id,
        profile=profile,
        interest=interest,
        preparation_level=preparation_level,
        scenarios=scenarios,
        gap=gap,
    )
    cards: List[Dict[str, Any]] = []
    seen: set[str] = set()
    steps = path_payload.get("steps") or []
    current_idx = int((path_payload.get("metrics") or {}).get("current_step_index") or 0)
    # текущий и следующий шаг — в приоритете для карточек
    order_indices = [current_idx]
    if current_idx + 1 < len(steps):
        order_indices.append(current_idx + 1)
    for i, step in enumerate(steps):
        if i not in order_indices and len(cards) >= 6:
            continue
        for res in step.get("resources") or []:
            url = res.get("url") or ""
            if url in seen:
                continue
            seen.add(url)
            cards.append(
                {
                    "title": res.get("title"),
                    "url": url,
                    "kind": res.get("kind") or "ресурс",
                    "description": (res.get("description") or step.get("goal") or "")[:300],
                    "step_title": step.get("title"),
                    "provider": res.get("provider"),
                }
            )
            if len(cards) >= 8:
                break
        if len(cards) >= 8:
            break

    if not cards:
        r = get_resource("stepik_python")
        if r:
            cards.append(resource_to_card(r))

    return {"learning": cards, "learning_path": path_payload}


def get_integration_status() -> Dict[str, Any]:
    return integration_status()
