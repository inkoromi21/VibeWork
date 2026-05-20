"""Интеграция веб-разбора с каталогом обучения (wibe_work.learning)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "miniapp" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from wibe_work.services.learning_pack import build_learning_extras, normalize_preparation_level  # noqa: E402
from wibe_work.questionnaire_fields import SPHERE_TO_WEB_INTEREST  # noqa: E402
from wibe_work.services.user_context import parse_interest_spheres  # noqa: E402

from app.api_schemas import CareerDirection, DiagnosisPayload, GapAnalysis, Interest, LearningResource  # noqa: E402
from app.profession_packs import resolve_profession_pack  # noqa: E402

_WEB_TO_SPHERE: dict[str, str] = {}
for _sid, _web in SPHERE_TO_WEB_INTEREST.items():
    _WEB_TO_SPHERE[str(_web).lower()] = _sid
    _WEB_TO_SPHERE[_sid] = _sid


def _sphere_from_payload(payload: DiagnosisPayload) -> str:
    extra = payload.profile_extra or {}
    spheres = parse_interest_spheres(extra)
    if spheres:
        return spheres[0]
    intr = payload.interests[0].value.lower()
    if intr in _WEB_TO_SPHERE:
        return _WEB_TO_SPHERE[intr]
    for sid, web in SPHERE_TO_WEB_INTEREST.items():
        if str(web).lower() == intr:
            return sid
    return "other"


def _track_from_pack(interest: Interest) -> str | None:
    pk = resolve_profession_pack(interest).key
    if pk == "tech":
        return "backend"
    if pk == "design":
        return "design"
    if pk == "data":
        return "data"
    return None


def _profile_dict(payload: DiagnosisPayload) -> dict[str, Any]:
    p = dict(payload.profile_extra or {})
    p.setdefault("age", payload.age)
    p["preparation_level"] = normalize_preparation_level(str(payload.preparation_level))
    if payload.motivation:
        p.setdefault("motivation_ai", payload.motivation)
    if not p.get("main_sphere"):
        p["main_sphere"] = _sphere_from_payload(payload)
    return p


def _gap_dict(gap: GapAnalysis) -> dict[str, Any]:
    return {
        "headline": gap.headline,
        "overall_hp": gap.overall_hp,
        "bars": [
            {
                "label": b.label,
                "key": b.label,
                "user_percent": b.user_percent,
                "target_percent": b.target_percent,
                "gap_percent": b.gap_percent,
            }
            for b in gap.bars
        ],
        "closing_skills": list(gap.closing_skills or []),
    }


def _scenarios_from_directions(directions: list[CareerDirection], interest: Interest) -> dict[str, Any]:
    plans = [
        {
            "id": d.plan_code,
            "name": d.name,
            "score_percent": d.match_score,
        }
        for d in directions
    ]
    track = _track_from_pack(interest)
    inf: dict[str, Any] = {}
    if track:
        inf["track_id"] = track
        if directions:
            inf["label"] = directions[0].name
    return {
        "plans": plans,
        "best_plan_name": directions[0].name if directions else interest.value,
        "inferred_profession": inf or None,
    }


def _cards_to_learning_resources(cards: list[dict[str, Any]]) -> list[LearningResource]:
    out: list[LearningResource] = []
    for c in cards:
        url = (c.get("url") or "").strip()
        if not url or url == "#":
            continue
        out.append(
            LearningResource(
                title=str(c.get("title") or "Материал"),
                type=str(c.get("kind") or "ресурс"),
                description=str(c.get("description") or c.get("step_title") or "")[:400],
                url=url,
            )
        )
    return out


def build_learning_pack_for_website(
    payload: DiagnosisPayload,
    *,
    directions: list[CareerDirection],
    gap: GapAnalysis,
    profile_summary: str,
) -> dict[str, Any]:
    """Каталог, пути обучения, индивидуальные советы и этапы роста с материалами."""
    profile = _profile_dict(payload)
    sphere = _sphere_from_payload(payload)
    scenarios = _scenarios_from_directions(directions, payload.interests[0])
    gap_d = _gap_dict(gap)

    extras = build_learning_extras(
        profile=profile,
        interest=sphere,
        preparation_level=str(payload.preparation_level),
        scenarios=scenarios,
        gap=gap_d,
        profile_summary=profile_summary,
        user_id=None,
        eff_interest=sphere,
    )
    cards = extras.get("learning") or []
    resources = _cards_to_learning_resources(cards)
    return {
        "learning_resources": resources,
        "learning_path_detail": extras.get("learning_path_detail"),
        "individual_advice": extras.get("individual_advice"),
        "growth_stages_rich": extras.get("growth_stages_rich"),
    }
