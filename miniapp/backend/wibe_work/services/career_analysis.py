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


DIRECTION_POOLS: Dict[str, Tuple[str, ...]] = {
    "it_dev": (
        "Веб- и бэкенд-разработка",
        "Мобильные приложения",
        "Автотесты и качество ПО",
        "Данные, SQL и продуктовая аналитика",
        "DevOps и релизы",
        "Сопровождение и внутренние сервисы",
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


def _score_direction_name(name: str, dom_axis: str, fp: int, idx: int) -> int:
    n = name.lower()
    score = 44 + ((fp + idx * 17) % 23) + idx * 3
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
) -> Dict[str, Any]:
    """Три плана A/B/C из пула сферы + смежные треки по доминанте радара."""
    dk = _direction_interest_key(interest)
    pool = list(DIRECTION_POOLS.get(dk, DIRECTION_POOLS["default"]))
    dom = _dominant_radar_key(axes)
    pool = pool + list(ADJACENT_BY_AXIS.get(dom, ()))
    seen: Set[str] = set()
    uniq: List[str] = []
    for p in pool:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    scored = [(n, _score_direction_name(n, dom, fp, i)) for i, n in enumerate(uniq)]
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
    return {
        "plans": plans,
        "best_plan_id": best["id"],
        "best_plan_name": best["name"],
        "best_avg_percent": best["score_percent"],
        "caption": "согласованность профиля с треками развития (правила + ответы теста)",
    }


def _mts_tokens(text: str) -> Set[str]:
    return {
        t
        for t in re.split(r"[^\wёЁа-яА-Яa-zA-Z]+", text.lower())
        if len(t) > 2
    }


def _rank_mts_rows(
    profile: Dict[str, Any],
    profile_extra: Dict[str, Any],
    interest: str,
    answers: List[Dict[str, Any]],
    axes: List[Dict[str, Any]],
    limit: int = 6,
) -> List[Dict[str, Any]]:
    roles = _load_mts_roles()
    if not roles:
        return [
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
    dom = _dominant_radar_key(axes)
    fp = _answer_fingerprint(answers)
    dk = _direction_interest_key(interest)

    scored: List[Tuple[float, str]] = []
    for role in roles:
        title = str(role.get("title") or "Роль")
        req = " ".join(role.get("requirements") or [])
        duty = " ".join(role.get("duties") or [])
        combined = f"{title} {req} {duty}".lower()
        rt = _mts_tokens(combined)
        overlap = len(user_tokens & rt)
        sc = 20.0 + min(38.0, overlap * 3.5)

        tl = title.lower()
        if dom == "structure_mastery":
            if any(x in tl for x in ("инженер", "данн", "аналит", "сопровожд", "систем", "закуп")):
                sc += 14
        elif dom == "people_service":
            if any(x in tl for x in ("продаж", "hr", "клиент", "рекрут", "развития")):
                sc += 16
        elif dom == "self_insight":
            sc += 6
        else:
            sc += 4

        if dk == "it_dev" and any(x in combined for x in ("it", "данн", "систем", "sql", "тех")):
            sc += 10
        if dk == "data" and any(x in combined for x in ("данн", "аналит", "отчёт", "метрик", "excel")):
            sc += 12
        if dk == "design" and any(x in combined for x in ("дизайн", "визуал", "ux", "бренд")):
            sc += 10

        sc += float((fp >> (len(scored) % 7)) % 9)
        scored.append((sc, title))

    scored.sort(key=lambda x: -x[0])
    top = scored[:limit]
    mx = top[0][0] if top else 1.0
    if mx < 1:
        mx = 1.0
    rows: List[Dict[str, Any]] = []
    for rank, (sc, title) in enumerate(top):
        pct = int(round(40 + 55 * (sc / mx)))
        pct = max(38, min(97, pct))
        rows.append({"role_name": title, "percent": pct, "rank": rank})
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


def _learning_cards(interest: str, preparation: str) -> List[Dict[str, Any]]:
    base = {
        "it_dev": [
            {"title": "Основы Python", "url": "https://stepik.org", "kind": "курс"},
            {"title": "Git для начинающих", "url": "https://learngitbranching.js.org/?locale=ru", "kind": "симулятор"},
        ],
        "data": [
            {"title": "SQL интерактив", "url": "https://sql-academy.org", "kind": "практика"},
            {"title": "Kaggle Learn", "url": "https://www.kaggle.com/learn", "kind": "курс"},
        ],
        "design": [
            {"title": "Figma Learn", "url": "https://help.figma.com", "kind": "документация"},
            {"title": "UX-тренажёр", "url": "https://lawsofux.com", "kind": "гайд"},
        ],
    }
    cards = list(base.get(interest, base["it_dev"]))
    if preparation == "weak":
        cards.insert(
            0,
            {"title": "Якоря карьеры Шейна (обзор)", "url": "https://www.mindtools.com/pages/article/career-anchors.htm", "kind": "статья"},
        )
    return cards


def _advice_blocks(scenarios: Dict[str, Any], preparation: str) -> Dict[str, Any]:
    plans = scenarios.get("plans") or []
    out = {}
    for p in plans:
        pid = p.get("id", "A")
        steps = [
            "Трио самоисследования: сильные стороны, текущие интересы, готовность решать запросы других людей (не только «для себя»)",
            "Зафиксируйте карьерные ценности (якоря Шейна): что в работе для вас опора — служение, экспертиза, управление или баланс с жизнью",
            "Резюме: структура и примеры (видео/статьи) или поддержка карьерного консультанта; попросите близких назвать ваши сильные стороны",
            "Сопоставьте тип среды (по Голланду) и комфорт в команде: общение vs регламент, логика vs отношения, план vs гибкость",
        ]
        if preparation == "weak":
            steps.insert(0, "Начните с короткого вводного курса или чеклиста по направлению 10–15 ч")
        out[pid] = {
            "title": p.get("name", "План"),
            "steps": steps,
            "priority_skills": ["самопознание", "карьерные ценности", "резюме и отклики"],
        }
    return {"by_plan": out}


def _growth_stages(interest: str) -> List[Dict[str, Any]]:
    return [
        {
            "stage": 1,
            "title": "Самопознание и ценности",
            "subtitle": f"Опора перед выбором в «{interest}»",
            "body": "Выписать сильные стороны и примеры; отметить, где сейчас энергия и интерес; отделить хобби от готовности делать то же для запросов других людей.",
            "horizon": "2–4 недели",
            "focus_tags": ["трио", "якоря"],
            "milestones": ["Список сильных сторон", "Черновик карьерных ценностей"],
            "when_next": "Когда ясно, что вас мотивирует в работе и где вы готовы отдавать ценность не только себе.",
        },
        {
            "stage": 2,
            "title": "Резюме и поддержка",
            "subtitle": "Снять страх отклика",
            "body": "Разобрать структуру резюме; при страхе ошибки — опора на гайды; при страхе отказа — друг или консультант; спросить близких: «с каким вопросом ты ко мне приходишь?»",
            "horizon": "2–6 недель",
            "focus_tags": ["резюме", "обратная связь"],
            "milestones": ["Черновик резюме", "3 формулировки достижений от друзей/наставника"],
            "when_next": "Когда есть версия резюме, которую не стыдно показать и вы готовы к первым откликам.",
        },
        {
            "stage": 3,
            "title": "Рынок и тип среды",
            "subtitle": "Голланд, команда, ритм",
            "body": "Целенаправленно откликайтесь с учётом типа среды (идеи, практика, люди, творчество) и комфорта: общение vs регламент, хаос vs план.",
            "horizon": "1–3 месяца",
            "focus_tags": ["отклики", "собес"],
            "milestones": ["10 откликов", "3 разговора с работодателями или стажировками"],
            "when_next": "Когда есть оффер, стажировка или понятный разбор, что докрутить.",
        },
    ]


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
    scenarios = _pick_scenario_plans(interest, axes, fp)
    mts_rows = _rank_mts_rows(profile, profile_extra, interest, answers, axes)
    learning = _learning_cards(interest, preparation_level)
    advice = _advice_blocks(scenarios, preparation_level)
    stages = _growth_stages(interest)

    city = profile.get("city") or profile_extra.get("city") or ""
    age = profile.get("age") or profile_extra.get("age")
    profile_summary = (
        f"Возраст: {age}; сфера: {interest}; образование: {education}; "
        f"город: {city or 'не указан'}; подготовка: {preparation_level}."
    )
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
                {"from": 80, "to": 100, "color": "#22a954"},
            ],
        },
        "style_radar": {"axes": axes},
        "scenarios": scenarios,
        "mts_matrix": {"rows": mts_rows},
        "learning": learning,
        "individual_advice": advice,
        "growth_stages": stages,
        "behavioral_hint": behavioral,
        "ai_narrative": narrative,
        "ai_narrative_source": ai_narrative_source,
        "ai_narrative_notice": ai_narrative_notice,
        # внутреннее для чата
        "profile_summary": profile_summary,
        "directions_hint": directions_hint,
        "narrative": narrative,
        "_timings_note": question_timings_ms,
    }


def public_analysis_payload(full: Dict[str, Any]) -> Dict[str, Any]:
    """Только то, что видит пользователь в разделе разбора."""
    keys = (
        "analyzed_at",
        "readiness",
        "style_radar",
        "scenarios",
        "mts_matrix",
        "learning",
        "individual_advice",
        "growth_stages",
        "behavioral_hint",
        "ai_narrative",
        "ai_narrative_source",
        "ai_narrative_notice",
    )
    return {k: full[k] for k in keys if k in full}
