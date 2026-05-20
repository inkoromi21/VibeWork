"""Формат банка вопросов как на сайте: до 10 задач по сфере + блок профориентации (школа — без задач по сфере)."""

from __future__ import annotations

from typing import Any

from wibe_work.services.assessment_bundle import get_assessment_bundle
from wibe_work.services.user_context import parse_interest_spheres
from wibe_work.questionnaire_fields import SPHERE_TO_WEB_INTEREST


def sphere_id_for_profile(profile: dict[str, Any], form_interest: str) -> str:
    spheres = parse_interest_spheres(profile)
    if spheres:
        return spheres[0]
    raw = (form_interest or "").strip()
    if raw in SPHERE_TO_WEB_INTEREST:
        return raw
    low = raw.lower()
    for sid, web in SPHERE_TO_WEB_INTEREST.items():
        if str(web).lower() == low:
            return sid
    return "other"


def _norm_options(q: dict) -> list[dict]:
    out = []
    for o in q.get("options") or []:
        oid = o.get("id") or o.get("k")
        label = o.get("label") or o.get("t") or ""
        if oid:
            out.append({"k": str(oid), "t": str(label)})
    return out


def _to_website_bank(questions: list[dict], *, renumber_from: int = 1) -> list[dict]:
    bank = []
    for i, q in enumerate(questions):
        bank.append(
            {
                "id": renumber_from + i,
                "text": str(q.get("text") or ""),
                "options": _norm_options(q),
                "_global_id": q.get("id"),
                "module": q.get("module"),
            }
        )
    return bank


def quiz_bundle_for_web(profile: dict[str, Any], form_interest: str) -> dict[str, Any]:
    """
    Тест 1 — до 10 вопросов по выбранной сфере (для школьников пустой список).
    Тест 2 — ориентация + карьера (id 1..N) с блоками modules.
    """
    sphere_key = sphere_id_for_profile(profile, form_interest)
    bundle = get_assessment_bundle(profile, sphere_key)

    technical = _to_website_bank(bundle.get("technical") or [], renumber_from=1)
    orient = list(bundle.get("orientation") or [])
    career = list(bundle.get("career") or bundle.get("personality") or [])
    second_block = _to_website_bank(orient + career, renumber_from=1)

    modules_ui = []
    for mod in bundle.get("modules") or []:
        mod_id = mod.get("id")
        if mod_id == "sphere":
            continue
        qs = mod.get("questions") or []
        if mod_id == "career":
            qs = career
        bank = _to_website_bank(qs, renumber_from=1)
        if mod_id != "sphere" and bank:
            modules_ui.append({"id": mod_id, "title": mod.get("title"), "questions": bank})

    return {
        "quiz_key": sphere_key,
        "track_id": bundle.get("track_id"),
        "track_label": bundle.get("track_label"),
        "track_hint": bundle.get("track_hint"),
        "test_grade": bundle.get("test_grade"),
        "questions": technical,
        "personality_questions": second_block,
        "orientation_count": len(orient),
        "assessment_focus": bundle.get("assessment_focus", "proforientation"),
        "career_module_title": bundle.get("career_module_title", "Карьера и мотивы"),
        "career_count": len(career),
        "personality_count": len(second_block),
        "modules": modules_ui,
        "global_question_map": {
            "technical": [q.get("_global_id") for q in technical],
            "personality": [q.get("_global_id") for q in second_block],
        },
    }
