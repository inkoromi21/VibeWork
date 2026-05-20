"""Разбор для школьников: куда идти учиться и что подтянуть, без карьерных треков."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from wibe_work.questionnaire_fields import INTEREST_SPHERES, parse_favorite_subjects
from wibe_work.services.profile_analysis_context import (
    SUBJECT_GAP_LABELS,
    analysis_mode_for_profile,
    favorite_subjects_labels,
)
from wibe_work.services.assessment_routing import parse_course_grade, resolve_assessment_track
from wibe_work.services.user_context import parse_interest_spheres

_SPHERE_LABELS: Dict[str, str] = {s["id"]: s["label"] for s in INTEREST_SPHERES}

# Варианты «куда идти» по сфере (не профессии на рынке труда)
_SCHOOL_PATH_POOLS: Dict[str, Tuple[str, ...]] = {
    "it_dev": (
        "Колледж / СПО: программирование и IT",
        "11 класс + профильная информатика и ЕГЭ",
        "Техникум с отраслевой специальностью (IT, связь, автоматизация)",
        "Университет через 2–3 года: прикладная информатика / IT",
        "Кружки, олимпиады и проекты — проверить интерес до поступления",
    ),
    "data": (
        "Колледж: аналитика, экономика, IT",
        "11 класс: математика + информатика (профиль)",
        "СПО с упором на данные и отчётность",
        "Университет: прикладная математика / аналитика",
    ),
    "design": (
        "Колледж: дизайн, графика, мультимедиа",
        "11 класс: искусство / информатика + портфолио",
        "Училище / колледж прикладного искусства",
        "Вуз: дизайн, архитектура, медиа",
    ),
    "marketing": (
        "Колледж: маркетинг, реклама, SMM",
        "11 класс: обществознание + проекты (контент, исследования)",
        "СПО: коммерция, маркетинг",
        "Вуз: маркетинг, менеджмент, медиа",
    ),
    "sales": (
        "Колледж: торговля, менеджмент, сервис",
        "11 класс + курсы переговоров / волонтёрство",
        "СПО: продажи и обслуживание",
        "Вуз: экономика, менеджмент",
    ),
    "engineering": (
        "Техникум / колледж: рабочие и инженерные специальности",
        "11 класс: физика + математика",
        "Профессионалитет / колледж по отрасли",
        "Вуз: инженерные направления",
    ),
    "medicine": (
        "Колледж: сестринское, фармация, лаборатория",
        "11 класс: биология + химия (профиль)",
        "Медколледж",
        "Вуз: медицина / биология",
    ),
    "default": (
        "Колледж (СПО) по выбранной сфере",
        "11 класс — уточнить профильные предметы",
        "Профессионалитет + практика",
        "Вуз — после осознанного выбора сферы",
    ),
}

# Предметы/навыки для «разрыва» у школьника (не job skills)
_SCHOOL_GAP_BY_INTEREST: Dict[str, List[Tuple[str, str]]] = {
    "it_dev": [
        ("math", "Математика (алгебра, логика)"),
        ("informatics", "Информатика / программирование"),
        ("english", "Английский (для документации и курсов)"),
        ("project", "Проект или олимпиада / кружок"),
        ("career_choice", "Профориентация и выбор после 9/11"),
    ],
    "data": [
        ("math", "Математика"),
        ("informatics", "Информатика / Excel"),
        ("english", "Английский"),
        ("project", "Исследовательский мини-проект"),
        ("career_choice", "Выбор колледжа / вуза"),
    ],
    "design": [
        ("art", "Рисунок и композиция"),
        ("digital", "Цифровые инструменты (Figma и др.)"),
        ("portfolio", "Портфолио (3–5 работ)"),
        ("english", "Английский"),
        ("career_choice", "Куда поступать"),
    ],
    "default": [
        ("core_subjects", "Профильные предметы в школе"),
        ("practice", "Практика: кружок, проект, подработка"),
        ("english", "Английский"),
        ("orientation", "Профориентация"),
        ("exams", "Подготовка к экзаменам / вступительным"),
    ],
}

_SCHOOL_PAIN_STEPS: Dict[str, str] = {
    "pain_school_direction": "Запишите 3 варианта «куда идти» из сценариев A/B/C и обсудите с родителями или классным — один шаг на 2 недели.",
    "pain_school_subjects": "Сопоставьте любимые предметы из анкеты с требованиями колледжа/вуза мечты — выберите один предмет для углубления на месяц.",
    "pain_school_exams": "Один предмет из блока «Обучение» и 2 короткие тренировки в неделю — без попытки закрыть всё сразу.",
    "pain_school_grades": "Начните с предмета, где уже есть интерес (из любимых) — репетитор или бесплатный курс из подборки.",
    "pain_school_parents": "Покажите родителям сценарии A/B/C из разбора — зафиксируйте один компромиссный вариант на пробу.",
    "pain_school_confidence": "Список из 5 дел из школы и хобби, где вы справились — это ваши сильные стороны.",
    "pain_career": "Запишите 3 варианта «куда идти» из сценариев A/B/C и обсудите с родителями или классным — один шаг на 2 недели.",
    "pain_no_exp": "Опыт для школьника — это проекты, кружки, олимпиады: оформите один кейс в 5 строк (что делали → результат).",
    "pain_region": "Смотрите колледжи и вузы в своём городе и соседних — плюс дистанционные программы по вашей сфере.",
    "pain_money_courses": "Бесплатные курсы и олимпиады из блока «Обучение» — один трек на месяц, без покупки дорогих пакетов.",
    "pain_interview": "Пока рано про собеседования на работу — полезнее пробное поступление и день открытых дверей в колледже.",
    "pain_overload": "Один шаг из плана на неделю: один предмет или один вариант поступления, не всё сразу.",
    "pain_low_confidence": "Список из 5 дел из школы и хобби, где вы справились — это ваши сильные стороны, не сравнение с взрослыми.",
    "pain_gap_skills": "Сопоставьте «разрыв предметов» с требованиями колледжа мечты — начните с одного предмета на месяц.",
}


def _interest_key(interest: str) -> str:
    k = (interest or "").strip()
    return k if k in _SCHOOL_PATH_POOLS else "default"


def _dominant_radar_key(axes: List[Dict[str, Any]]) -> str:
    if not axes:
        return "structure_mastery"
    best = max(axes, key=lambda a: int(a.get("value_percent") or 0))
    return str(best.get("key") or "structure_mastery")


def _score_path(name: str, dom: str, fp: int, idx: int) -> int:
    low = name.lower()
    base = 58 + (fp % 11) - (idx * 2)
    if dom == "structure_mastery" and any(x in low for x in ("матем", "информ", "техник", "it", "данн")):
        base += 8
    if dom == "people_service" and any(x in low for x in ("колледж", "сервис", "маркет", "мед")):
        base += 6
    if dom == "self_insight" and "профор" in low:
        base += 5
    if "11 класс" in low or "егэ" in low:
        base += 4
    return base


_GOAL_PATH_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "after_9_college": ("колледж", "спо", "9 класса"),
    "after_9_school": ("10–11", "11 класс", "профильн"),
    "after_11_university": ("вуз", "11 класс", "егэ"),
    "after_11_college": ("колледж", "спо", "11"),
    "undecided": ("профор", "уточнить"),
}


def _boost_score_for_post_school_goal(name: str, goal: str) -> int:
    kws = _GOAL_PATH_KEYWORDS.get((goal or "").strip(), ())
    low = name.lower()
    return 10 if any(k in low for k in kws) else 0


def _path_conflicts_exclusions(
    path_name: str,
    *,
    exclude_subject_ids: Set[str],
    exclude_sphere_ids: Set[str],
) -> bool:
    low = path_name.lower()
    if "informatics" in exclude_subject_ids and any(
        k in low for k in ("информ", "программ", "it ", " айти")
    ):
        return True
    if "math" in exclude_subject_ids and "матем" in low:
        return True
    if exclude_sphere_ids & {"it_dev", "data"} and any(
        k in low for k in ("it", "информ", "программ", "данн", "аналит")
    ):
        return True
    return False


def pick_school_path_plans(
    profile: Dict[str, Any],
    interest: str,
    axes: List[Dict[str, Any]],
    fp: int,
    *,
    exclude_sphere_ids: Optional[Set[str]] = None,
    exclude_subject_ids: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Три маршрута A/B/C: куда учиться, не кем работать."""
    ex_sp = set(exclude_sphere_ids or ())
    ex_sub = set(exclude_subject_ids or ())
    dk = _interest_key(interest)
    if dk in ex_sp:
        for alt in parse_interest_spheres(profile):
            if alt not in ex_sp and alt in _SCHOOL_PATH_POOLS:
                dk = alt
                break
        else:
            dk = "default"
    pool = list(_SCHOOL_PATH_POOLS.get(dk, _SCHOOL_PATH_POOLS["default"]))
    track = resolve_assessment_track(profile)
    if track == "school_grade9":
        pool = [p for p in pool if "9" not in p] + [
            "После 9 класса: колледж (СПО) по сфере",
            "После 9 класса: 10–11 класс с профильными предметами",
        ]
    goal = str(profile.get("post_school_goal") or "").strip()
    dom = _dominant_radar_key(axes)
    seen: Set[str] = set()
    uniq: List[str] = []
    for p in pool:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    filtered: List[str] = []
    for p in uniq:
        if _path_conflicts_exclusions(
            p, exclude_subject_ids=ex_sub, exclude_sphere_ids=ex_sp
        ):
            continue
        filtered.append(p)
    if not filtered:
        filtered = [
            p
            for p in _SCHOOL_PATH_POOLS["default"]
            if not _path_conflicts_exclusions(
                p, exclude_subject_ids=ex_sub, exclude_sphere_ids=ex_sp
            )
        ]
    scored = [
        (n, _score_path(n, dom, fp, i) + _boost_score_for_post_school_goal(n, goal))
        for i, n in enumerate(filtered)
    ]
    scored.sort(key=lambda x: -x[1])
    codes = ["A", "B", "C"]
    plans = []
    for idx, (name, raw) in enumerate(scored[:3]):
        pid = codes[idx]
        pct = max(47, min(96, raw))
        plans.append({"id": pid, "name": f"Вариант {pid}: {name}", "score_percent": pct})
    while len(plans) < 3:
        plans.append(
            {
                "id": codes[len(plans)],
                "name": f"Вариант {codes[len(plans)]}: уточнить с профориентологом",
                "score_percent": 50,
            }
        )
    best = max(plans, key=lambda p: p["score_percent"])
    spheres = parse_interest_spheres(profile)
    if not spheres and profile.get("main_sphere"):
        spheres = [str(profile.get("main_sphere")).strip()]
    sphere_lbl = ", ".join(_SPHERE_LABELS.get(s, s) for s in spheres[:2]) or "ваши интересы"
    return {
        "plans": plans,
        "best_plan_id": best["id"],
        "best_plan_name": best["name"],
        "best_avg_percent": best["score_percent"],
        "caption": "согласованность с маршрутами обучения (школа → колледж / 11 класс / вуз)",
        "focus_label": f"Сфера интересов: {sphere_lbl}. Дальше — куда учиться и что подтянуть.",
    }


def build_school_gap_analysis(
    profile: Dict[str, Any],
    interest: str,
    top_path: str,
    axes: List[Dict[str, Any]],
    fp: int,
    *,
    exclude_subject_ids: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """«Разрыв» по предметам и подготовке, не по навыкам вакансии."""
    ex_sub = set(exclude_subject_ids or ())
    dk = _interest_key(interest)
    subjects = list(_SCHOOL_GAP_BY_INTEREST.get(dk, _SCHOOL_GAP_BY_INTEREST["default"]))
    if ex_sub:
        subjects = [(sk, lab) for sk, lab in subjects if sk not in ex_sub]
    existing_labels = {lab for _, lab in subjects}
    for sid in parse_favorite_subjects(profile):
        if sid in ex_sub:
            continue
        label = SUBJECT_GAP_LABELS.get(sid)
        if label and label not in existing_labels:
            subjects.insert(0, (sid, label))
            existing_labels.add(label)
    exam = str(profile.get("exam_focus") or "").strip()
    if exam in ("oge_9", "both") and "Подготовка к ОГЭ" not in existing_labels:
        subjects.append(("exams_oge", "Подготовка к ОГЭ"))
        existing_labels.add("Подготовка к ОГЭ")
    if exam in ("ege_11", "both") and "Подготовка к ЕГЭ" not in existing_labels:
        subjects.append(("exams_ege", "Подготовка к ЕГЭ"))
        existing_labels.add("Подготовка к ЕГЭ")
    dom = _dominant_radar_key(axes)
    bars: List[Dict[str, Any]] = []
    closeness: List[int] = []
    for i, (_sk, label) in enumerate(subjects):
        base = 52 + (fp % 9) + (i * 3)
        if dom == "structure_mastery" and _sk in ("math", "informatics", "core_subjects"):
            base += 12
        if dom == "people_service" and _sk in ("career_choice", "practice", "orientation"):
            base += 10
        if dom == "self_insight" and _sk == "career_choice":
            base += 8
        fav_ids = set(parse_favorite_subjects(profile))
        if _sk in fav_ids or label in favorite_subjects_labels(profile):
            base += 14
        user_pct = max(28, min(88, base - (i * 2)))
        target_pct = min(100, user_pct + 18 + (i % 3) * 5)
        gap_pct = max(0, target_pct - user_pct)
        closeness.append(100 - min(100, gap_pct))
        bars.append(
            {
                "label": label,
                "user_percent": user_pct,
                "target_percent": target_pct,
                "gap_percent": gap_pct,
            }
        )
    overall = sum(closeness) // max(1, len(closeness))
    weak = sorted(
        ((b["label"], b["gap_percent"]) for b in bars if b["gap_percent"] > 12),
        key=lambda x: -x[1],
    )
    closing = [w[0] for w in weak[:3]] or ["Профильные предметы", "Проект или кружок", "Профориентация"]
    path_clean = re.sub(r"^Вариант\s+[ABC]:\s*", "", (top_path or "").strip(), flags=re.IGNORECASE)
    headline = "Подготовка к выбранному маршруту"
    if path_clean:
        headline = f"Что подтянуть для маршрута «{path_clean[:60]}»"
    return {
        "headline": headline,
        "overall_hp": overall,
        "bars": bars,
        "closing_skills": closing,
    }


def school_education_hints(
    profile: Dict[str, Any],
    interest: str,
    scenarios: Dict[str, Any],
) -> Dict[str, Any]:
    """Вместо матрицы вакансий — подсказки по типам учебных заведений."""
    plans = scenarios.get("plans") or []
    rows: List[Dict[str, Any]] = []
    for p in plans[:3]:
        name = re.sub(r"^Вариант\s+[ABC]:\s*", "", str(p.get("name") or ""), flags=re.IGNORECASE)
        rows.append(
            {
                "role_name": name,
                "match_percent": int(p.get("score_percent") or 50),
                "education_type": True,
            }
        )
    city = (profile.get("city") or "").strip()
    caption = "Варианты куда идти учиться (не вакансии)"
    if city:
        caption += f" — уточните программы в {city} и соседних городах"
    return {"rows": rows, "caption": caption, "school_mode": True}


def school_weekly_roadmap(
    profile: Dict[str, Any],
    top_path: str,
    interest: str,
) -> List[Dict[str, Any]]:
    path = re.sub(r"^Вариант\s+[ABC]:\s*", "", (top_path or "").strip(), flags=re.IGNORECASE)
    track = resolve_assessment_track(profile)
    w1_learn = "Сверьте требования к предметам у 2–3 колледжей или вузов по вашей сфере."
    w1_practice = "Запишите, какие предметы в школе даются легче всего — это опора для профиля."
    goal = str(profile.get("post_school_goal") or "").strip()
    exam = str(profile.get("exam_focus") or "").strip()
    fav = favorite_subjects_labels(profile)
    if track == "school_grade9":
        w1_learn = "Разберите: остаться в 10–11 классе или идти в колледж после 9 — плюсы и минусы для вашей сферы."
        w1_practice = "Поговорите с классным или профориентологом: один вариант из сценариев A/B/C."
    elif goal == "after_11_university":
        w1_learn = "Сверьте предметы ЕГЭ для вашей сферы с требованиями 2–3 вузов."
        w1_practice = "Откройте ФИПИ по выбранным предметам — один раздел кодификатора."
    elif goal == "after_9_college":
        w1_learn = "Найдите 2 колледжа по сфере и список вступительных предметов."
        w1_practice = "Запишите плюсы/минусы колледжа vs 10–11 класс для себя."
    if fav:
        w1_practice = (w1_practice + " ").strip() + f"Опора на любимые предметы: {', '.join(fav[:3])}."
    w2_learn = f"Откройте день открытых дверей или сайт программы по маршруту «{path[:50]}»."
    w2_practice = "Один мини-шаг: кружок, олимпиада, проект или пробный курс — 3–5 часов в неделю."
    if exam in ("oge_9", "ege_11", "both"):
        w2_learn += " Закрепите один предмет из анкеты в тренажёре ОГЭ/ЕГЭ."
    return [
        {
            "period": "Недели 1–2",
            "learn": w1_learn,
            "practice": w1_practice,
            "outcome": "Понятнее, какой маршрут реалистичен и что нужно подтянуть в школе.",
        },
        {
            "period": "Недели 3–4",
            "learn": w2_learn,
            "practice": w2_practice,
            "outcome": "Есть конкретный следующий шаг: предмет, поступление или проект.",
        },
    ]


def mock_school_narrative(
    profile: Dict[str, Any],
    interest: str,
    scenarios: Dict[str, Any],
    axes: List[Dict[str, Any]],
    fp: int,
    *,
    readiness_percent: int = 0,
    gap: Optional[Dict[str, Any]] = None,
) -> str:
    spheres = parse_interest_spheres(profile)
    if not spheres and profile.get("main_sphere"):
        spheres = [str(profile.get("main_sphere")).strip()]
    sphere = ", ".join(_SPHERE_LABELS.get(s, s) for s in spheres[:2]) or "ваше направление"
    course = (profile.get("course_grade") or profile.get("course_or_grade") or "").strip()
    city = (profile.get("city") or "").strip()

    plans = sorted(
        list(scenarios.get("plans") or []),
        key=lambda p: -(int(p.get("score_percent") or 0)),
    )
    best = re.sub(r"^Вариант\s+[ABC]:\s*", "", str(plans[0].get("name") or ""), flags=re.IGNORECASE) if plans else ""
    best_pct = int(plans[0].get("score_percent") or 0) if plans else None
    alt = [
        re.sub(r"^Вариант\s+[ABC]:\s*", "", str(p.get("name") or ""), flags=re.IGNORECASE)
        for p in plans[1:3]
        if re.sub(r"^Вариант\s+[ABC]:\s*", "", str(p.get("name") or ""), flags=re.IGNORECASE)
    ]

    intro = f"Вы на школьном этапе, сфера интересов: {sphere}."
    if course:
        intro += f" Сейчас: {course}."
    if city:
        intro += f" Город: {city}."
    fav = favorite_subjects_labels(profile)
    if fav:
        intro += f" Сильные предметы в анкете: {', '.join(fav[:4])}."
    goal = str(profile.get("post_school_goal") or "").strip()
    if goal:
        from wibe_work.services.profile_analysis_context import (
            _EXAM_FOCUS_RU,
            _POST_SCHOOL_GOAL_RU,
            _label,
        )

        intro += f" План: {_label(_POST_SCHOOL_GOAL_RU, goal)}."
    exam = str(profile.get("exam_focus") or "").strip()
    if exam:
        from wibe_work.services.profile_analysis_context import _EXAM_FOCUS_RU, _label

        intro += f" Готовит: {_label(_EXAM_FOCUS_RU, exam)}."
    adm = (profile.get("admission_target") or "").strip()
    if adm:
        intro += f" Цель поступления: {adm[:80]}."
    intro += " Сейчас важнее не «кем работать», а куда идти учиться и что сдавать/подтягивать."

    mid = f"Индекс готовности к выбору около {readiness_percent}% — это про ясность маршрута, не про рынок труда."
    if best and best_pct is not None:
        mid += f" Ближе всего вариант «{best}» (около {best_pct}% по ответам)."
    if alt:
        mid += f" Также смотрите: «{'» и «'.join(alt)}» — можно сравнить на практике за месяц."

    closing = list((gap or {}).get("closing_skills") or [])[:2]
    if closing:
        mid += f" Полезнее всего сейчас: {', '.join(closing)}."

    tips = (
        f"На ближайший месяц: один маршрут"
        + (f" — «{best}»" if best else "")
        + " и один предмет или кружок; обсудите с родителями или школой.",
        "Не гонитесь за взрослыми профессиями — сначала профильные предметы и пробный опыт (проект, олимпиада).",
        "После уточнения маршрута можно снова пройти тест — цифры обновятся.",
    )
    return " ".join((intro, mid, tips[fp % len(tips)]))


def school_learning_extras(
    *,
    profile: dict[str, Any],
    interest: str,
    preparation_level: str,
    scenarios: dict[str, Any],
    gap: dict[str, Any],
    profile_summary: str = "",
    user_id: str | None = None,
    eff_interest: str | None = None,
    exclude_subject_ids: Optional[Set[str]] = None,
) -> dict[str, Any]:
    """Обучение для школьника: профориентация и бесплатные треки, без «резюме и откликов»."""
    from wibe_work.services.learning_pack import build_learning_extras
    from wibe_work.services.school_subject_resources import (
        augment_school_advice_with_links,
        build_school_curated_learning_cards,
        merge_school_cards_with_catalog,
    )

    pack = build_learning_extras(
        profile=profile,
        interest=interest,
        preparation_level=preparation_level,
        scenarios=scenarios,
        gap=gap,
        profile_summary=profile_summary,
        user_id=user_id,
        eff_interest=eff_interest,
    )
    best = re.sub(
        r"^Вариант\s+[ABC]:\s*",
        "",
        str(scenarios.get("best_plan_name") or ""),
        flags=re.IGNORECASE,
    )
    fav_txt = ", ".join(favorite_subjects_labels(profile)[:4])
    exam = str(profile.get("exam_focus") or "").strip()
    exam_note = ""
    if exam in ("oge_9", "ege_11", "both"):
        exam_note = " Начните с материалов ОГЭ/ЕГЭ из блока «Обучение»."
    advice = augment_school_advice_with_links(
        f"Школьный фокус: сравните маршрут «{best[:70]}» с требованиями к предметам."
        + (f" Опирайтесь на любимые предметы ({fav_txt})." if fav_txt else "")
        + " В блоке «Обучение» — ФИПИ и тренажёры по разрыву из разбора;"
        + exam_note
        + " Добавьте один вводный курс/кружок по сфере на 2–3 недели."
    )
    curated_cards = build_school_curated_learning_cards(
        profile,
        eff_interest or interest,
        gap,
        exclude_subject_ids=set(exclude_subject_ids or ()),
    )
    catalog_cards = pack.get("learning") or []
    pack["learning"] = merge_school_cards_with_catalog(curated_cards, catalog_cards)

    from wibe_work.services.learning.growth_stages import build_growth_stages
    from wibe_work.services.school_subject_resources import build_school_learning_path_payload

    school_lp = build_school_learning_path_payload(
        user_id=user_id,
        profile=profile,
        interest=eff_interest or interest,
        preparation_level=preparation_level,
        scenarios=scenarios,
        gap=gap,
        exclude_subject_ids=set(exclude_subject_ids or ()),
    )
    pack["learning_path"] = school_lp
    pack["learning_path_detail"] = school_lp
    readiness = int(gap.get("overall_hp") or 50)
    stages = build_growth_stages(
        interest=interest,
        eff_interest=eff_interest or interest,
        preparation_level=preparation_level,
        readiness_percent=readiness,
        profile=profile,
        gap=gap,
        scenarios=scenarios,
        individual_advice=pack.get("individual_advice"),
        learning_path=school_lp,
    )
    pack["individual_advice"] = advice
    pack["growth_stages"] = stages
    pack["growth_stages_rich"] = stages
    return pack


def school_pain_first_step(pain_id: str) -> Optional[str]:
    return _SCHOOL_PAIN_STEPS.get(pain_id)
