"""Сборка опроса: модули профориентации + 10 по сфере + 5 карьерных."""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from wibe_work.services.aptitude_quiz import (
    _personality_questions,
    _technical_questions,
    get_pro_weights_matrix_for_interest,
)
from wibe_work.services.aptitude_quiz_grading import compute_quiz_grade, quiz_grade_hint, quiz_grade_label
from wibe_work.services.assessment_modules import module_question_slice
from wibe_work.services.assessment_routing import (
    module_title,
    resolve_assessment_track,
    track_meta,
    track_modules,
)

WRow = List[tuple]


def _format_question(
    qid: int,
    raw: Dict[str, Any],
    *,
    module_id: str,
    block: str,
) -> Dict[str, Any]:
    opts = raw.get("options") or []
    return {
        "id": qid,
        "text": str(raw.get("text") or ""),
        "options": [
            {"id": o.get("id"), "label": o.get("label") or o.get("t") or ""} for o in opts
        ],
        "block": block,
        "module": module_id,
        "methodology": module_id,
    }


def _build_orientation(profile: Dict[str, Any], track_id: str, start_id: int) -> tuple[List[Dict[str, Any]], List[List[tuple]], int]:
    questions: List[Dict[str, Any]] = []
    weights: List[List[tuple]] = []
    qid = start_id
    for mod_id in track_modules(track_id):
        for raw in module_question_slice(mod_id, track_id):
            questions.append(_format_question(qid, raw, module_id=mod_id, block="orientation"))
            weights.append(list(raw["weights"]))
            qid += 1
    return questions, weights, qid


def get_assessment_bundle(profile: Dict[str, Any], interest: str) -> Dict[str, Any]:
    """
    Полный набор вопросов для пользователя.
    orientation (1..O) → technical (O+1..O+10) → career/personality (O+11..O+15).
    """
    meta = track_meta(profile)
    track_id = meta["track_id"]
    grade = meta["test_grade"]

    orientation, orient_weights, next_id = _build_orientation(profile, track_id, 1)
    orient_count = len(orientation)

    technical = copy.deepcopy(_technical_questions(interest))
    for i, q in enumerate(technical):
        q["id"] = next_id + i
        q["block"] = "technical"
        q["module"] = "sphere"
        opts = q.get("options") or []
        q["options"] = [
            {"id": o.get("id") or o.get("k"), "label": o.get("label") or o.get("t") or ""}
            for o in opts
        ]
    next_id += len(technical)

    expert = copy.deepcopy(_personality_questions(interest, grade))
    for q in expert:
        q["id"] = next_id
        next_id += 1
        q["block"] = "career"
        q["module"] = "career"

    all_questions = orientation + technical + expert

    modules_out: List[Dict[str, Any]] = []
    for mod_id in track_modules(track_id):
        mod_qs = [q for q in orientation if q.get("module") == mod_id]
        if mod_qs:
            modules_out.append(
                {
                    "id": mod_id,
                    "title": module_title(mod_id),
                    "questions": mod_qs,
                }
            )
    modules_out.append(
        {
            "id": "sphere",
            "title": "Задачи в вашей сфере",
            "questions": technical,
        }
    )
    modules_out.append(
        {
            "id": "career",
            "title": "Карьера и мотивы",
            "questions": expert,
        }
    )

    core_matrix = get_pro_weights_matrix_for_interest(interest)
    full_weights = orient_weights + list(core_matrix)

    return {
        "interest": (interest or "").strip() or "other",
        "track_id": track_id,
        "track_label": meta["track_label"],
        "track_hint": meta["track_hint"],
        "test_grade": grade,
        "test_grade_label": quiz_grade_label(grade),
        "test_grade_hint": quiz_grade_hint(grade),
        "orientation_count": orient_count,
        "technical_count": len(technical),
        "career_count": len(expert),
        "total_count": len(all_questions),
        "orientation_offset": 0,
        "core_offset": orient_count,
        "core_question_ids": [q["id"] for q in technical + expert],
        "modules": modules_out,
        "orientation": orientation,
        "technical": technical,
        "personality": expert,
        "career": expert,
        "questions": all_questions,
        "weights_matrix": full_weights,
        "personality_count": len(expert),
    }


def expected_question_ids(profile: Dict[str, Any], interest: str) -> List[int]:
    bundle = get_assessment_bundle(profile, interest)
    return [int(q["id"]) for q in bundle["questions"]]


def orientation_offset_for_profile(profile: Dict[str, Any], interest: str) -> int:
    return get_assessment_bundle(profile, interest)["core_offset"]
