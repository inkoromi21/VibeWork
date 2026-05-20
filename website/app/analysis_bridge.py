"""Единый разбор wibe_work для веб-формы (школа vs карьера)."""

from __future__ import annotations

import logging
import re
from typing import Any

from wibe_work.services.assessment_bundle import get_assessment_bundle
from wibe_work.services.career_analysis import build_analysis_result
from wibe_work.services.profile_analysis_context import analysis_mode_for_profile
from wibe_work.services.learning_pack import normalize_preparation_level
from wibe_work.services.quiz_web_bundle import quiz_bundle_for_web, sphere_id_for_profile

from app.api_schemas import (
    AiPipelineStep,
    AnalysisResult,
    CareerDirection,
    CareerStage,
    DiagnosisPayload,
    Education,
    EmployerFeedbackHint,
    GapAnalysis,
    GapSkillBar,
    InsightTile,
    Interest,
    LearningResource,
    MtsMatrixMatch,
    PreparationBranch,
    StyleFitBar,
    WeekPlanItem,
)
from app.learning_bridge import _cards_to_learning_resources, _profile_dict, _sphere_from_payload

logger = logging.getLogger(__name__)

_PREP_FROM_API = {
    "слабый": "weak",
    "средний": "medium",
    "сильный": "strong",
}

_EDUCATION_LABEL = {
    Education.SCHOOL: "школа",
    Education.COLLEGE: "колледж",
    Education.UNIVERSITY: "вуз",
}


def _prep_level(payload: DiagnosisPayload) -> str:
    raw = str(payload.preparation_level or "средний").strip().lower()
    return normalize_preparation_level(_PREP_FROM_API.get(raw, "medium"))


def _web_interest_label(payload: DiagnosisPayload) -> str:
    return payload.interests[0].value if payload.interests else "IT"


def _answers_from_payload(
    payload: DiagnosisPayload,
    profile: dict[str, Any],
    sphere: str,
) -> list[dict[str, Any]]:
    web = quiz_bundle_for_web(profile, _web_interest_label(payload))
    gmap = web.get("global_question_map") or {}
    tech_globals = list(gmap.get("technical") or [])
    pers_globals = list(gmap.get("personality") or [])

    by_global: dict[int, str] = {}
    for a in payload.test_answers or []:
        idx = int(a.question_id) - 1
        if 0 <= idx < len(tech_globals) and tech_globals[idx]:
            by_global[int(tech_globals[idx])] = str(a.choice).strip()
    for a in payload.personality_test_answers or []:
        idx = int(a.question_id) - 1
        if 0 <= idx < len(pers_globals) and pers_globals[idx]:
            by_global[int(pers_globals[idx])] = str(a.choice).strip()

    bundle = get_assessment_bundle(profile, sphere)
    out: list[dict[str, Any]] = []
    for q in bundle.get("questions") or []:
        qid = int(q["id"])
        if qid in by_global:
            out.append({"question_id": qid, "choice": by_global[qid]})
    return out


def _gap_model(gap: dict[str, Any]) -> GapAnalysis:
    bars = [
        GapSkillBar(
            label=str(b.get("label") or ""),
            user_percent=int(b.get("user_percent") or 0),
            target_percent=int(b.get("target_percent") or 0),
            gap_percent=int(b.get("gap_percent") or 0),
        )
        for b in gap.get("bars") or []
    ]
    return GapAnalysis(
        headline=str(gap.get("headline") or ""),
        overall_hp=int(gap.get("overall_hp") or 0),
        bars=bars,
        closing_skills=list(gap.get("closing_skills") or []),
    )


def _directions_from_scenarios(scenarios: dict[str, Any], *, school: bool) -> list[CareerDirection]:
    plans = scenarios.get("plans") or []
    focus = str(scenarios.get("focus_label") or "").strip()
    codes = ("A", "B", "C")
    out: list[CareerDirection] = []
    for i, p in enumerate(plans[:3]):
        code = str(p.get("id") or codes[min(i, 2)])
        if code not in codes:
            code = codes[min(i, 2)]
        name = str(p.get("name") or "")
        score = int(p.get("score_percent") or 50)
        rationale = focus or (
            "Маршрут обучения по ответам теста."
            if school
            else "Направление по ответам теста и профилю."
        )
        steps = (
            ["Сверьте предметы и требования колледжа/вуза.", "Один кружок или проект на месяц."]
            if school
            else ["Уточните стек и вакансии в городе.", "Один практический шаг на 2 недели."]
        )
        out.append(
            CareerDirection(
                plan_code=code,  # type: ignore[arg-type]
                name=name,
                match_score=score,
                rationale=rationale,
                first_steps=steps,
                salary_motivation_hint=None if school else None,
            )
        )
    return out


def _mts_rows(mts: Any) -> list[MtsMatrixMatch]:
    if isinstance(mts, list):
        rows = mts
        school = False
    else:
        rows = (mts or {}).get("rows") or []
        school = bool((mts or {}).get("school_mode"))
    out: list[MtsMatrixMatch] = []
    for i, r in enumerate(rows[:8]):
        title = str(r.get("role_name") or r.get("title") or "")
        pct = int(r.get("match_percent") or r.get("percent") or r.get("relevance") or 0)
        tag = "education" if school or r.get("education_type") else ""
        out.append(
            MtsMatrixMatch(
                id=f"edu_{i}" if school else f"mts_{i}",
                title=title,
                profession_tag=tag,
                relevance=max(0, min(100, pct)),
                reason=str((mts or {}).get("caption") or "")[:200] if school and i == 0 else "",
                requirements=[],
                duties=[],
            )
        )
    return out


def _style_fit(full: dict[str, Any]) -> list[StyleFitBar]:
    axes = (full.get("style_radar") or {}).get("axes") or []
    return [
        StyleFitBar(
            label=str(a.get("label") or ""),
            percent=int(a.get("value_percent") or 0),
            hint=None,
        )
        for a in axes
    ]


def _weekly(items: list[dict[str, Any]]) -> list[WeekPlanItem]:
    out: list[WeekPlanItem] = []
    for w in items or []:
        topics = [t for t in (w.get("learn"), w.get("practice"), w.get("outcome")) if t]
        if not topics and w.get("topics"):
            topics = list(w["topics"])
        out.append(
            WeekPlanItem(
                week_range=str(w.get("period") or w.get("week_range") or "Недели"),
                topics=[str(t) for t in topics if t],
            )
        )
    return out


def _learning_resources(full: dict[str, Any]) -> list[LearningResource]:
    path = full.get("learning_path")
    if isinstance(path, dict) and path.get("steps"):
        cards: list[dict[str, Any]] = []
        for st in path.get("steps") or []:
            for r in st.get("resources") or []:
                cards.append(r)
        if cards:
            return _cards_to_learning_resources(cards)
    cards = full.get("learning") or []
    if isinstance(cards, list) and cards:
        return _cards_to_learning_resources(cards)
    return []


def _career_stages_from_growth(full: dict[str, Any]) -> list[CareerStage]:
    rich = full.get("growth_stages_rich") or full.get("growth_stages") or []
    stages: list[CareerStage] = []
    for g in rich:
        if not isinstance(g, dict):
            continue
        stages.append(
            CareerStage(
                title=str(g.get("title") or "Этап"),
                subtitle=str(g.get("subtitle") or ""),
                description=str(g.get("detail") or g.get("description") or ""),
                typical_duration=str(g.get("horizon") or "по ситуации"),
                focus_areas=[],
                milestones=[],
                transition_hint=str(g.get("when_next") or ""),
            )
        )
    return stages


def _school_insight_tiles(
    full: dict[str, Any],
    directions: list[CareerDirection],
) -> list[InsightTile]:
    readiness = int((full.get("readiness") or {}).get("value_percent") or 0)
    best = directions[0] if directions else None
    best_short = ""
    if best:
        best_short = re.sub(r"^Вариант\s+[ABC]:\s*", "", best.name, flags=re.IGNORECASE)
        if len(best_short) > 44:
            best_short = best_short[:41] + "…"
    cap = str((full.get("scenarios") or {}).get("caption") or "")
    return [
        InsightTile(
            title="Ясность маршрута",
            value=f"{readiness}%",
            subtitle="Насколько по ответам понятно, куда идти учиться дальше (не оценка для работодателя).",
        ),
        InsightTile(
            title="Лучший вариант A/B/C",
            value=f"{best.match_score}%" if best else "—",
            subtitle=f"Ближе всего: «{best_short or '—'}»." if best_short else cap or "Сравните три маршрута обучения.",
        ),
        InsightTile(
            title="Предметы и подготовка",
            value=f"{(full.get('gap_analysis') or {}).get('overall_hp', 0)}%",
            subtitle="Близость к целевому уровню по школьным предметам и профориентации из блока «разрыв».",
        ),
        InsightTile(
            title="Практика и профориентация",
            value="фокус",
            subtitle="Кружок, олимпиада или разговор с классным — один шаг из дорожной карты на 2 недели.",
        ),
    ]


def _normalize_advice(advice: Any, directions: list[CareerDirection], *, school: bool) -> dict[str, Any] | None:
    if isinstance(advice, dict) and advice.get("by_plan"):
        return advice
    if isinstance(advice, str) and advice.strip():
        pid = "A"
        if directions:
            pid = str(directions[0].plan_code or "A")
        title = directions[0].name if directions else ("Маршрут обучения" if school else "План A")
        return {
            "by_plan": {
                pid: {
                    "title": title,
                    "intro": advice.strip(),
                    "steps": [],
                    "sections": [{"title": "Следующий шаг", "steps": [advice.strip()]}],
                }
            },
            "source": "school" if school else "rules",
        }
    return None


async def build_analysis_unified(payload: DiagnosisPayload) -> AnalysisResult:
    """Разбор через miniapp/wibe_work: школа — куда учиться; СПО/вуз — карьера в сфере."""
    from app.career_advisor import (
        AI_PIPELINE_STEPS,
        build_career_stages,
        build_employer_feedback_hint,
        build_grade_plan,
        build_insight_tiles,
        build_preparation_branch,
        mock_ai_narrative,
    )

    profile = _profile_dict(payload)
    if not profile.get("education_detail"):
        edu = payload.education
        if edu == Education.SCHOOL:
            profile.setdefault("education_detail", "school_8_11")
        elif edu == Education.COLLEGE:
            profile.setdefault("education_detail", "college_spo")
        elif edu == Education.UNIVERSITY:
            profile.setdefault("education_detail", "univ_bachelor")

    sphere = _sphere_from_payload(payload)
    answers = _answers_from_payload(payload, profile, sphere)
    if not answers:
        raise ValueError("Нужны ответы на тест 2 (профориентация).")

    prep = _prep_level(payload)
    education = _EDUCATION_LABEL.get(payload.education, str(payload.education.value))
    profile_extra = {"city": profile.get("city"), "age": profile.get("age")}

    full = build_analysis_result(
        profile,
        profile_extra,
        sphere,
        education,
        prep,
        answers,
        question_timings_ms=[t.ms for t in payload.question_timings] or None,
    )

    mode = str(full.get("analysis_mode") or analysis_mode_for_profile(profile))
    school = mode == "school"
    scenarios = full.get("scenarios") or {}
    directions = _directions_from_scenarios(scenarios, school=school)
    gap = _gap_model(full.get("gap_analysis") or {})
    mts_rows = _mts_rows(full.get("mts_matrix"))
    style_fit = _style_fit(full)
    top_track = directions[0].name if directions else sphere
    top_clean = re.sub(r"^(Вариант|План)\s+[ABC]:\s*", "", top_track, flags=re.IGNORECASE).strip()

    if school:
        insight_tiles = _school_insight_tiles(full, directions)
        grade_plan: list = []
        employer = EmployerFeedbackHint(
            headline="Школьный этап",
            body="Сейчас важнее выбор учебного маршрута и предметов, чем отклики на вакансии.",
            suggestion="Сравните варианты A/B/C с родителями или классным и зафиксируйте один шаг на месяц.",
        )
    else:
        ts: dict[str, int] = {}
        insight_tiles = build_insight_tiles(
            payload, ts, directions, mts_rows, payload.interests[0]
        )
        grade_plan = build_grade_plan(top_clean, payload.interests[0])
        employer = build_employer_feedback_hint(top_clean)

    narrative = str(full.get("ai_narrative") or "").strip()
    if not narrative:
        narrative = mock_ai_narrative(payload, directions)

    stages = _career_stages_from_growth(full)
    if not stages:
        stages = build_career_stages(primary_track=top_clean)

    learning = _learning_resources(full)
    advice = _normalize_advice(full.get("individual_advice"), directions, school=school)

    learn_cards = full.get("learning") or []
    if isinstance(learn_cards, list):
        learn_cards = [c for c in learn_cards if isinstance(c, dict)]
    else:
        learn_cards = []

    return AnalysisResult(
        profile_summary=str(full.get("profile_summary") or ""),
        behavioral_hint=full.get("behavioral_hint"),
        readiness=full.get("readiness") if isinstance(full.get("readiness"), dict) else None,
        learning_cards=learn_cards or None,
        directions=directions,
        gap_analysis=gap,
        learning_path=learning,
        learning_path_detail=full.get("learning_path_detail"),
        individual_advice=advice,
        growth_stages_rich=full.get("growth_stages_rich"),
        career_stages=stages,
        skill_plan=[],
        weekly_roadmap=_weekly(full.get("weekly_roadmap") or []),
        ai_narrative=narrative,
        mts_matrix=mts_rows,
        style_fit=style_fit,
        insight_tiles=insight_tiles,
        grade_plan=grade_plan,
        preparation_branch=build_preparation_branch(payload),
        employer_feedback=employer,
        ai_pipeline=list(AI_PIPELINE_STEPS),
        analysis_mode=mode,
    )
