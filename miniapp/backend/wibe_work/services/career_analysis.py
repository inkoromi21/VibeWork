"""Построение результата разбора: метрики для UI + внутренние поля для чата."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from wibe_work.miniapp_paths import data_file
from wibe_work.services.llm_client import fetch_llm_completion, llm_configured
from wibe_work.services.llm_prompts import ANALYSIS_NARRATIVE_SYSTEM, build_analysis_user_prompt
from wibe_work.services.aptitude_quiz import get_pro_weights_matrix_for_interest, letter_to_index
from wibe_work.services.user_context import (
    _PAIN_LABELS,
    coach_profile_snippet,
    profile_skill_blob,
)
from wibe_work.services.user_pain_mapping import align_pains

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


def _proforientation_radar_axes(answers: List[Dict[str, Any]], interest: str) -> List[Dict[str, Any]]:
    """15 вопросов: веса по question_id; нормализация по достижимому максимуму на каждую ось."""
    matrix = get_pro_weights_matrix_for_interest(interest)
    by_id = {int(a.get("question_id") or 0): a for a in answers}
    totals = [0, 0, 0, 0]
    for qi, row in enumerate(matrix):
        qid = qi + 1
        ans = by_id.get(qid)
        if not ans:
            continue
        idx = _choice_index(ans)
        w = row[idx]
        for k in range(4):
            totals[k] += int(w[k])
    max_per = [0, 0, 0, 0]
    for row in matrix:
        for k in range(4):
            max_per[k] += max(int(row[j][k]) for j in range(4))
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


def _mock_ai_narrative(
    interest: str,
    education: str,
    preparation_level: str,
    scenarios: Dict[str, Any],
    axes: List[Dict[str, Any]],
    fp: int,
) -> str:
    dom = _dominant_radar_key(axes)
    axis_labels = {a.get("key"): a.get("label") for a in axes}
    tilt = axis_labels.get(dom, "профиль по осям методики")
    plans = scenarios.get("plans") or []
    names = ", ".join(f"{p.get('id', '?')}: {p.get('name', '')}" for p in plans[:3])
    variants = (
        f"По радару сильнее выражена ось «{tilt}». Сценарии: {names}. Держите один трек главным на квартал, второй — для короткого эксперимента.",
        f"Профиль: «{tilt}» и сфера «{interest}», подготовка «{preparation_level}». Варианты {names}: фиксируйте результат каждую неделю.",
        f"Образование: {education}. Оси методики указывают на «{tilt}». Маршруты {names}: портфолио и практика убедительнее любого теста.",
    )
    return variants[fp % len(variants)]


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
) -> Tuple[str, str, Optional[str]]:
    """(текст, источник llm|mock, notice)."""
    plans = scenarios.get("plans") or []
    plan_line = ", ".join(
        f"{p.get('id')}={p.get('name', '')} (~{p.get('score_percent', '?')}%)"
        for p in plans[:3]
    )
    axes_line = _format_axes_for_llm(axes)
    short_quiz = answers_count < 15
    caveat = ""
    if short_quiz:
        caveat = (
            f"Опрос неполный: только {answers_count} ответов из 15 по полной методике. "
            "Не утверждай высокую точность профиля; используй формулировки «по текущим данным», «предварительно»."
        )
    prompt = build_analysis_user_prompt(
        profile_summary=profile_summary,
        readiness_percent=readiness_percent,
        axes_line=axes_line,
        plan_line=plan_line,
        answers_count=answers_count,
        short_quiz_caveat=caveat,
    )
    if not llm_configured():
        return "", "mock", None
    text, notice = fetch_llm_completion(
        prompt,
        max_tokens=560,
        temperature=0.42,
        system_prompt=ANALYSIS_NARRATIVE_SYSTEM,
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


def _pain_focus(profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    pain_id = (profile.get("primary_pain") or "").strip()
    if pain_id and pain_id in _PAIN_LABELS:
        tips = align_pains(profile).get("matched_pains") or []
        extra = [t.get("bot_value", [""])[0] for t in tips[:2] if t.get("bot_value")]
        return {
            "pain_id": pain_id,
            "label": _PAIN_LABELS[pain_id],
            "tips": [_PAIN_FIRST_STEP.get(pain_id, "")] + extra,
        }
    aligned = align_pains(profile)
    matched = aligned.get("matched_pains") or []
    if matched:
        m = matched[0]
        return {
            "pain_id": None,
            "label": m.get("pain", ""),
            "tips": (m.get("bot_value") or [])[:3],
        }
    return None


def _weekly_roadmap(top_track: str, interest: str) -> List[Dict[str, Any]]:
    pack = _resolve_profession_pack(interest)
    pk = pack.key if pack else "tech"
    low = (top_track or "").lower()
    if pk == "tech" and any(x in low for x in ("python", "java", "данн", "sql", "backend")):
        return [
            {
                "week_range": "Недели 1–2",
                "topics": ["Git и окружение", "основы языка или SQL + 5 задач"],
            },
            {
                "week_range": "Недели 3–4",
                "topics": ["мини-проект в портфолио", "черновик резюме под отклики"],
            },
        ]
    if pk == "design" or "дизайн" in low:
        return [
            {
                "week_range": "Недели 1–2",
                "topics": ["Figma: auto-layout", "редизайн одного экрана"],
            },
            {
                "week_range": "Недели 3–4",
                "topics": ["мини-кейс в портфолио", "3 работы с контекстом задачи"],
            },
        ]
    if pk in ("sales", "marketing"):
        return [
            {
                "week_range": "Недели 1–2",
                "topics": ["воронка и метрики", "один учебный креатив или скрипт"],
            },
            {
                "week_range": "Недели 3–4",
                "topics": ["кейс с цифрами", "10 целевых откликов"],
            },
        ]
    return [
        {
            "week_range": "Недели 1–2",
            "topics": ["рынок и 5 вакансий-ориентиров", "один ключевой инструмент сферы"],
        },
        {
            "week_range": "Недели 3–4",
            "topics": ["учебный кейс или проект", "резюме и сопроводительное"],
        },
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
    if len(answers) >= 15:
        axes = _proforientation_radar_axes(answers, interest)
        axis_avg = sum(a["value_percent"] for a in axes) / max(1, len(axes))
        readiness = int(max(12, min(100, round(0.35 * readiness_vec + 0.65 * axis_avg))))
    else:
        axes = _radar_axes(vec)
        readiness = readiness_vec
    fp = _answer_fingerprint(answers)
    eff_interest = _resolve_effective_interest(profile, interest)
    scenarios = _pick_scenario_plans(eff_interest, axes, fp, answers)
    plans = scenarios.get("plans") or []
    top_track = str(scenarios.get("best_plan_name") or (plans[0].get("name") if plans else interest))
    top_track = re.sub(r"^План [ABC]:\s*", "", top_track).strip() or interest
    gap = _build_gap_analysis(profile, interest, top_track, axes, fp)
    mts_rows = _rank_mts_rows(profile, profile_extra, eff_interest, answers, axes)
    from wibe_work.services.learning.engine import build_learning_for_analysis

    _learning_pack = build_learning_for_analysis(
        user_id=str(profile.get("_user_id") or "") or None,
        profile=profile,
        interest=eff_interest,
        preparation_level=preparation_level,
        scenarios=scenarios,
        gap=gap,
    )
    learning = _learning_pack.get("learning") or _learning_cards(
        eff_interest, preparation_level
    )
    learning_path = _learning_pack.get("learning_path")
    from wibe_work.services.learning.personalized_advice import build_individual_advice

    profile_summary_pre = _profile_summary_rich(
        profile, profile_extra, interest, education, preparation_level
    )
    advice = build_individual_advice(
        scenarios=scenarios,
        preparation_level=preparation_level,
        profile=profile,
        gap=gap,
        interest=eff_interest,
        learning_path=learning_path,
        profile_summary=profile_summary_pre,
        user_id=str(profile.get("_user_id") or "") or None,
    )
    from wibe_work.services.learning.growth_stages import build_growth_stages

    stages = build_growth_stages(
        interest=interest,
        eff_interest=eff_interest,
        preparation_level=preparation_level,
        readiness_percent=readiness,
        profile=profile,
        gap=gap,
        scenarios=scenarios,
        individual_advice=advice,
        learning_path=learning_path,
    )
    pain_focus = _pain_focus(profile)
    weekly = _weekly_roadmap(top_track, interest)

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
    )
    if llm_text.strip():
        narrative = llm_text.strip()
        ai_narrative_source = "llm"
        ai_narrative_notice = None
    else:
        narrative = _mock_ai_narrative(
            interest, education, preparation_level, scenarios, axes, fp
        )
        ai_narrative_source = "mock"
        ai_narrative_notice = narr_notice
    behavioral = _behavioral_hint(question_timings_ms)

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
        },
        "style_radar": {"axes": axes},
        "scenarios": scenarios,
        "mts_matrix": {"rows": mts_rows},
        "learning": learning,
        "learning_path": learning_path,
        "individual_advice": advice,
        "growth_stages": stages,
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
        "readiness",
        "style_radar",
        "scenarios",
        "inferred_profession",
        "mts_matrix",
        "learning",
        "learning_path",
        "individual_advice",
        "growth_stages",
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
