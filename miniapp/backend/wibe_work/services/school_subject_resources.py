"""Отобранные ссылки ЕГЭ/ОГЭ и школьных предметов для режима разбора «школа».

ФИПИ — первичный официальный источник (демоверсии, кодификаторы, открытый банк).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

# Общие — всегда в начале списка рекомендаций
GENERAL_SCHOOL_LINKS: List[Dict[str, str]] = [
    {
        "title": "ФИПИ — официальный источник",
        "url": "https://fipi.ru/",
        "kind": "ЕГЭ/ОГЭ · официально",
        "description": (
            "Демоверсии, кодификаторы и открытый банк заданий ЕГЭ и ОГЭ. "
            "Ориентируйтесь по спецификации и официальным материалам в первую очередь."
        ),
        "provider": "ФИПИ",
    },
    {
        "title": "СДАМ ГИА · ЕГЭ (тренажёр)",
        "url": "https://ege.sdamgia.ru/",
        "kind": "ЕГЭ/ОГЭ · тренажёр",
        "description": (
            "Варианты, автоматическая проверка и задания по темам для всех предметов ЕГЭ "
            "(часто ищут как «решу ЕГЭ»)."
        ),
        "provider": "Сдам ГИА",
    },
    {
        "title": "СДАМ ГИА · ОГЭ (тренажёр)",
        "url": "https://oge.sdamgia.ru/",
        "kind": "ЕГЭ/ОГЭ · тренажёр",
        "description": "Тот же формат для ОГЭ (часто ищут как «решу ОГЭ»): варианты и темы по предметам.",
        "provider": "Сдам ГИА",
    },
    {
        "title": "Незнайка",
        "url": "https://neznaika.info/",
        "kind": "ЕГЭ/ОГЭ",
        "description": "Тесты, теория, сочинения и пробники; удобно для 9–11 классов.",
        "provider": "Незнайка",
    },
    {
        "title": "Умскул",
        "url": "https://umschool.net/",
        "kind": "онлайн-школа",
        "description": "Предметы ЕГЭ/ОГЭ, вебинары, домашние задания, пробники и приложение.",
        "provider": "Умскул",
    },
    {
        "title": "Фоксфорд",
        "url": "https://foxford.ru/",
        "kind": "курсы",
        "description": "Подготовка к ЕГЭ, ОГЭ, олимпиадам и школьной программе.",
        "provider": "Фоксфорд",
    },
    {
        "title": "Вебиум",
        "url": "https://webium.ru/",
        "kind": "онлайн",
        "description": "Лайв-занятия, кураторы, пробники и интенсивы.",
        "provider": "Вебиум",
    },
]

# По предметам (добавляются по релевантности к «разрыву» и сфере)
SUBJECT_LINKS: Dict[str, List[Dict[str, str]]] = {
    "math": [
        {
            "title": "math100.ru — профильная математика",
            "url": "https://math100.ru/",
            "kind": "математика",
            "description": "Задачи, разборы, теория и сложные номера для профиля.",
            "provider": "math100",
        },
        {
            "title": "СДАМ ГИА · математика",
            "url": "https://ege.sdamgia.ru/math",
            "kind": "математика",
            "description": "Большой банк задач по математике (база и профиль).",
            "provider": "Сдам ГИА",
        },
        {
            "title": "Алексей Ларин — варианты",
            "url": "https://alexlarin.net/",
            "kind": "математика",
            "description": "Авторские и пробные варианты, сложные задачи.",
            "provider": "AlexLarin.net",
        },
    ],
    "russian": [
        {
            "title": "Грамота.ру",
            "url": "https://gramota.ru/",
            "kind": "русский язык",
            "description": "Орфография, пунктуация и правила русского языка.",
            "provider": "Грамота.ру",
        },
        {
            "title": "СДАМ ГИА · русский язык",
            "url": "https://rus-ege.sdamgia.ru/",
            "kind": "русский язык",
            "description": "Тестовая часть, сочинение и изложение для ЕГЭ.",
            "provider": "Сдам ГИА",
        },
    ],
    "informatics": [
        {
            "title": "КЕГЭ — Евгений Поляков",
            "url": "https://kpolyakov.spb.ru/school/ege/",
            "kind": "информатика",
            "description": "Задания ЕГЭ, Python, алгоритмы и тренажёры по информатике.",
            "provider": "Поляков",
        },
        {
            "title": "informatics.msk.ru",
            "url": "https://informatics.msk.ru/",
            "kind": "информатика",
            "description": "Практика программирования и олимпиадные/школьные задачи.",
            "provider": "informatics.msk.ru",
        },
    ],
    "physics": [
        {
            "title": "СДАМ ГИА · физика",
            "url": "https://phys-ege.sdamgia.ru/",
            "kind": "физика",
            "description": "Тренажёр задач ЕГЭ по физике.",
            "provider": "Сдам ГИА",
        },
        {
            "title": "GetAClass — физика",
            "url": "https://getaclass.ru/",
            "kind": "физика",
            "description": "Видеоуроки и объяснения тем (в т.ч. «физика в опытах»).",
            "provider": "GetAClass",
        },
    ],
    "chemistry": [
        {
            "title": "СДАМ ГИА · химия",
            "url": "https://chem-ege.sdamgia.ru/",
            "kind": "химия",
            "description": "Задачи и варианты ЕГЭ по химии.",
            "provider": "Сдам ГИА",
        },
        {
            "title": "Химия ЕГЭ — Степенин",
            "url": "https://stepenin.ru/",
            "kind": "химия",
            "description": "Теория, тесты, цепочки реакций и разборы (популярный курс).",
            "provider": "Степенин",
        },
    ],
    "biology": [
        {
            "title": "СДАМ ГИА · биология",
            "url": "https://bio-ege.sdamgia.ru/",
            "kind": "биология",
            "description": "Тренажёр заданий ЕГЭ по биологии.",
            "provider": "Сдам ГИА",
        },
        {
            "title": "BioFAQ (био-фак)",
            "url": "https://bio-faq.ru/",
            "kind": "биология",
            "description": "Конспекты, теория и тесты по биологии.",
            "provider": "BioFAQ",
        },
    ],
    "social": [
        {
            "title": "СДАМ ГИА · обществознание",
            "url": "https://soc-ege.sdamgia.ru/",
            "kind": "обществознание",
            "description": "Задания и варианты для подготовки к ЕГЭ.",
            "provider": "Сдам ГИА",
        },
        {
            "title": "НезЛО Антона Чубукова",
            "url": "https://nezlo.ru/",
            "kind": "обществознание",
            "description": "Сильная подготовка к обществознанию: теория и разбор формата ЕГЭ.",
            "provider": "НезЛО",
        },
    ],
    "english": [
        {
            "title": "СДАМ ГИА · английский",
            "url": "https://eng-ege.sdamgia.ru/",
            "kind": "английский",
            "description": "Задания ЕГЭ по английскому языку.",
            "provider": "Сдам ГИА",
        },
        {
            "title": "Puzzle English",
            "url": "https://puzzle-english.com/",
            "kind": "английский",
            "description": "Аудирование, грамматика и словарь через практику.",
            "provider": "Puzzle English",
        },
    ],
}

# Сфера интересов → какие предметы чаще всего стоит подсветить (дополнительно к разрыву)
INTEREST_DEFAULT_SUBJECTS: Dict[str, Set[str]] = {
    "it_dev": {"math", "informatics", "english"},
    "data": {"math", "informatics", "english"},
    "design": {"russian", "english"},
    "marketing": {"russian", "social", "english"},
    "sales": {"russian", "social", "english"},
    "engineering": {"math", "physics"},
    "medicine": {"biology", "chemistry", "russian"},
    "default": set(),
}


def _norm_url(u: str) -> str:
    s = (u or "").strip().lower().rstrip("/")
    if s.startswith("http://"):
        s = "https://" + s[len("http://") :]
    return s


def _subjects_from_gap(gap: Dict[str, Any]) -> Set[str]:
    out: Set[str] = set()
    bars = gap.get("bars") or []
    for bar in bars:
        lab = str(bar.get("label") or "").lower()
        if "матем" in lab:
            out.add("math")
        if "информ" in lab or "программ" in lab:
            out.add("informatics")
        if "англий" in lab:
            out.add("english")
        if "русск" in lab:
            out.add("russian")
        if "физик" in lab:
            out.add("physics")
        if "хим" in lab:
            out.add("chemistry")
        if "биолог" in lab:
            out.add("biology")
        if "обществ" in lab:
            out.add("social")
    for lbl in gap.get("closing_skills") or []:
        t = str(lbl).lower()
        if "матем" in t:
            out.add("math")
        if "информ" in t:
            out.add("informatics")
        if "англий" in t:
            out.add("english")
        if "предмет" in t or "егэ" in t or "огэ" in t:
            out.add("_generic_subjects_hint")
    return out


def _interest_key(interest: str) -> str:
    k = (interest or "").strip()
    return k if k in INTEREST_DEFAULT_SUBJECTS else "default"


def pick_school_subject_ids(
    profile: Dict[str, Any],
    interest: str,
    gap: Dict[str, Any],
    *,
    exclude_subject_ids: Optional[Set[str]] = None,
) -> Set[str]:
    """Какие предметные блоки ссылок показать (ключи SUBJECT_LINKS)."""
    from wibe_work.questionnaire_fields import parse_favorite_subjects

    from_gap = _subjects_from_gap(gap)
    from_gap.discard("_generic_subjects_hint")

    ints = INTEREST_DEFAULT_SUBJECTS.get(_interest_key(interest), set())
    from_profile = set(parse_favorite_subjects(profile))

    merged = from_gap | ints | from_profile
    if not merged:
        merged = {"math", "russian", "informatics", "english"}
    excluded = set(exclude_subject_ids or ())
    if excluded:
        merged = {s for s in merged if s not in excluded}
    if not merged:
        merged = {s for s in ("math", "russian", "physics", "english", "social") if s not in excluded}
    return merged


def link_cards_to_learning_items(links: Sequence[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Формат карточек как в learning.engine (build_learning_for_analysis)."""
    out: List[Dict[str, Any]] = []
    for item in links:
        out.append(
            {
                "title": item["title"],
                "url": item["url"],
                "kind": item.get("kind") or "школа",
                "description": item.get("description") or "",
                "provider": item.get("provider"),
                "step_title": "Подготовка к предметам (ЕГЭ/ОГЭ)",
            }
        )
    return out


def build_school_curated_learning_cards(
    profile: Dict[str, Any],
    interest: str,
    gap: Dict[str, Any],
    *,
    max_subject_cards: int = 8,
    max_total: int = 20,
    exclude_subject_ids: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """Общие ссылки ФИПИ/тренажёры плюс предметы по разрыву и сфере."""
    subjects = pick_school_subject_ids(
        profile, interest, gap, exclude_subject_ids=exclude_subject_ids
    )

    subject_items: List[Dict[str, str]] = []
    for sid in sorted(subjects):
        for row in SUBJECT_LINKS.get(sid, ()):
            subject_items.append(dict(row))

    # Уникальность URL, сохраняем порядок: сначала общие, потом предметы
    seen: Set[str] = set()
    ordered: List[Dict[str, str]] = []

    def add_batch(batch: Iterable[Dict[str, str]]) -> None:
        for row in batch:
            key = _norm_url(row["url"])
            if not key or key in seen:
                continue
            seen.add(key)
            ordered.append(row)

    add_batch(GENERAL_SCHOOL_LINKS)
    add_batch(subject_items)

    capped = ordered[:max_total]
    # Ограничим только предметную часть после общих: блок ФИПИ и тренажёры всегда в начале
    n_gen = len(GENERAL_SCHOOL_LINKS)
    if len(capped) > n_gen + max_subject_cards:
        capped = capped[: n_gen + max_subject_cards]

    return link_cards_to_learning_items(capped)


def augment_school_advice_with_links(advice_text: str) -> str:
    """Короткое напоминание про ФИПИ в тексте совета."""
    if not advice_text.strip():
        return advice_text
    if re.search(r"фипи\.ru|ФИПИ", advice_text, re.IGNORECASE):
        return advice_text
    return (
        advice_text.rstrip()
        + " Официальные материалы и банк заданий начинайте с ФИПИ (fipi.ru), затем тренируйтесь на тренажёрах из блока «Обучение»."
    )


def _subject_resources_for_step(subject_id: str, *, limit: int = 4) -> List[Dict[str, Any]]:
    """Ресурсы шага в формате learning_path (как career engine)."""
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for row in GENERAL_SCHOOL_LINKS[:2]:
        u = _norm_url(row["url"])
        if u in seen:
            continue
        seen.add(u)
        out.append(
            {
                "title": row["title"],
                "url": row["url"],
                "kind": row.get("kind") or "ЕГЭ/ОГЭ",
                "description": row.get("description") or "",
                "provider": row.get("provider"),
            }
        )
    for row in SUBJECT_LINKS.get(subject_id, ())[:limit]:
        u = _norm_url(row["url"])
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(
            {
                "title": row["title"],
                "url": row["url"],
                "kind": row.get("kind") or "предмет",
                "description": row.get("description") or "",
                "provider": row.get("provider"),
            }
        )
    return out[: limit + 2]


def build_school_learning_path_payload(
    *,
    user_id: Optional[str],
    profile: Dict[str, Any],
    interest: str,
    preparation_level: str,
    scenarios: Optional[Dict[str, Any]] = None,
    gap: Optional[Dict[str, Any]] = None,
    exclude_subject_ids: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Пошаговый путь школьника — тот же контракт, что career learning_path (Any.do)."""
    from wibe_work.services.learning.adapters import integration_status
    from wibe_work.services.learning.assessment_signals import build_assessment_signals
    from wibe_work.services.learning.progress import (
        apply_progress_to_steps,
        compute_metrics,
        get_progress_map,
    )
    from wibe_work.services.learning.substeps import attach_substeps_to_step
    from wibe_work.services.profile_analysis_context import SUBJECT_GAP_LABELS

    gap = gap or {}
    scenarios = scenarios or {}
    subject_ids = sorted(
        pick_school_subject_ids(
            profile, interest, gap, exclude_subject_ids=exclude_subject_ids
        )
    )
    sphere = _interest_key(interest)
    path_id = f"school_{sphere}"
    if subject_ids:
        path_id = f"{path_id}_{'_'.join(subject_ids)}"

    best = re.sub(
        r"^Вариант\s+[ABC]:\s*",
        "",
        str(scenarios.get("best_plan_name") or ""),
        flags=re.IGNORECASE,
    ).strip()
    exam = str(profile.get("exam_focus") or "").strip()
    exam_note = ""
    if exam in ("oge_9", "both"):
        exam_note = " ОГЭ — с демоверсий и банка заданий на ФИПИ."
    if exam in ("ege_11", "both"):
        exam_note = (exam_note + " ЕГЭ — по спецификации и открытому банку ФИПИ.").strip()

    steps_out: List[Dict[str, Any]] = []
    order = 1

    orient_goal = (
        f"Сравните маршрут «{best[:70]}» с предметами к сдаче и зафиксируйте 2–3 варианта с классным или родителями."
        if best
        else "Выберите 2–3 варианта из сценариев A/B/C и обсудите с классным или родителями."
    )
    steps_out.append(
        {
            "step_id": "school_orient",
            "order": order,
            "title": "Сверить маршрут и сферу",
            "goal": orient_goal,
            "duration_hint": "1–2 нед.",
            "skills": ["career_map"],
            "checkpoint": orient_goal,
            "resources": [
                {
                    "title": GENERAL_SCHOOL_LINKS[0]["title"],
                    "url": GENERAL_SCHOOL_LINKS[0]["url"],
                    "kind": GENERAL_SCHOOL_LINKS[0].get("kind") or "профориентация",
                    "description": GENERAL_SCHOOL_LINKS[0].get("description") or "",
                    "provider": GENERAL_SCHOOL_LINKS[0].get("provider"),
                }
            ],
            "status": "pending",
        }
    )
    order += 1

    for sid in subject_ids:
        label = SUBJECT_GAP_LABELS.get(sid, sid)
        goal = (
            f"Подтяните «{label}»: 2–3 занятия в неделю по материалам ниже."
            + (exam_note if exam_note else " Начните с ФИПИ, затем тренажёр.")
        )
        if preparation_level == "weak":
            goal = (
                f"База по «{label}»: 20–30 минут в день, один блок тем из тренажёра."
                + (exam_note if exam_note else "")
            )
        steps_out.append(
            {
                "step_id": f"sub_{sid}",
                "order": order,
                "title": label,
                "goal": goal,
                "duration_hint": "2–3 нед.",
                "skills": [sid],
                "checkpoint": goal,
                "resources": _subject_resources_for_step(sid),
                "status": "pending",
            }
        )
        order += 1

    sphere_label = interest
    try:
        from wibe_work.questionnaire_fields import INTEREST_SPHERES

        for sp in INTEREST_SPHERES:
            if sp.get("id") == interest:
                sphere_label = str(sp.get("label") or interest)
                break
    except Exception:
        pass
    probe_goal = (
        f"Проба сферы «{sphere_label}»: кружок, олимпиада или мини-проект на 2–3 недели — "
        "понять, нравится ли направление."
    )
    steps_out.append(
        {
            "step_id": "school_sphere_probe",
            "order": order,
            "title": "Проба сферы интересов",
            "goal": probe_goal,
            "duration_hint": "2–3 нед.",
            "skills": ["orientation"],
            "checkpoint": probe_goal,
            "resources": [],
            "status": "pending",
        }
    )

    steps_out = [attach_substeps_to_step(s) for s in steps_out]
    progress: Dict[str, str] = {}
    if user_id and path_id:
        progress = get_progress_map(user_id, path_id)
    steps_out = apply_progress_to_steps(steps_out, progress)
    metrics = compute_metrics(steps_out)

    signals = build_assessment_signals(
        profile=profile,
        interest=interest,
        preparation_level=preparation_level,
        scenarios=scenarios,
        gap=gap,
    )

    priority_skills: List[str] = []
    for bar in gap.get("bars") or []:
        lab = bar.get("label") or bar.get("key")
        if lab:
            priority_skills.append(str(lab))

    title = "Подготовка к предметам и поступлению"
    if best:
        title = f"Школьный путь: {best[:55]}"

    return {
        "path_id": path_id,
        "title": title,
        "sphere": sphere,
        "track": None,
        "preparation_level": preparation_level,
        "steps": steps_out,
        "metrics": metrics,
        "priority_skills_from_gap": priority_skills[:5],
        "assessment_signals": {
            "sphere": signals.get("sphere"),
            "analysis_mode": "school",
            "education_grade": signals.get("education_grade"),
        },
        "integration": integration_status(),
    }


def merge_school_cards_with_catalog(
    curated: List[Dict[str, Any]],
    catalog_cards: List[Dict[str, Any]],
    *,
    max_total: int = 22,
) -> List[Dict[str, Any]]:
    """Кураторские ссылки первыми, затем карточки каталога без дублей URL."""
    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []

    def take(cards: List[Dict[str, Any]]) -> None:
        for c in cards:
            if len(out) >= max_total:
                return
            u = _norm_url(str(c.get("url") or ""))
            if not u or u in seen:
                continue
            seen.add(u)
            out.append(c)

    take(curated)
    take(catalog_cards or [])
    return out
