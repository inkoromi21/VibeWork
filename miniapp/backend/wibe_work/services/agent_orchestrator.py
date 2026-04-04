from typing import Any, Dict, List

from wibe_work.services.career_navigator import build_navigator
from wibe_work.services.diagnostics import run_diagnostics
from wibe_work.services.job_search import match_jobs_for_user
from wibe_work.services.mts_match import match_mts_roles
from wibe_work.services.user_pain_mapping import align_pains
from wibe_work.services.recommendations import run_recommendations
from wibe_work.services.user_context import load_competencies, load_profile


def build_full_report(user_id: str) -> Dict[str, Any]:
    profile = load_profile(user_id)
    competencies = load_competencies(user_id)
    diagnostics = run_diagnostics(profile, competencies)
    recommendations = run_recommendations(profile, competencies)
    navigator = build_navigator(profile, competencies)
    jobs = match_jobs_for_user(user_id, profile, competencies)
    pains = align_pains(profile)
    mts = match_mts_roles(profile, competencies, top_n=5)

    summary_parts: List[str] = []
    if diagnostics.get("profile_completeness_score", 0) < 0.7:
        summary_parts.append("Профиль стоит дополнить для более точных рекомендаций.")
    if recommendations.get("primary_direction"):
        summary_parts.append(
            f"Ключевое направление: {recommendations['primary_direction']}."
        )
    top_job = jobs["vacancies"][0]["title"] if jobs["vacancies"] else None
    if top_job:
        summary_parts.append(f"Самая релевантная вакансия в каталоге: «{top_job}».")
    if pains.get("matched_pains"):
        summary_parts.append(
            f"Учтены продуктовые «боли» ({len(pains['matched_pains'])} совпадений по тексту профиля)."
        )
    if mts.get("top_roles"):
        summary_parts.append(
            f"Лучшее совпадение с матрицей ролей: «{mts['top_roles'][0]['title']}»."
        )

    return {
        "user_id": user_id,
        "executive_summary": " ".join(summary_parts)
        if summary_parts
        else "Заполните профиль и компетенции, чтобы агент дал персональный отчёт.",
        "diagnostics": diagnostics,
        "recommendations": recommendations,
        "career_navigator": navigator,
        "job_matches": jobs,
        "pain_alignment": pains,
        "mts_matrix_match": mts,
    }
