"""Тест: тест не дублирует анкету; вопросы соответствуют уровню и сфере."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.assessment_bundle import get_assessment_bundle
from wibe_work.services.assessment_questionnaire_overlap import (
    question_matches_interest_meta,
    question_matches_level,
    question_overlaps_filled_profile_field,
)
from wibe_work.services.assessment_routing import uses_job_search_assessment

_INTERESTS = ("it_dev", "medicine", "design", "marketing", "sales")


def _texts(bundle: dict) -> list[str]:
    return [str(q.get("text") or "").lower() for q in bundle.get("questions") or []]


def _any_match(patterns: list[str], texts: list[str]) -> bool:
    for pat in patterns:
        rx = re.compile(pat, re.I)
        if any(rx.search(t) for t in texts):
            return True
    return False


def _school_profile_filled() -> dict:
    return {
        "education_detail": "school_8_11",
        "course_grade": "10 класс",
        "age": 16,
        "city": "Казань",
        "interest_spheres": '["it_dev"]',
        "favorite_subjects": '["math", "informatics"]',
        "like_to_do": "робототехника",
        "post_school_goal": "after_11_university",
        "exam_focus": "ege_11",
        "hours_per_week": 10,
    }


def _spo_profile_filled() -> dict:
    return {
        "education_detail": "spo",
        "course_grade": "2 курс",
        "study_form": "fulltime",
        "age": 19,
        "city": "Москва",
        "interest_spheres": '["marketing"]',
        "like_to_do": "контент",
        "work_format_preference": "hybrid",
        "work_schedule": "after_classes",
        "target_salary": 40000,
        "hours_per_week": 15,
        "preparation_level": "medium",
        "internship_ready": "yes",
    }


def _university_profile_filled() -> dict:
    return {
        "education_detail": "univ_bachelor",
        "course_grade": "3 курс",
        "study_form": "fulltime",
        "age": 21,
        "city": "СПб",
        "interest_spheres": '["it_dev"]',
        "like_to_do": "разработка",
        "work_format_preference": "remote",
        "work_schedule": "flex",
        "target_salary": 120000,
        "hours_per_week": 20,
        "preparation_level": "strong",
        "internship_ready": "paid_only",
    }


# --- Дубли с анкетой (при заполненном профиле) ---


@pytest.mark.parametrize("interest", _INTERESTS)
def test_school_no_questionnaire_duplicates_when_profile_filled(interest: str) -> None:
    profile = _school_profile_filled()
    bundle = get_assessment_bundle(profile, interest)
    texts = _texts(bundle)
    assert bundle["test_grade"] == "school"
    assert not _any_match(
        [
            r"после 9 или 11",
            r"принять решение \(профиль, колледж, вуз\)",
            r"разбираться в задачах по математике или информатике",
            r"ваканс",
            r"должност",
            r"зарплат",
        ],
        texts,
    )
    # Модуль profil целиком убран при favorite_subjects
    assert not any("скорее нравится" in t and "математик" in t for t in texts)


@pytest.mark.parametrize("interest", _INTERESTS)
def test_spo_no_questionnaire_duplicates_when_profile_filled(interest: str) -> None:
    profile = _spo_profile_filled()
    bundle = get_assessment_bundle(profile, interest)
    texts = _texts(bundle)
    assert bundle["test_grade"] == "vocational"
    assert bundle["technical_count"] == 10
    assert not _any_match(
        [
            r"гибкий график и свобода формата",
            r"стабильный офис с понятными правилами",
            r"после 9 или 11",
            r"одноклассник",
            r"огэ",
        ],
        texts,
    )


@pytest.mark.parametrize("interest", _INTERESTS)
def test_university_no_questionnaire_duplicates_when_profile_filled(interest: str) -> None:
    profile = _university_profile_filled()
    bundle = get_assessment_bundle(profile, interest)
    texts = _texts(bundle)
    assert uses_job_search_assessment(profile)
    assert bundle["orientation_count"] == 0
    assert not _any_match(
        [
            r"формат работ",
            r"приблизит вас к желаемой должности",
            r"зарплата, график и условия",
            r"первую работу или стажировку",
            r"одноклассник",
            r"школьн",
        ],
        texts,
    )


def test_school_empty_profile_still_has_orientation() -> None:
    profile = {"education_detail": "school_8_11", "course_grade": "9 класс"}
    bundle = get_assessment_bundle(profile, "it_dev")
    assert bundle["orientation_count"] > 0
    assert bundle["personality_count"] >= 4


def test_overlap_helper_maps_fields() -> None:
    profile = _university_profile_filled()
    q = {"text": "Что сильнее всего приблизит вас к желаемой должности в ближайший месяц?"}
    assert question_overlaps_filled_profile_field(q, profile) == "preparation_level"


# --- Соответствие уровню ---


@pytest.mark.parametrize("interest", _INTERESTS)
def test_school_questions_are_school_level(interest: str) -> None:
    profile = {"education_detail": "school_8_11", "course_grade": "11 класс"}
    bundle = get_assessment_bundle(profile, interest)
    for q in bundle["questions"]:
        assert question_matches_level(q, "school"), q.get("text")


@pytest.mark.parametrize("interest", _INTERESTS)
def test_university_questions_are_not_school_wording(interest: str) -> None:
    profile = {"education_detail": "univ_bachelor", "course_grade": "2 курс"}
    bundle = get_assessment_bundle(profile, interest)
    for q in bundle["questions"]:
        assert question_matches_level(q, "university"), q.get("text")


@pytest.mark.parametrize("interest", _INTERESTS)
def test_spo_questions_are_vocational_not_school_exam(interest: str) -> None:
    profile = {"education_detail": "spo", "course_grade": "1 курс"}
    bundle = get_assessment_bundle(profile, interest)
    for q in bundle["questions"]:
        assert question_matches_level(q, "vocational"), q.get("text")


# --- Соответствие сфере (orientation + technical) ---


@pytest.mark.parametrize("interest", _INTERESTS)
def test_orientation_respects_interest_filters(interest: str) -> None:
    profile = {"education_detail": "school_8_11", "course_grade": "10 класс"}
    bundle = get_assessment_bundle(profile, interest)
    for q in bundle.get("orientation") or []:
        assert question_matches_interest_meta(q, interest), (
            interest,
            q.get("text"),
            q.get("only_interests"),
            q.get("skip_interests"),
        )


@pytest.mark.parametrize(
    "interest,need,forbid",
    [
        ("it_dev", ("программ", "код", "api", "данн", "информ"), ("медицин", "сестрин")),
        # medicine → общий банк сферы (без IT-лексики)
        ("medicine", ("задач", "мотивац", "навык", "обратн"), ("api", "git", "deploy", "ci/cd")),
        ("design", ("дизайн", "figma", "визуал", "макет"), ("api", "баз данных sql")),
    ],
)
def test_university_technical_matches_interest_sphere(
    interest: str, need: tuple[str, ...], forbid: tuple[str, ...]
) -> None:
    profile = {"education_detail": "univ_bachelor", "course_grade": "2 курс"}
    bundle = get_assessment_bundle(profile, interest)
    assert len(bundle["technical"]) == 10
    blob = " ".join(_texts({"questions": bundle["technical"]}))
    assert any(n in blob for n in need), (interest, blob[:200])
    assert not any(f in blob for f in forbid), (interest, blob[:200])


def test_weights_length_matches_questions_after_filtering() -> None:
    for profile in (_school_profile_filled(), _spo_profile_filled(), _university_profile_filled()):
        bundle = get_assessment_bundle(profile, "it_dev")
        assert len(bundle["weights_matrix"]) == bundle["total_count"]
        assert len(bundle["questions"]) == bundle["total_count"]
