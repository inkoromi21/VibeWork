"""Построение результата разбора: метрики для UI + внутренние поля для чата."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from wibe_work.miniapp_paths import data_file
from wibe_work.services.llm_client import fetch_llm_completion, llm_configured
from wibe_work.services.llm_prompts import (
    ANALYSIS_NARRATIVE_SCHOOL_SYSTEM,
    ANALYSIS_NARRATIVE_SYSTEM,
    build_analysis_user_prompt,
)
from wibe_work.services.aptitude_quiz import get_pro_weights_matrix_for_interest, letter_to_index
from wibe_work.questionnaire_fields import INTEREST_SPHERES
from wibe_work.services.user_context import (
    _PAIN_LABELS,
    _PRIORITY_RU,
    _WORK_FORMAT_RU,
    coach_profile_snippet,
    parse_interest_spheres,
    profile_skill_blob,
)
from wibe_work.services.user_pain_mapping import align_pains
from wibe_work.services.learning_pack import build_learning_extras
from wibe_work.services.career_analysis_school import (
    analysis_mode_for_profile,
    build_school_gap_analysis,
    mock_school_narrative,
    pick_school_path_plans,
    school_education_hints,
    school_learning_extras,
    school_pain_first_step,
    school_weekly_roadmap,
)

_SKILL_ORDER = (
    "programming",
    "analytics",
    "communication",
    "design",
    "management",
)
_SKILL_TO_PACK_KEY = {
    "programming": "программирование",
    "analytics": "аналитика",
    "communication": "коммуникации",
    "design": "дизайн",
    "management": "организация_и_управление",
}

_MINIAPP_TO_WEBSITE_INTEREST = {
    "it_dev": "IT",
    "data": "данные_и_AI",
    "design": "дизайн",
    "marketing": "маркетинг",
    "sales": "продажи",
    "engineering": "инженерия",
    "mgmt": "продукт_и_PMO",
    "finance": "финансы_и_контроль",
    "hr_edu": "HR_и_рекрутинг",
    "logistics": "логистика",
    "medicine": "наука",
    "education": "бизнес",
    "creative": "дизайн",
    "sport": "бизнес",
    "other": "IT",
}

_SPHERE_LABELS: Dict[str, str] = {s["id"]: s["label"] for s in INTEREST_SPHERES}

_PREP_LABELS: Dict[str, str] = {
    "weak": "начальный",
    "medium": "средний",
    "strong": "уверенный",
}

_PAIN_FIRST_STEP: Dict[str, str] = {
    "pain_career": "Зафиксируйте 3 гипотезы из сценариев A/B/C и проверьте одну коротким проектом за 2 недели.",
    "pain_no_exp": "Добавьте в резюме один учебный или волонтёрский кейс с цифрой результата — даже без официальной работы.",
    "pain_region": "Сузьте поиск: удалёнка/гибрид и 2–3 города с реальными вакансиями по вашей сфере.",
    "pain_money_courses": "Выберите один бесплатный трек из блока «Обучение» и доведите до артефакта (конспект или мини-проект).",
    "pain_interview": "Три тренировочных ответа на типовые вопросы по сфере — вслух, с таймером 2 минуты.",
    "pain_overload": "Один шаг на эту неделю из этапов роста; остальное — в список «потом».",
    "pain_low_confidence": "Список из 5 навыков из повседневности (школа, хобби, помощь людям) — без сравнения с «идеалом».",
    "pain_gap_skills": "Сопоставьте топ-3 разрыва навыков с одной вакансией мечты и закройте самый узкий за месяц.",
}

_MTS_PATH = data_file("mts_role_matrix.json")


def _load_mts_roles() -> List[Dict[str, Any]]:
    p = Path(_MTS_PATH)
    if not p.is_file():
        return []
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("roles") or [])


def _profile_blob(profile: Dict[str, Any], profile_extra: Dict[str, Any]) -> str:
    parts = [json.dumps(profile, ensure_ascii=False), json.dumps(profile_extra, ensure_ascii=False)]
    return " ".join(parts).lower()


def _answer_vector(answers: List[Dict[str, Any]]) -> List[int]:
    out: List[int] = []
    for a in answers:
        ch = a.get("choice") or a.get("choice_id")
        if isinstance(ch, int):
            idx = max(0, min(3, int(ch)))
        else:
            idx = letter_to_index(str(ch))
        out.append(idx)
    return out


def _readiness_percent(vec: List[int], preparation: str) -> int:
    if not vec:
        return 35
    scores = [(v + 1) * 25 for v in vec]
    avg = sum(scores) / len(scores)
    prep_bonus = {"weak": -6, "medium": 0, "strong": 10}.get(preparation, 0)
    return int(max(12, min(100, round(avg * 0.82 + prep_bonus))))


def _build_readiness_insight(
    readiness: int,
    preparation_level: str,
    axes: List[Dict[str, Any]],
    gap: Optional[Dict[str, Any]],
    scenarios: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Краткое «почему столько» и плюсы/минусы для карточки готовности."""
    prep = {"weak": "начальный", "medium": "средний", "strong": "уверенный"}.get(
        preparation_level, "средний"
    )
    pros: List[str] = []
    cons: List[str] = []

    if axes:
        by_val = sorted(axes, key=lambda a: int(a.get("value_percent") or 0), reverse=True)
        for a in by_val[:2]:
            pct = int(a.get("value_percent") or 0)
            if pct >= 55:
                pros.append(f"{a.get('label', 'Ось')}: {pct}%")
        for a in list(reversed(by_val))[:2]:
            pct = int(a.get("value_percent") or 0)
            if pct < 52:
                cons.append(f"{a.get('label', 'Ось')} — {pct}%")

    if gap:
        hp = gap.get("overall_hp")
        if hp is not None and int(hp) >= 68:
            pros.append(f"Навыки близки к цели трека (~{int(hp)}%)")
        for label in (gap.get("closing_skills") or [])[:2]:
            cons.append(f"Подтянуть: {label}")

    best = (scenarios or {}).get("best_avg_percent")
    if best is not None and int(best) >= 58:
        pros.append(f"Сценарий плана ~{int(best)}%")

    if readiness < 40:
        why = (
            f"{readiness}% — стартовая зона: до цели трека ещё путь, "
            "опирайтесь на план из разбора и навыки из разрыва."
        )
    elif readiness < 55:
        why = (
            f"{readiness}% — смешанный профиль: сильные стороны есть, "
            "узкие места по осям и навыкам снижают индекс."
        )
    elif readiness < 70:
        why = (
            f"{readiness}% — рабочий уровень: к цели близко, "
            "добейте пункты «закрыть в первую очередь»."
        )
    else:
        why = (
            f"{readiness}% — сильная база: упор на практику, "
            "кейсы и отклики, а не на повтор теста."
        )
    why += f" Уровень подготовки в анкете: {prep}."

    if not pros:
        pros.append("Пройден полный тест — картина устойчивее разовых ответов")
    if not cons:
        cons.append(
            "Закрепляйте навыки практикой"
            if readiness >= 60
            else "Доберите 1–2 навыка из блока «разрыв»"
        )

    return {"why": why, "pros": pros[:3], "cons": cons[:3]}


_RADAR_META = [
    ("self_insight", "Самопознание"),
    ("people_service", "Люди и служение"),
    ("structure_mastery", "Структура и экспертиза"),
    ("balance_autonomy", "Баланс и жизнь"),
]


def _choice_index(ans: Dict[str, Any]) -> int:
    ch = ans.get("choice") or ans.get("choice_id")
    if isinstance(ch, int):
        return max(0, min(3, int(ch)))
    return letter_to_index(str(ch))


def _proforientation_radar_axes(
    answers: List[Dict[str, Any]],
    interest: str,
    profile: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """Веса по question_id; нормализация по достижимому максимуму на каждую ось."""
    matrix = get_pro_weights_matrix_for_interest(interest, profile=profile)
    by_id = {int(a.get("question_id") or 0): a for a in answers}
    core_offset = 0
    core_len = 15
    if profile:
        from wibe_work.services.assessment_bundle import get_assessment_bundle

        bundle = get_assessment_bundle(profile, interest)
        core_offset = int(bundle.get("core_offset") or 0)
        core_len = int(bundle.get("technical_count") or 10) + int(
            bundle.get("career_count") or bundle.get("personality_count") or 5
        )
    totals = [0, 0, 0, 0]
    core_end = min(len(matrix), core_offset + core_len)
    for qi in range(core_offset, core_end):
        row = matrix[qi]
        qid = qi + 1
        ans = by_id.get(qid)
        if not ans:
            continue
        idx = _choice_index(ans)
        if idx < 0 or idx >= len(row):
            continue
        w = row[idx]
        for k in range(4):
            totals[k] += int(w[k])
    max_per = [0, 0, 0, 0]
    for qi in range(core_offset, core_end):
        row = matrix[qi]
        for k in range(4):
            max_per[k] += max(int(row[j][k]) for j in range(len(row)))
    axes: List[Dict[str, Any]] = []
    for i, (key, label) in enumerate(_RADAR_META):
        denom = max_per[i] or 1
        raw = totals[i]
        ratio = min(1.0, raw / float(denom))
        pct = int(round(18 + ratio * 76))
        pct = max(18, min(93, pct))
        axes.append({"key": key, "label": label, "value_percent": pct})
    return axes


def _radar_axes(vec: List[int]) -> List[Dict[str, Any]]:
    """Fallback: старый паттерн по вектору (короткие тесты, неполные ответы)."""
    if not vec:
        vec = [1, 1, 1, 1]
    chunks = [vec[i::4] for i in range(4)]
    labels = [
        ("analytical", "Аналитика"),
        ("creative", "Креатив"),
        ("social", "Коммуникации"),
        ("execution", "Результат"),
    ]
    axes = []
    for i, (key, label) in enumerate(labels):
        c = chunks[i] if i < len(chunks) and chunks[i] else [1]
        raw = sum(c) / max(1, len(c)) / 3.0
        pct = int(round(max(15, min(95, 30 + raw * 55))))
        axes.append({"key": key, "label": label, "value_percent": pct})
    return axes


# IT: id трека → подпись в разборе и буст к планам A/B/C
_IT_TRACK_LABELS: Dict[str, str] = {
    "backend": "Backend-разработчик",
    "frontend": "Frontend-разработчик",
    "devops": "DevOps / инженер инфраструктуры",
    "data": "Аналитик данных / SQL",
    "qa": "Инженер по тестированию (QA)",
}

_IT_TRACK_PLAN_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "backend": ("бэкенд", "backend", "api", "сервер", "веб- и бэкенд"),
    "frontend": ("frontend", "интерфейс", "веб-интерфейс", "мобильн"),
    "devops": ("devops", "релиз", "ci/cd", "сопровожд", "инфраструктур"),
    "data": ("данн", "sql", "аналит", "продуктовая аналитика"),
    "qa": ("автотест", "качеств", "qa", "тестирован"),
}

DIRECTION_POOLS: Dict[str, Tuple[str, ...]] = {
    "it_dev": (
        "Backend-разработка (API, сервер, базы данных)",
        "Frontend и веб-интерфейсы",
        "Мобильная разработка",
        "Автотесты и QA",
        "Данные, SQL и продуктовая аналитика",
        "DevOps и CI/CD",
    ),
    "data": (
        "Продуктовая и бизнес-аналитика",
        "Инженерия данных и витрины",
        "ML и рекомендательные системы",
        "Эксперименты и A/B-тесты",
        "Визуализация и отчётность",
        "Качество данных",
    ),
    "design": (
        "UI/UX продуктовых команд",
        "Дизайн-системы и компоненты",
        "Исследования и юзабилити",
        "Графика и бренд-коммуникации",
        "Прототипирование под разработку",
        "Моушн и презентационные форматы",
    ),
    "default": (
        "Операции и процессы",
        "Проекты и координация",
        "Аналитика и отчётность",
        "Коммуникации и сервис",
        "Обучение и развитие",
        "Предпринимательский эксперимент",
    ),
}

ADJACENT_BY_AXIS: Dict[str, Tuple[str, ...]] = {
    "structure_mastery": ("Системность и регламенты", "Метрики и контроль качества"),
    "people_service": ("Клиентский успех", "Координация стейкхолдеров"),
    "self_insight": ("Портфолио и рефлексия", "Карьерные гипотезы"),
    "balance_autonomy": ("Устойчивый ритм и границы", "Гибкий формат работы"),
}


def _direction_interest_key(interest: str) -> str:
    k = (interest or "").strip()
    return k if k in DIRECTION_POOLS else "default"


def _resolve_effective_interest(profile: Dict[str, Any], interest: str) -> str:
    """Сфера для разбора: явная → main_sphere → первая из анкеты."""
    k = (interest or "").strip()
    if k in DIRECTION_POOLS:
        return k
    ms = str(profile.get("main_sphere") or "").strip()
    if ms in DIRECTION_POOLS:
        return ms
    raw = profile.get("interest_spheres")
    if isinstance(raw, list):
        for item in raw:
            sid = str(item).strip()
            if sid in DIRECTION_POOLS:
                return sid
    elif isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                for item in parsed:
                    sid = str(item).strip()
                    if sid in DIRECTION_POOLS:
                        return sid
        except (json.JSONDecodeError, TypeError):
            pass
        for part in raw.replace(";", ",").split(","):
            sid = part.strip().strip('"').strip("'")
            if sid in DIRECTION_POOLS:
                return sid
    return k or "other"


_CORPORATE_MTS_MARKERS = (
    "закуп",
    "линейно-кабель",
    "кабельн",
    "транспортн",
    "недвижим",
    "юрист",
    "хозяйствен",
    "розничн",
)


def _rows_look_like_corporate_mts(rows: List[Dict[str, Any]]) -> bool:
    if not rows:
        return False
    combined = " ".join(str(r.get("role_name") or "") for r in rows).lower()
    return any(m in combined for m in _CORPORATE_MTS_MARKERS)


def _rows_match_it_direction_pool(rows: List[Dict[str, Any]]) -> bool:
    if not rows:
        return False
    combined = " ".join(str(r.get("role_name") or "") for r in rows).lower()
    it_kw = ("backend", "бэкенд", "frontend", "devops", "qa", "мобильн", "автотест", "sql")
    return any(k in combined for k in it_kw)


def _should_refresh_mts_matrix(
    profile: Dict[str, Any], interest: str, rows: List[Dict[str, Any]]
) -> bool:
    eff = _resolve_effective_interest(profile, interest)
    if eff not in _MTS_DIRECTION_INTERESTS:
        return False
    if not rows:
        return True
    if _rows_look_like_corporate_mts(rows):
        return True
    if eff == "it_dev" and not _rows_match_it_direction_pool(rows):
        return True
    return False


def _answer_letter(ans: Dict[str, Any]) -> str:
    ch = ans.get("choice") or ans.get("choice_id")
    if isinstance(ch, int):
        return "ABCD"[max(0, min(3, int(ch)))]
    s = str(ch or "A").strip().upper()
    return s[0] if s and s[0] in "ABCD" else "A"


def infer_it_track_from_answers(answers: List[Dict[str, Any]]) -> Optional[str]:
    """
    По техническим вопросам IT (1–10): A → backend/data, B → frontend,
    D → devops/QA, C → меньший вес (люди/PM).
    """
    scores: Dict[str, float] = {
        "backend": 0.0,
        "frontend": 0.0,
        "devops": 0.0,
        "data": 0.0,
        "qa": 0.0,
    }
    for a in answers:
        qid = int(a.get("question_id") or 0)
        if qid < 1 or qid > 10:
            continue
        w = 2.0 if qid <= 5 else 1.0
        letter = _answer_letter(a)
        if letter == "A":
            scores["backend"] += w
            if qid in (4, 5):
                scores["data"] += w * 0.35
        elif letter == "B":
            scores["frontend"] += w
        elif letter == "C":
            scores["backend"] += w * 0.15
        elif letter == "D":
            scores["devops"] += w
            if qid in (1, 2):
                scores["qa"] += w * 0.4
    best = max(scores.items(), key=lambda x: x[1])
    if best[1] < 1.0:
        return None
    if best[0] == "data" and scores["backend"] >= scores["data"]:
        return "backend"
    if best[0] == "qa" and scores["devops"] >= scores["qa"]:
        return "devops"
    return str(best[0])


def inferred_it_profession(
    interest: str, answers: List[Dict[str, Any]], stack: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    if _direction_interest_key(interest) != "it_dev":
        return None
    track = infer_it_track_from_answers(answers)
    if not track:
        return None
    label = _IT_TRACK_LABELS.get(track, track)
    from wibe_work.services.hh_filter import hh_search_phrase_for_it_track

    return {
        "track_id": track,
        "label": label,
        "hh_search_phrase": hh_search_phrase_for_it_track(track, stack or []),
    }


def _answer_fingerprint(answers: List[Dict[str, Any]]) -> int:
    h = 0
    for a in sorted(answers, key=lambda x: int(x.get("question_id") or 0)):
        ch = a.get("choice") or a.get("choice_id") or "A"
        s = str(ch).upper()[:1]
        if s not in ("A", "B", "C", "D"):
            s = "A"
        qid = int(a.get("question_id") or 0)
        h = (h * 31 + qid * 17 + ord(s)) % (2**31 - 1)
    return int(h)


def _dominant_radar_key(axes: List[Dict[str, Any]]) -> str:
    if not axes:
        return "structure_mastery"
    best = max(axes, key=lambda a: int(a.get("value_percent") or 0))
    return str(best.get("key") or "structure_mastery")


def _score_direction_name(
    name: str,
    dom_axis: str,
    fp: int,
    idx: int,
    *,
    it_track: Optional[str] = None,
) -> int:
    n = name.lower()
    score = 44 + ((fp + idx * 17) % 23) + idx * 3
    if it_track:
        for kw in _IT_TRACK_PLAN_KEYWORDS.get(it_track, ()):
            if kw in n:
                score += 22
                break
    if dom_axis == "structure_mastery":
        score += sum(
            9
            for kw in (
                "данн",
                "sql",
                "python",
                "backend",
                "devops",
                "аналит",
                "систем",
                "контрол",
                "отчёт",
                "процесс",
                "метрик",
                "автотест",
                "релиз",
            )
            if kw in n
        )
    elif dom_axis == "people_service":
        score += sum(
            9
            for kw in (
                "клиент",
                "продаж",
                "поддерж",
                "hr",
                "команд",
                "коммуникац",
                "сервис",
                "презентац",
            )
            if kw in n
        )
    elif dom_axis == "self_insight":
        score += sum(
            9
            for kw in (
                "портфолио",
                "исслед",
                "гипотез",
                "рефлекс",
                "карьер",
                "само",
            )
            if kw in n
        )
    else:
        score += sum(
            8
            for kw in ("баланс", "гибк", "ритм", "удал", "жизн", "устойч")
            if kw in n
        )
    return score


def _pick_scenario_plans(
    interest: str,
    axes: List[Dict[str, Any]],
    fp: int,
    answers: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Три плана A/B/C из пула сферы + смежные треки по доминанте радара."""
    dk = _direction_interest_key(interest)
    it_track: Optional[str] = None
    inferred: Optional[Dict[str, Any]] = None
    if dk == "it_dev" and answers:
        inferred = inferred_it_profession(interest, answers)
        if inferred:
            it_track = str(inferred.get("track_id") or "")
    pool = list(DIRECTION_POOLS.get(dk, DIRECTION_POOLS["default"]))
    dom = _dominant_radar_key(axes)
    pool = pool + list(ADJACENT_BY_AXIS.get(dom, ()))
    seen: Set[str] = set()
    uniq: List[str] = []
    for p in pool:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    scored = [
        (n, _score_direction_name(n, dom, fp, i, it_track=it_track))
        for i, n in enumerate(uniq)
    ]
    scored.sort(key=lambda x: -x[1])
    top = scored[:3]
    fallback = list(DIRECTION_POOLS["default"])
    while len(top) < 3:
        added = False
        for x in fallback:
            if x not in {t[0] for t in top}:
                top.append((x, 52))
                added = True
                break
        if not added:
            break
    codes = ["A", "B", "C"]
    plans = []
    for idx, (name, raw) in enumerate(top[:3]):
        pid = codes[idx]
        match_score = max(47, min(97, raw + (fp % 5) - 2))
        plans.append({"id": pid, "name": f"План {pid}: {name}", "score_percent": match_score})
    best = max(plans, key=lambda p: p["score_percent"])
    out: Dict[str, Any] = {
        "plans": plans,
        "best_plan_id": best["id"],
        "best_plan_name": best["name"],
        "best_avg_percent": best["score_percent"],
        "caption": "согласованность профиля с треками развития (ответы теста + анкета)",
    }
    if inferred:
        out["inferred_profession"] = inferred
    return out


def _mts_tokens(text: str) -> Set[str]:
    return {
        t
        for t in re.split(r"[^\wёЁа-яА-Яa-zA-Z]+", text.lower())
        if len(t) > 2
    }


_MINIAPP_INTEREST_TO_MTS_TAG: Dict[str, str] = {
    "it_dev": "IT",
    "data": "IT",
    "design": "маркетинг",
    "marketing": "маркетинг",
    "sales": "маркетинг",
    "engineering": "инженерия",
    "logistics": "инженерия",
    "finance": "бизнес",
    "mgmt": "бизнес",
    "hr_edu": "бизнес",
    "medicine": "бизнес",
    "education": "бизнес",
    "creative": "маркетинг",
    "sport": "бизнес",
    "other": "бизнес",
}

_MTS_DIRECTION_INTERESTS = frozenset({"it_dev", "data", "design"})


def _infer_mts_profession_tag(title: str) -> str:
    """Тег роли МТС для сопоставления с интересом (как на сайте)."""
    t = title.lower()
    if "аналитик" in t and "ai" in t:
        return "IT"
    if "сопровожден" in t and "рабоч" in t:
        return "IT"
    if "инженер" in t or "линейно-кабель" in t:
        return "инженерия"
    if "маркетинг" in t:
        return "маркетинг"
    if "продавец" in t or "рознич" in t:
        return "маркетинг"
    if "продаж" in t or "развития" in t:
        return "маркетинг"
    if "корпоратив" in t or "клиент" in t:
        return "бизнес"
    if "hr" in t:
        return "бизнес"
    if "юрист" in t:
        return "бизнес"
    if "закуп" in t:
        return "бизнес"
    if "недвижим" in t or ("эксплуатац" in t and "здан" in t):
        return "бизнес"
    if "транспорт" in t:
        return "инженерия"
    if "административн" in t or "хозяйствен" in t:
        return "бизнес"
    return "бизнес"


def _percent_rows_from_scored(
    scored: List[Tuple[float, str]], limit: int
) -> List[Dict[str, Any]]:
    scored.sort(key=lambda x: -x[0])
    top = scored[:limit]
    if not top:
        return []
    mx = top[0][0] if top[0][0] > 0 else 1.0
    rows: List[Dict[str, Any]] = []
    for rank, (sc, title) in enumerate(top):
        pct = int(round(40 + 55 * (sc / mx)))
        pct = max(38, min(97, pct))
        rows.append({"role_name": title, "percent": pct, "rank": rank})
    return rows


def _rank_career_direction_rows(
    interest: str,
    axes: List[Dict[str, Any]],
    fp: int,
    answers: List[Dict[str, Any]],
    limit: int = 6,
    *,
    it_track_override: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Роли из пула направлений сферы (backend, frontend и т.д.) — по тесту и радару."""
    dk = _direction_interest_key(interest)
    it_track: Optional[str] = it_track_override
    if dk == "it_dev" and not it_track:
        inf = inferred_it_profession(interest, answers)
        if inf:
            it_track = str(inf.get("track_id") or "")
    pool = list(DIRECTION_POOLS.get(dk, DIRECTION_POOLS["default"]))
    if dk == "it_dev" and it_track and it_track in _IT_TRACK_LABELS:
        lead = _IT_TRACK_LABELS[it_track]
        pool = [lead] + [p for p in pool if p != lead]
    dom = _dominant_radar_key(axes)
    if dk != "it_dev":
        for adj in ADJACENT_BY_AXIS.get(dom, ()):
            if adj not in pool:
                pool.append(adj)
    scored: List[Tuple[float, str]] = []
    for i, n in enumerate(pool):
        sc = float(_score_direction_name(n, dom, fp, i, it_track=it_track))
        if dk == "it_dev" and it_track and i == 0 and n in _IT_TRACK_LABELS.values():
            sc += 12.0
        scored.append((sc, n))
    return _percent_rows_from_scored(scored, limit)


def refresh_mts_matrix_in_snapshot(
    snap: Dict[str, Any],
    profile: Dict[str, Any],
    profile_extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Пересчитать роли в сохранённом разборе (старые снимки с матрицей МТС)."""
    interest = str(snap.get("_analysis_interest") or "").strip()
    if not interest:
        interest = _resolve_effective_interest(profile, "")
    rows = list((snap.get("mts_matrix") or {}).get("rows") or [])
    if not _should_refresh_mts_matrix(profile, interest, rows):
        return snap
    answers = list(snap.get("_quiz_answers") or [])
    axes = list((snap.get("style_radar") or {}).get("axes") or [])
    it_track: Optional[str] = None
    inf = (snap.get("scenarios") or {}).get("inferred_profession") or snap.get(
        "inferred_profession"
    )
    if isinstance(inf, dict) and inf.get("track_id"):
        it_track = str(inf["track_id"])
    eff = _resolve_effective_interest(profile, interest)
    extra = profile_extra if profile_extra is not None else {}
    if eff in _MTS_DIRECTION_INTERESTS:
        new_rows = _rank_career_direction_rows(
            eff, axes, _answer_fingerprint(answers), answers, it_track_override=it_track
        )
    else:
        new_rows = _rank_mts_rows(profile, extra, eff, answers, axes)
    out = dict(snap)
    out["mts_matrix"] = {"rows": new_rows}
    if it_track and eff == "it_dev":
        label = _IT_TRACK_LABELS.get(it_track)
        if label:
            inf_out = dict(inf) if isinstance(inf, dict) else {}
            inf_out.setdefault("track_id", it_track)
            inf_out.setdefault("label", label)
            out["inferred_profession"] = inf_out
            sc = dict(out.get("scenarios") or {})
            sc["inferred_profession"] = inf_out
            out["scenarios"] = sc
    return out


def _rank_mts_rows(
    profile: Dict[str, Any],
    profile_extra: Dict[str, Any],
    interest: str,
    answers: List[Dict[str, Any]],
    axes: List[Dict[str, Any]],
    limit: int = 6,
) -> List[Dict[str, Any]]:
    dom = _dominant_radar_key(axes)
    fp = _answer_fingerprint(answers)
    eff = _resolve_effective_interest(profile, interest)
    dk = _direction_interest_key(eff)

    if dk in _MTS_DIRECTION_INTERESTS:
        return _rank_career_direction_rows(eff, axes, fp, answers, limit)

    roles = _load_mts_roles()
    if not roles:
        return _rank_career_direction_rows(eff, axes, fp, answers, limit) or [
            {"role_name": "Стажёр направления", "percent": 72, "rank": 0},
            {"role_name": "Младший специалист", "percent": 58, "rank": 1},
        ]

    blob_parts = [
        _profile_blob(profile, profile_extra),
        interest.lower(),
        str(profile.get("main_sphere") or ""),
        str(profile.get("like_to_do") or ""),
        str(profile.get("programming_skills") or ""),
        str(profile.get("achievements") or ""),
    ]
    user_blob = " ".join(blob_parts).lower()
    user_tokens = _mts_tokens(user_blob)
    user_tag = _MINIAPP_INTEREST_TO_MTS_TAG.get(eff, "бизнес")

    scored: List[Tuple[float, str]] = []
    for role in roles:
        title = str(role.get("title") or "Роль")
        req = " ".join(role.get("requirements") or [])
        duty = " ".join(role.get("duties") or [])
        combined = f"{title} {req} {duty}".lower()
        rt = _mts_tokens(combined)
        overlap = len(user_tokens & rt)
        tag = _infer_mts_profession_tag(title)
        sc = 22.0 + min(36.0, overlap * 3.2)

        if tag == user_tag:
            sc += 38.0
        elif interest == "design" and tag == "маркетинг":
            sc += 14.0
        elif user_tag == "IT" and tag in ("IT", "инженерия"):
            sc += 10.0
        elif user_tag == "инженерия" and tag == "инженерия":
            sc += 28.0

        if user_tag == "IT" and tag == "бизнес":
            sc -= 28.0
        if user_tag == "IT" and tag not in ("IT", "инженерия"):
            sc -= 10.0

        tl = title.lower()
        if dom == "structure_mastery":
            if tag in ("IT", "инженерия") or any(
                x in tl for x in ("инженер", "данн", "аналит", "систем", "ai")
            ):
                sc += 12.0
            if user_tag == "IT" and any(x in tl for x in ("закуп", "транспорт", "недвижим", "юрист")):
                sc -= 18.0
        elif dom == "people_service":
            if any(x in tl for x in ("продаж", "hr", "клиент", "рекрут", "развития")):
                sc += 14.0
        elif dom == "self_insight":
            sc += 5.0
        else:
            sc += 3.0

        if dk == "data" and any(x in combined for x in ("данн", "аналит", "отчёт", "метрик", "excel", "sql")):
            sc += 10.0

        sc += float((fp >> (len(scored) % 7)) % 5)
        scored.append((sc, title))

    rows = _percent_rows_from_scored(scored, limit)
    if user_tag == "IT" and rows:
        top_name = (rows[0].get("role_name") or "").lower()
        if any(x in top_name for x in ("закуп", "транспорт", "недвижим", "юрист", "хозяйствен")):
            return _rank_career_direction_rows(eff, axes, fp, answers, limit)
    return rows


def _behavioral_hint(question_timings_ms: Optional[List[int]]) -> Optional[str]:
    if not question_timings_ms:
        return None
    times = [t for t in question_timings_ms if isinstance(t, int) and t >= 0]
    if len(times) < 3:
        return None
    fast = sum(1 for ms in times if ms < 4000)
    slow = sum(1 for ms in times if ms > 25_000)
    parts: List[str] = []
    if fast >= max(3, len(times) // 4):
        parts.append("Часть ответов дана быстро — возможен импульсивный стиль или высокая уверенность в теме.")
    if slow >= 2:
        parts.append("Есть вдумчивые ответы — склонность к рефлексии; на собеседовании это можно подать как сильную сторону.")
    if not parts:
        parts.append("Темп ответов в целом сбалансирован.")
    return " ".join(parts)


def _clean_scenario_name(name: str) -> str:
    return re.sub(r"^План\s+[ABC]:\s*", "", (name or "").strip(), flags=re.IGNORECASE)


def _axis_plain_explanation(dom: str) -> str:
    return {
        "structure_mastery": "вам близки порядок, логика и разбор задач по шагам",
        "people_service": "важны люди, общение и ощущение пользы другим",
        "self_insight": "вы опираетесь на самопознание и понимание своих мотивов",
        "balance_autonomy": "для вас важны баланс жизни и свобода в решениях",
    }.get(dom, "по тесту виден свой устойчивый стиль работы")


def _mock_ai_narrative(
    profile: Dict[str, Any],
    interest: str,
    preparation_level: str,
    scenarios: Dict[str, Any],
    axes: List[Dict[str, Any]],
    fp: int,
    *,
    readiness_percent: int = 0,
    gap: Optional[Dict[str, Any]] = None,
) -> str:
    """Человеческий вывод без LLM — из анкеты, теста и сценариев."""
    dom = _dominant_radar_key(axes)
    axis_human = _axis_plain_explanation(dom)
    spheres = _sphere_display_labels(profile)
    sphere = ", ".join(spheres[:3]) if spheres else (interest or "ваше направление")
    like = (profile.get("like_to_do") or "").strip()
    city = (profile.get("city") or "").strip()
    prep = _PREP_LABELS.get((preparation_level or "").strip(), "средний")

    plans = sorted(
        list(scenarios.get("plans") or []),
        key=lambda p: -(int(p.get("score_percent") or 0)),
    )
    best_name = _clean_scenario_name(str(plans[0].get("name") or "")) if plans else ""
    best_pct = int(plans[0].get("score_percent") or 0) if plans else None
    alt = [
        _clean_scenario_name(str(p.get("name") or ""))
        for p in plans[1:3]
        if _clean_scenario_name(str(p.get("name") or ""))
    ]

    intro = f"По анкете и тесту у вас сфера: {sphere}."
    if like:
        intro += f" Вы писали, что нравится: {like[:120]}."
    if city:
        intro += f" Город: {city}."
    intro += f" Сильнее других — сторона, где {axis_human}; на это логично опираться в учёбе и в задачах."

    mid = (
        f"Индекс готовности сейчас около {readiness_percent}% — "
        "это не «оценка личности», а отправная точка перед практикой и откликами."
    )
    if best_name and best_pct is not None:
        mid += f" Ближе всего к вам сценарий «{best_name}» (около {best_pct}% по модели)."
    if alt:
        mid += f" «{'» и «'.join(alt)}» можно попробовать коротким экспериментом, если тянет, но не распыляйтесь."

    closing = list((gap or {}).get("closing_skills") or [])[:2]
    if closing:
        mid += f" Из навыков сейчас полезнее всего подтянуть: {', '.join(closing)}."

    closings = (
        f"На 2–3 месяца возьмите один главный трек"
        + (f" — «{best_name}»" if best_name else "")
        + " и раз в неделю фиксируйте маленький результат: задача, урок, кусок портфолио.",
        f"Уровень подготовки в анкете — {prep}: не гонитесь за идеалом, "
        "делайте по одному шагу из плана роста и раздела «Обучение».",
        "Если сомневаетесь — две недели практики по главному треку и снова посмотрите на разбор; "
        "цифры обновятся, когда пройдёте тест ещё раз.",
    )
    return " ".join((intro, mid, closings[fp % len(closings)]))


def _format_axes_for_llm(axes: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for a in axes[:8]:
        lab = str(a.get("label") or a.get("key") or "?")
        pct = a.get("value_percent")
        if pct is not None:
            parts.append(f"{lab}: {pct}%")
    return "; ".join(parts) if parts else "—"


def _analysis_narrative_llm(
    profile_summary: str,
    scenarios: Dict[str, Any],
    *,
    axes: List[Dict[str, Any]],
    readiness_percent: int,
    answers_count: int,
    analysis_mode: str = "career",
) -> Tuple[str, str, Optional[str]]:
    """(текст, источник llm|mock, notice)."""
    plans = scenarios.get("plans") or []
    plan_line = ", ".join(
        f"{p.get('id')}={p.get('name', '')} (~{p.get('score_percent', '?')}%)"
        for p in plans[:3]
    )
    axes_line = _format_axes_for_llm(axes)
    min_full = 15 if analysis_mode != "school" else 12
    short_quiz = answers_count < min_full
    caveat = ""
    if short_quiz:
        caveat = (
            f"Опрос неполный: только {answers_count} ответов. "
            "Не утверждай высокую точность профиля; используй формулировки «по текущим данным», «предварительно»."
        )
    prompt = build_analysis_user_prompt(
        profile_summary=profile_summary,
        readiness_percent=readiness_percent,
        axes_line=axes_line,
        plan_line=plan_line,
        answers_count=answers_count,
        short_quiz_caveat=caveat,
        analysis_mode=analysis_mode,
    )
    system = (
        ANALYSIS_NARRATIVE_SCHOOL_SYSTEM
        if analysis_mode == "school"
        else ANALYSIS_NARRATIVE_SYSTEM
    )
    if not llm_configured():
        return "", "mock", None
    text, notice = fetch_llm_completion(
        prompt,
        max_tokens=560,
        temperature=0.42,
        system_prompt=system,
    )
    if text:
        return text, "llm", None
    return "", "mock", notice


def _profile_summary_rich(
    profile: Dict[str, Any],
    profile_extra: Dict[str, Any],
    interest: str,
    education: str,
    preparation_level: str,
) -> str:
    """Текст для LLM и чата: анкета + параметры теста."""
    snippet = coach_profile_snippet(profile)
    city = profile.get("city") or profile_extra.get("city") or ""
    age = profile.get("age") or profile_extra.get("age")
    tail = (
        f"Сфера теста: {interest}; возраст: {age or '—'}; "
        f"образование (сводка): {education}; город: {city or 'не указан'}; "
        f"подготовка: {preparation_level}."
    )
    if snippet:
        return snippet + "\n" + tail
    return tail


def _resolve_profession_pack(interest: str) -> Any:
    try:
        import sys

        repo = Path(__file__).resolve().parents[4]
        website = repo / "website"
        if website.is_dir() and str(website) not in sys.path:
            sys.path.insert(0, str(website))
        from app.api_schemas import Interest
        from app.profession_packs import resolve_profession_pack

        key = _MINIAPP_TO_WEBSITE_INTEREST.get((interest or "").strip(), "IT")
        return resolve_profession_pack(Interest(key))
    except Exception:
        return None


def _skill_scores(
    profile: Dict[str, Any],
    axes: List[Dict[str, Any]],
    fp: int,
    interest: str,
) -> Dict[str, int]:
    scores = {
        k: 40 + (fp >> (i * 5)) % 14 for i, k in enumerate(_SKILL_ORDER)
    }
    dom = _dominant_radar_key(axes)
    if dom == "structure_mastery":
        scores["programming"] += 12
        scores["analytics"] += 14
    elif dom == "people_service":
        scores["communication"] += 14
        scores["management"] += 10
    elif dom == "self_insight":
        scores["analytics"] += 8
        scores["communication"] += 6
    else:
        scores["management"] += 8

    blob = (profile_skill_blob(profile) or "").lower()
    if any(x in blob for x in ("python", "java", "javascript", "sql", "git", "c++")):
        scores["programming"] = min(94, scores["programming"] + 12)
    if any(x in blob for x in ("excel", "аналит", "data", "bi", "tableau")):
        scores["analytics"] = min(94, scores["analytics"] + 10)
    if any(x in blob for x in ("figma", "дизайн", "photoshop", "ui", "ux")):
        scores["design"] = min(94, scores["design"] + 12)
    if interest in ("sales", "hr_edu", "mgmt", "education"):
        scores["communication"] = min(94, scores["communication"] + 8)

    for k in _SKILL_ORDER:
        scores[k] = max(36, min(94, scores[k]))
    return scores


def _target_for_track(track_name: str) -> Dict[str, int]:
    t = (track_name or "").lower()
    targets = {k: 70 for k in _SKILL_ORDER}
    if any(x in t for x in ("python", "java", "backend", "devops", "sql", "данн")):
        targets["programming"] = 82
        targets["analytics"] = 78
    elif any(x in t for x in ("дизайн", "ux", "ui", "график")):
        targets["design"] = 85
        targets["communication"] = 72
    elif any(x in t for x in ("продаж", "hr", "клиент", "рекрут")):
        targets["communication"] = 84
        targets["management"] = 76
    elif any(x in t for x in ("маркет", "контент", "smm")):
        targets["communication"] = 78
        targets["analytics"] = 75
    return targets


def _build_gap_analysis(
    profile: Dict[str, Any],
    interest: str,
    top_track: str,
    axes: List[Dict[str, Any]],
    fp: int,
) -> Dict[str, Any]:
    pack = _resolve_profession_pack(interest)
    user = _skill_scores(profile, axes, fp, interest)
    target = _target_for_track(top_track)
    labels = (
        dict(pack.gap_bar_labels)
        if pack
        else {
            _SKILL_TO_PACK_KEY[k]: k.replace("_", " ").title()
            for k in _SKILL_ORDER
        }
    )
    headline = pack.gap_headline if pack else "Навыки vs цель выбранного направления"
    bars: List[Dict[str, Any]] = []
    closeness: List[int] = []
    for sk in _SKILL_ORDER:
        pack_key = _SKILL_TO_PACK_KEY[sk]
        u = user[sk]
        tg = target.get(sk, 70)
        gap = max(0, tg - u)
        closeness.append(100 - min(100, gap))
        bars.append(
            {
                "label": labels.get(pack_key, sk),
                "user_percent": u,
                "target_percent": min(100, tg),
                "gap_percent": min(100, gap),
            }
        )
    overall = sum(closeness) // max(1, len(closeness))
    weak = sorted(
        ((b["label"], b["gap_percent"]) for b in bars if b["gap_percent"] > 15),
        key=lambda x: -x[1],
    )
    closing = [w[0] for w in weak[:3]]
    if not closing:
        closing = ["Портфолио или учебный кейс", "Обратная связь наставника", "Регулярные отклики"]
    return {
        "headline": headline,
        "overall_hp": overall,
        "bars": bars,
        "closing_skills": closing,
    }


def _sphere_display_labels(profile: Dict[str, Any]) -> List[str]:
    ids = parse_interest_spheres(profile)
    if not ids and (profile.get("main_sphere") or "").strip():
        ids = [str(profile.get("main_sphere")).strip()]
    return [_SPHERE_LABELS.get(s, s) for s in ids if s]


def _profile_skill_hints(profile: Dict[str, Any], limit: int = 4) -> List[str]:
    hints: List[str] = []
    for key in (
        "like_to_do",
        "programming_skills",
        "software_skills",
        "experience_projects",
        "extra_education",
    ):
        raw = (profile.get(key) or "").strip()
        if not raw:
            continue
        chunk = raw.replace("\n", ", ")[:140]
        if chunk and chunk not in hints:
            hints.append(chunk)
        if len(hints) >= limit:
            break
    return hints


def _pain_context(
    profile: Dict[str, Any],
    *,
    gap: Optional[Dict[str, Any]],
    scenarios: Optional[Dict[str, Any]],
    axes: Optional[List[Dict[str, Any]]],
    readiness_percent: Optional[int],
    top_track: str,
) -> Dict[str, Any]:
    sc = scenarios or {}
    g = gap or {}
    plans = sc.get("plans") or []
    best_name = str(sc.get("best_plan_name") or (plans[0].get("name") if plans else "") or "")
    best_pct = sc.get("best_avg_percent")
    closing = list(g.get("closing_skills") or [])[:3]
    weak_axes: List[str] = []
    strong_axes: List[str] = []
    for a in axes or []:
        lbl = str(a.get("label") or "")
        pct = int(a.get("value_percent") or 0)
        if pct >= 58 and lbl:
            strong_axes.append(f"{lbl} ({pct}%)")
        elif pct < 50 and lbl:
            weak_axes.append(lbl)
    wf_raw = (
        profile.get("work_format_preference")
        or profile.get("work_format_pref")
        or ""
    )
    wf = str(wf_raw).strip()
    pr = (profile.get("career_priority") or "").strip().lower()
    return {
        "city": (profile.get("city") or "").strip(),
        "like": (profile.get("like_to_do") or "").strip(),
        "dislike": (profile.get("dislike_to_do") or "").strip(),
        "edu": (
            profile.get("education_detail") or profile.get("education_level") or ""
        ).strip(),
        "course": (profile.get("course_grade") or profile.get("course_or_grade") or "").strip(),
        "spheres": _sphere_display_labels(profile),
        "prep": _PREP_LABELS.get(
            (profile.get("preparation_level") or "").strip(), "средний"
        ),
        "work_format": _WORK_FORMAT_RU.get(wf, wf) if wf else "",
        "priority": _PRIORITY_RU.get(pr, pr) if pr else "",
        "salary": profile.get("target_salary"),
        "skill_hints": _profile_skill_hints(profile),
        "readiness": readiness_percent,
        "top_track": (top_track or "").strip(),
        "best_plan": best_name,
        "best_pct": best_pct,
        "closing": closing,
        "gap_hp": g.get("overall_hp"),
        "weak_axes": weak_axes[:2],
        "strong_axes": strong_axes[:2],
    }


def _join_natural(parts: List[str]) -> str:
    clean = [p.strip() for p in parts if p and str(p).strip()]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    return clean[0] + " " + " ".join(clean[1:])


def _pain_summary_for(pain_id: str, ctx: Dict[str, Any]) -> str:
    label = _PAIN_LABELS.get(pain_id, "")
    lead = f"В анкете главная сложность — «{label}»."
    bits: List[str] = [lead]

    if ctx["spheres"]:
        bits.append(f"Сферы, которые вы выбрали: {', '.join(ctx['spheres'][:4])}.")
    if ctx["city"]:
        loc = ctx["city"]
        if ctx["work_format"]:
            loc += f", формат работы — {ctx['work_format']}"
        bits.append(f"Локация и условия: {loc}.")
    if ctx["like"]:
        bits.append(f"Вам нравится: {ctx['like'][:160]}.")
    if ctx["readiness"] is not None:
        bits.append(f"По тесту индекс готовности — {ctx['readiness']}%.")
    if ctx["best_plan"] and ctx["best_pct"] is not None:
        bits.append(
            f"Ближе всего сценарий «{ctx['best_plan']}» (~{ctx['best_pct']}%)."
        )
    if ctx["closing"]:
        bits.append(f"Из разрыва навыков в приоритете: {', '.join(ctx['closing'][:2])}.")

    tail = {
        "pain_career": (
            "Это не приговор: опирайтесь на сценарии A/B/C ниже и проверьте одно направление "
            "маленьким делом, а не бесконечным «выбором профессии»."
        ),
        "pain_no_exp": (
            "Опыта в резюме может не быть — но в анкете уже есть зацепки для первого кейса "
            "(учёба, проекты, подработки)."
        ),
        "pain_region": (
            "Вакансий в городе может быть меньше — зато в профиле можно целиться в удалёнку "
            "и смотреть соседние города."
        ),
        "pain_money_courses": (
            "Платные курсы не обязательны: в разделе «Обучение» есть бесплатные треки под вашу сферу."
        ),
        "pain_interview": (
            "Страх собеседований часто сильнее реальных требований — тренируйте ответы по своей сфере, "
            "а не «вообще про работу»."
        ),
        "pain_overload": (
            "Информации много — поэтому ниже план по неделям и этапы роста; берите один шаг, не всё сразу."
        ),
        "pain_low_confidence": (
            "Ощущение «ничего не умею» расходится с данными анкеты и теста: навыки есть, "
            "их нужно назвать вслух и оформить, а не сравнивать себя с чужим идеалом."
        ),
        "pain_gap_skills": (
            "Скорее всего, не «вас не берут», а не совпадает подача с требованиями вакансий — "
            "это видно по разрыву навыков и сценариям плана."
        ),
    }
    bits.append(tail.get(pain_id, ""))
    return _join_natural(bits)


def _pain_tips_for(pain_id: str, ctx: Dict[str, Any]) -> List[str]:
    tips: List[str] = []
    skills = ctx["skill_hints"]
    closing = ctx["closing"]
    like = ctx["like"]
    city = ctx["city"]
    wf = ctx["work_format"]

    if pain_id == "pain_low_confidence":
        if skills:
            tips.append(
                f"Выпишите 5 конкретных дел из вашей жизни по мотивам «{skills[0][:80]}» — "
                "срок, что сделали, кому помогли. Это и есть навыки для резюме."
            )
        elif like:
            tips.append(
                f"Составьте список из 5 задач, связанных с «{like[:80]}», где вы уже что-то умеете — "
                "без сравнения с senior-специалистами."
            )
        if ctx["strong_axes"]:
            tips.append(
                f"Опирайтесь на сильные стороны по тесту: {', '.join(ctx['strong_axes'])}."
            )
        if closing:
            tips.append(
                f"На этой неделе — один маленький шаг по «{closing[0]}», не «стать идеалом за месяц»."
            )
    elif pain_id == "pain_no_exp":
        proj = (skills[2] if len(skills) > 2 else skills[0] if skills else like)
        if proj:
            tips.append(
                f"Оформите один кейс из анкеты ({proj[:90]}): задача → ваши действия → результат в цифрах."
            )
        if ctx["best_plan"]:
            tips.append(
                f"В откликах укажите цель «{ctx['best_plan'][:60]}» и 2–3 навыка из раздела «Разрыв навыков»."
            )
        if wf or city:
            tips.append(
                f"В «Вакансиях» включите фильтр: {wf or 'удобный формат'}"
                + (f", город {city}" if city else "")
                + ", уровень «без опыта» / стажировка."
            )
    elif pain_id == "pain_career":
        if ctx["best_plan"]:
            tips.append(
                f"Выберите для проверки сценарий «{ctx['best_plan'][:70]}» — "
                "2 недели мини-проекта или стажировки, потом сравните ощущения."
            )
        if ctx["spheres"]:
            tips.append(
                f"Сузьте выбор до 2 сфер: {', '.join(ctx['spheres'][:2])} — остальное в «потом»."
            )
        tips.append("Запишите, что из «нравится» и «не нравится» в анкете важнее денег vs обучения — это ваш фильтр.")
    elif pain_id == "pain_region":
        if wf:
            tips.append(f"Ищите вакансии с форматом «{wf}» — вы сами так указали в анкете.")
        if city:
            tips.append(
                f"Добавьте 2–3 города рядом с {city} или удалённые позиции по сфере "
                f"{', '.join(ctx['spheres'][:2]) or 'из анкеты'}."
            )
    elif pain_id == "pain_money_courses":
        track = ctx["top_track"] or (ctx["spheres"][0] if ctx["spheres"] else "ваше направление")
        tips.append(
            f"В «Обучение» откройте бесплатный трек под {track} — одна неделя, один артефакт (конспект или мини-проект)."
        )
        if closing:
            tips.append(f"Параллельно закройте один пункт разрыва: {closing[0]}.")
    elif pain_id == "pain_interview":
        sphere = ", ".join(ctx["spheres"][:2]) or ctx["top_track"] or "вашей сфере"
        tips.append(
            f"Три ответа вслух (по 2 мин) на типовые вопросы по {sphere} — опирайтесь на «{like[:60]}»"
            if like
            else f"Три ответа вслух (по 2 мин) на типовые вопросы по {sphere}."
        )
        if ctx["weak_axes"]:
            tips.append(
                f"Подготовьте пример по слабой оси теста: {ctx['weak_axes'][0]} — один кейс из учёбы или хобби."
            )
    elif pain_id == "pain_overload":
        tips.append("На эту неделю — только первый пункт из «Этапов роста» ниже; остальное в заметку «потом».")
        if closing:
            tips.append(f"Из разрыва навыков — один фокус: {closing[0]}.")
    elif pain_id == "pain_gap_skills":
        if closing:
            tips.append(
                f"Откройте одну вакансию мечты и сравните с разрывом: начните с «{closing[0]}» на 3–4 недели."
            )
        if ctx["best_pct"] is not None:
            tips.append(
                f"Сценарий плана уже ~{ctx['best_pct']}% — упакуйте это в резюме и сопроводительное, а не добавляйте новые курсы."
            )
        if skills:
            tips.append(f"В резюме явно перечислите: {skills[0][:100]}.")

    if not tips:
        tips.append(_PAIN_LABELS.get(pain_id, "Сделайте один шаг из плана ниже на этой неделе."))
    if ctx["priority"] and len(tips) < 3:
        tips.append(f"Учитывайте приоритет из анкеты — сейчас для вас важнее: {ctx['priority']}.")
    return [t for t in tips if t][:3]


def _pain_focus(
    profile: Dict[str, Any],
    *,
    gap: Optional[Dict[str, Any]] = None,
    scenarios: Optional[Dict[str, Any]] = None,
    axes: Optional[List[Dict[str, Any]]] = None,
    readiness_percent: Optional[int] = None,
    top_track: str = "",
) -> Optional[Dict[str, Any]]:
    pain_id = (profile.get("primary_pain") or "").strip()
    if pain_id and pain_id in _PAIN_LABELS:
        ctx = _pain_context(
            profile,
            gap=gap,
            scenarios=scenarios,
            axes=axes,
            readiness_percent=readiness_percent,
            top_track=top_track,
        )
        return {
            "pain_id": pain_id,
            "label": _PAIN_LABELS[pain_id],
            "summary": _pain_summary_for(pain_id, ctx),
            "tips": _pain_tips_for(pain_id, ctx),
        }
    aligned = align_pains(profile)
    matched = aligned.get("matched_pains") or []
    if not matched:
        return None
    m = matched[0]
    inferred = {
        "Я не знаю, кем стать": "pain_career",
        "У меня нет опыта, меня никуда не возьмут": "pain_no_exp",
        "Я из маленького города": "pain_region",
        "У меня нет денег на курсы": "pain_money_courses",
        "Я боюсь собеседований": "pain_interview",
        "Слишком много информации, не знаю с чего начать": "pain_overload",
        "Я ничего не умею": "pain_low_confidence",
        "Всё умею, но работу не дают": "pain_gap_skills",
    }.get(str(m.get("pain") or ""))
    if inferred:
        ctx = _pain_context(
            profile,
            gap=gap,
            scenarios=scenarios,
            axes=axes,
            readiness_percent=readiness_percent,
            top_track=top_track,
        )
        return {
            "pain_id": inferred,
            "label": _PAIN_LABELS[inferred],
            "summary": _pain_summary_for(inferred, ctx),
            "tips": _pain_tips_for(inferred, ctx),
        }
    return {
        "pain_id": None,
        "label": str(m.get("pain") or ""),
        "summary": (
            "По тексту анкеты мы видим эту сложность — ниже шаги с опорой на ваши ответы и разбор теста."
        ),
        "tips": _pain_tips_for("pain_overload", _pain_context(
            profile,
            gap=gap,
            scenarios=scenarios,
            axes=axes,
            readiness_percent=readiness_percent,
            top_track=top_track,
        )),
    }


def _week_mini_plan(
    week_range: str,
    learn: str,
    practice: str,
    outcome: str,
) -> Dict[str, str]:
    """Мини-план на блок недель: изучи → потренируй → в итоге."""
    return {
        "week_range": week_range,
        "learn": learn,
        "practice": practice,
        "outcome": outcome,
    }


def _weekly_roadmap(
    top_track: str,
    interest: str,
    *,
    preparation: str = "medium",
) -> List[Dict[str, Any]]:
    pack = _resolve_profession_pack(interest)
    pk = pack.key if pack else "tech"
    low = (top_track or "").lower()
    direction = (top_track or "").strip() or "ваше направление"
    prep = preparation if preparation in ("weak", "medium", "strong") else "medium"

    if pk == "tech" and any(x in low for x in ("python", "java", "данн", "sql", "backend", "devops", "frontend")):
        if prep == "weak":
            return [
                _week_mini_plan(
                    "Недели 1–2",
                    learn="Поставьте рабочее окружение: редактор, Git, первый репозиторий — без этого дальше будет путаница.",
                    practice="Пройдите вводный модуль по языку или SQL: 5–7 коротких задач, по 20–30 минут в день.",
                    outcome="Поймёте, как устроен обычный день разработчика, и перестанете бояться «сломать» проект.",
                ),
                _week_mini_plan(
                    "Недели 3–4",
                    learn="Соберите самый простой мини-проект по теме «"
                    + direction
                    + "» — главное, чтобы он был доведён до конца.",
                    practice="Напишите черновик резюме: три пункта «что сделал» под вакансии, которые смотрели в начале.",
                    outcome="Появится один кейс для портфолио и понятная история для первого отклика.",
                ),
            ]
        if prep == "strong":
            return [
                _week_mini_plan(
                    "Недели 1–2",
                    learn="Сверьте 5 вакансий по «" + direction + "» и выпишите, какие навыки повторяются чаще всего.",
                    practice="Сделайте pet-проект или доработайте учебный — с фокусом на один навык из разрыва.",
                    outcome="Резюме и портфолио будут бить в реальный спрос, а не в абстрактное «я учусь».",
                ),
                _week_mini_plan(
                    "Недели 3–4",
                    learn="Оформите проект: README, скрин или демо — чтобы рекрутеру было что открыть за 30 секунд.",
                    practice="Отправьте 3–5 точечных откликов с коротким сопроводительным под конкретную вакансию.",
                    outcome="Начнёте получать обратную связь с рынка и поймёте, что докрутить дальше.",
                ),
            ]
        return [
            _week_mini_plan(
                "Недели 1–2",
                learn="Разберитесь с Git и окружением: коммиты, ветки, запуск проекта локально.",
                practice="Закрепите основы языка или SQL — 5–10 задач, без марафона на десятки часов.",
                outcome="Будет привычный рабочий ритм: учиться → сразу применять → фиксировать результат.",
            ),
            _week_mini_plan(
                "Недели 3–4",
                learn="Соберите мини-проект по «" + direction + "» — пусть простой, но законченный.",
                practice="Обновите резюме и напишите сопроводительное под одну реальную вакансию.",
                outcome="Сможете откликнуться с примером работы, а не только с желанием «войти в IT».",
            ),
        ]

    if pk == "design" or "дизайн" in low or "ux" in low:
        return [
            _week_mini_plan(
                "Недели 1–2",
                learn="Освойте Figma на уровне auto-layout и компонентов — это база для любого UI.",
                practice="Сделайте редизайн одного экрана приложения или сайта, который вам нравится.",
                outcome="Появится первая работа, которую не стыдно положить в портфолио.",
            ),
            _week_mini_plan(
                "Недели 3–4",
                learn="Опишите мини-кейс: задача → что сделали → чем помогло пользователю (хотя бы в учебной форме).",
                practice="Соберите 2–3 работы в одном файле или на Behance/Dribbble с коротким контекстом.",
                outcome="Портфолио начнёт отвечать на вопрос «а что вы умеете на практике?», а не только «смотрите картинки».",
            ),
        ]

    if pk == "marketing":
        return [
            _week_mini_plan(
                "Недели 1–2",
                learn="Разберитесь, как устроена воронка и какие метрики смотрят в «" + direction + "».",
                practice="Сделайте один учебный креатив или пост — с гипотезой «кому и зачем это».",
                outcome="Поймёте язык маркетинга на примере, а не по сухой теории.",
            ),
            _week_mini_plan(
                "Недели 3–4",
                learn="Соберите мини-отчёт: что запускали, какие цифры (пусть учебные), что бы улучшили.",
                practice="Подготовьте 3–5 откликов или стажировок с кейсом в сопроводительном.",
                outcome="В резюме появится история с цифрами — это сильно отличает от «просто интересуюсь SMM».",
            ),
        ]

    if pk == "sales":
        return [
            _week_mini_plan(
                "Недели 1–2",
                learn="Изучите продукт сферы и типовые возражения — 5–10 реальных диалогов из интервью или кейсов.",
                practice="Отработайте 10–15 учебных звонков или переписок по скрипту, вслух или с другом.",
                outcome="Снизится страх «что сказать клиенту» и появится базовая уверенность в разговоре.",
            ),
            _week_mini_plan(
                "Недели 3–4",
                learn="Разберите один продукт, который хотите продавать: кому, какая выгода, чем отличается.",
                practice="Сделайте 5 целевых откликов или питчей — с одной конкретной компанией в фокусе.",
                outcome="Сможете показать работодателю, что понимаете продукт, а не только «умею звонить».",
            ),
        ]

    if pk in ("office_finance", "hr", "legal"):
        return [
            _week_mini_plan(
                "Недели 1–2",
                learn="Разберите типовые регламенты и шаблоны в «" + direction + "» — что делают каждый день.",
                practice="Пройдите учебный кейс в таблицах или документе: сверка, заявка, карточка кандидата.",
                outcome="Поймёте ритм работы и перестанете воспринимать сферу как набор непонятных аббревиатур.",
            ),
            _week_mini_plan(
                "Недели 3–4",
                learn="Оформите один законченный кейс с выводом: что проверили, что нашли, что предложили.",
                practice="Обновите резюме под 3 вакансии и попросите обратную связь у знакомого из сферы.",
                outcome="Будет готовый пример для собеседования: «вот задача — вот как я её решал».",
            ),
        ]

    # Универсальный мини-план (по умолчанию)
    if prep == "weak":
        learn_12 = (
            "Откройте 5 вакансий по «" + direction + "» и выпишите: что от вас просят чаще всего."
        )
        practice_12 = (
            "Выберите один бесплатный вводный курс или урок — 20–30 минут в день, без перегруза."
        )
    else:
        learn_12 = (
            "Посмотрите рынок: 5 вакансий-ориентиров по «" + direction + "» и список повторяющихся навыков."
        )
        practice_12 = (
            "Освойте один главный инструмент сферы на учебной задаче — 2–3 часа в неделю для старта хватит."
        )
    return [
        _week_mini_plan(
            "Недели 1–2",
            learn=learn_12,
            practice=practice_12,
            outcome="Станет ясно, куда целиться, и вы перестанете учить всё подряд без связи с работой.",
        ),
        _week_mini_plan(
            "Недели 3–4",
            learn="Сделайте учебный кейс или мини-проект — то, что можно описать в резюме одним абзацом.",
            practice="Соберите резюме и короткое сопроводительное под одну реальную вакансию из первых двух недель.",
            outcome="Сможете откликнуться не «в пустоту», а с примером и понятной историей о себе.",
        ),
    ]


def _learning_cards(interest: str, preparation: str) -> List[Dict[str, Any]]:
    base = {
        "it_dev": [
            {
                "title": "Основы Python",
                "url": "https://stepik.org",
                "kind": "курс",
                "description": "Синтаксис, типы, циклы и простые задачи — база для кода, автоматизации и аналитики.",
            },
            {
                "title": "Git для начинающих",
                "url": "https://learngitbranching.js.org/?locale=ru",
                "kind": "симулятор",
                "description": "Ветки, merge и rebase наглядно: без установки, в игровой форме.",
            },
        ],
        "data": [
            {
                "title": "SQL интерактив",
                "url": "https://sql-academy.org",
                "kind": "практика",
                "description": "Пишите запросы в браузере, с подсказками — удобно с нуля и для отборов в данных.",
            },
            {
                "title": "Kaggle Learn",
                "url": "https://www.kaggle.com/learn",
                "kind": "курс",
                "description": "Короткие треки по Python, SQL и ML; часть материалов на английском.",
            },
        ],
        "design": [
            {
                "title": "Figma Learn",
                "url": "https://help.figma.com",
                "kind": "документация",
                "description": "Официальные разделы про компоненты, автолейаут и прототипирование.",
            },
            {
                "title": "UX-тренажёр",
                "url": "https://lawsofux.com",
                "kind": "гайд",
                "description": "Короткие принципы UX карточками — подходит для насмотренности и языка интерфейсов.",
            },
        ],
    }
    cards = list(base.get(interest, base["it_dev"]))
    if preparation == "weak":
        cards.insert(
            0,
            {
                "title": "Якоря карьеры Шейна (обзор)",
                "url": "https://www.mindtools.com/pages/article/career-anchors.htm",
                "kind": "статья",
                "description": "Что для вас опора в работе — экспертиза, автономия, вызов, стабильность; помогает сузить направления.",
            },
        )
    return cards


def _advice_blocks(
    scenarios: Dict[str, Any],
    preparation: str,
    profile: Dict[str, Any],
    gap: Dict[str, Any],
) -> Dict[str, Any]:
    plans = scenarios.get("plans") or []
    closing = gap.get("closing_skills") or []
    priority = closing[:3] if closing else ["самопознание", "карьерные ценности", "резюме и отклики"]
    pain_id = (profile.get("primary_pain") or "").strip()
    pain_step = _PAIN_FIRST_STEP.get(pain_id) if pain_id else None
    out = {}
    for p in plans:
        pid = p.get("id", "A")
        steps = [
            "Трио самоисследования: сильные стороны, текущие интересы, готовность решать запросы других людей (не только «для себя»)",
            "Зафиксируйте карьерные ценности (якоря Шейна): что в работе для вас опора — служение, экспертиза, управление или баланс с жизнью",
            "Резюме: структура и примеры (видео/статьи) или поддержка карьерного консультанта; попросите близких назвать ваши сильные стороны",
            "Сопоставьте тип среды (по Голланду) и комфорт в команде: общение vs регламент, логика vs отношения, план vs гибкость",
        ]
        if pain_step:
            steps.insert(0, pain_step)
        if preparation == "weak":
            steps.insert(0, "Начните с короткого вводного курса или чеклиста по направлению 10–15 ч")
        out[pid] = {
            "title": p.get("name", "План"),
            "steps": steps,
            "priority_skills": priority,
        }
    return {"by_plan": out}


def build_analysis_result(
    profile: Dict[str, Any],
    profile_extra: Dict[str, Any],
    interest: str,
    education: str,
    preparation_level: str,
    answers: List[Dict[str, Any]],
    question_timings_ms: Optional[List[int]] = None,
) -> Dict[str, Any]:
    vec = _answer_vector(answers)
    readiness_vec = _readiness_percent(vec, preparation_level)
    min_core = 15
    if profile:
        from wibe_work.services.assessment_bundle import get_assessment_bundle

        b = get_assessment_bundle(profile, interest)
        min_core = int(b.get("technical_count") or 10) + int(
            b.get("career_count") or b.get("personality_count") or 5
        )
    if len(answers) >= min_core:
        axes = _proforientation_radar_axes(answers, interest, profile=profile)
        axis_avg = sum(a["value_percent"] for a in axes) / max(1, len(axes))
        readiness = int(max(12, min(100, round(0.35 * readiness_vec + 0.65 * axis_avg))))
    else:
        axes = _radar_axes(vec)
        readiness = readiness_vec
    fp = _answer_fingerprint(answers)
    eff_interest = _resolve_effective_interest(profile, interest)
    mode = analysis_mode_for_profile(profile)

    if mode == "school":
        scenarios = pick_school_path_plans(profile, eff_interest, axes, fp)
        plans = scenarios.get("plans") or []
        top_track = str(scenarios.get("best_plan_name") or (plans[0].get("name") if plans else interest))
        top_track = re.sub(r"^Вариант\s+[ABC]:\s*", "", top_track, flags=re.IGNORECASE).strip() or interest
        gap = build_school_gap_analysis(profile, eff_interest, top_track, axes, fp)
        mts_matrix = school_education_hints(profile, eff_interest, scenarios)
        profile_summary_pre = _profile_summary_rich(
            profile, profile_extra, interest, education, preparation_level
        )
        learn_x = school_learning_extras(
            profile=profile,
            interest=interest,
            preparation_level=preparation_level,
            scenarios=scenarios,
            gap=gap,
            profile_summary=profile_summary_pre,
            user_id=str(profile.get("_user_id") or "") or None,
            eff_interest=eff_interest,
        )
        weekly = school_weekly_roadmap(profile, top_track, eff_interest)
    else:
        scenarios = _pick_scenario_plans(eff_interest, axes, fp, answers)
        plans = scenarios.get("plans") or []
        top_track = str(scenarios.get("best_plan_name") or (plans[0].get("name") if plans else interest))
        top_track = re.sub(r"^План [ABC]:\s*", "", top_track).strip() or interest
        gap = _build_gap_analysis(profile, interest, top_track, axes, fp)
        mts_matrix = {"rows": _rank_mts_rows(profile, profile_extra, eff_interest, answers, axes)}
        profile_summary_pre = _profile_summary_rich(
            profile, profile_extra, interest, education, preparation_level
        )
        learn_x = build_learning_extras(
            profile=profile,
            interest=interest,
            preparation_level=preparation_level,
            scenarios=scenarios,
            gap=gap,
            profile_summary=profile_summary_pre,
            user_id=str(profile.get("_user_id") or "") or None,
            eff_interest=eff_interest,
        )
        weekly = _weekly_roadmap(top_track, interest, preparation=preparation_level)

    learning = learn_x.get("learning") or _learning_cards(eff_interest, preparation_level)
    learning_path = learn_x.get("learning_path")
    learning_path_detail = learn_x.get("learning_path_detail")
    advice = learn_x.get("individual_advice")
    stages = learn_x.get("growth_stages")
    growth_stages_rich = learn_x.get("growth_stages_rich")
    pain_focus = _pain_focus(
        profile,
        gap=gap,
        scenarios=scenarios,
        axes=axes,
        readiness_percent=readiness,
        top_track=top_track,
    )
    if mode == "school" and pain_focus:
        pid = (profile.get("primary_pain") or "").strip()
        school_step = school_pain_first_step(pid) if pid else None
        if school_step:
            tips = list(pain_focus.get("tips") or [])
            pain_focus["tips"] = [school_step] + [t for t in tips if school_step not in t][:2]

    profile_summary = profile_summary_pre
    directions_hint = ", ".join(
        f"{p['id']}: {p.get('name', '')} (~{p['score_percent']}%)"
        for p in scenarios.get("plans", [])
    )
    llm_text, narr_src, narr_notice = _analysis_narrative_llm(
        profile_summary,
        scenarios,
        axes=axes,
        readiness_percent=readiness,
        answers_count=len(answers),
        analysis_mode=mode,
    )
    if llm_text.strip():
        narrative = llm_text.strip()
        ai_narrative_source = "llm"
        ai_narrative_notice = None
    else:
        if mode == "school":
            narrative = mock_school_narrative(
                profile,
                eff_interest,
                scenarios,
                axes,
                fp,
                readiness_percent=readiness,
                gap=gap,
            )
        else:
            narrative = _mock_ai_narrative(
                profile,
                interest,
                preparation_level,
                scenarios,
                axes,
                fp,
                readiness_percent=readiness,
                gap=gap,
            )
        ai_narrative_source = "mock"
        ai_narrative_notice = None
    behavioral = _behavioral_hint(question_timings_ms)
    readiness_insight = _build_readiness_insight(
        readiness, preparation_level, axes, gap, scenarios
    )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return {
        "analyzed_at": now,
        "readiness": {
            "value_percent": readiness,
            "segments": [
                {"from": 0, "to": 20, "color": "#e11d48"},
                {"from": 20, "to": 40, "color": "#f97316"},
                {"from": 40, "to": 60, "color": "#eab308"},
                {"from": 60, "to": 80, "color": "#84cc16"},
                {"from": 80, "to": 100, "color": "#22c55e"},
            ],
            **readiness_insight,
        },
        "style_radar": {"axes": axes},
        "analysis_mode": mode,
        "scenarios": scenarios,
        "mts_matrix": mts_matrix,
        "learning": learning,
        "learning_path": learning_path,
        "learning_path_detail": learning_path_detail,
        "individual_advice": advice,
        "growth_stages": stages,
        "growth_stages_rich": growth_stages_rich,
        "gap_analysis": gap,
        "pain_focus": pain_focus,
        "weekly_roadmap": weekly,
        "behavioral_hint": behavioral,
        "ai_narrative": narrative,
        "ai_narrative_source": ai_narrative_source,
        "ai_narrative_notice": ai_narrative_notice,
        # внутреннее для чата
        "profile_summary": profile_summary,
        "directions_hint": directions_hint,
        "narrative": narrative,
        "_timings_note": question_timings_ms,
        "_analysis_interest": eff_interest,
        "_quiz_answers": answers,
    }


def public_analysis_payload(full: Dict[str, Any]) -> Dict[str, Any]:
    """Только то, что видит пользователь в разделе разбора."""
    keys = (
        "analyzed_at",
        "analysis_mode",
        "readiness",
        "style_radar",
        "scenarios",
        "inferred_profession",
        "mts_matrix",
        "learning",
        "learning_path",
        "learning_path_detail",
        "individual_advice",
        "growth_stages",
        "growth_stages_rich",
        "gap_analysis",
        "pain_focus",
        "weekly_roadmap",
        "behavioral_hint",
        "ai_narrative",
        "ai_narrative_source",
        "ai_narrative_notice",
    )
    out = {k: full[k] for k in keys if k in full}
    inf = (full.get("scenarios") or {}).get("inferred_profession")
    if inf and "inferred_profession" not in out:
        out["inferred_profession"] = inf
    return out
