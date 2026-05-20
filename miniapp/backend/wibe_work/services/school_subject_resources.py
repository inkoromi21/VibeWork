"""Отобранные ссылки ЕГЭ/ОГЭ и школьных предметов для режима разбора «школа».

ФИПИ — первичный официальный источник (демоверсии, кодификаторы, открытый банк).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Sequence, Set

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


def pick_school_subject_ids(profile: Dict[str, Any], interest: str, gap: Dict[str, Any]) -> Set[str]:
    """Какие предметные блоки ссылок показать (ключи SUBJECT_LINKS)."""
    from_gap = _subjects_from_gap(gap)
    from_gap.discard("_generic_subjects_hint")

    ints = INTEREST_DEFAULT_SUBJECTS.get(_interest_key(interest), set())

    merged = from_gap | ints
    if not merged:
        merged = {"math", "russian", "informatics", "english"}
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
) -> List[Dict[str, Any]]:
    """Общие ссылки ФИПИ/тренажёры плюс предметы по разрыву и сфере."""
    subjects = pick_school_subject_ids(profile, interest, gap)

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
