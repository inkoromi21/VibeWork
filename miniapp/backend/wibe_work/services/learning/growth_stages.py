"""Этапы роста: связь с советами, уровнем подготовки и материалами обучения."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from wibe_work.services.learning.personalized_advice import (
    _infer_track_from_plan,
    _pick_materials,
    _plan_label,
    _pool_materials,
    _priority_skills,
)


def _prep_label(preparation: str) -> str:
    return {
        "weak": "начальный",
        "medium": "средний",
        "strong": "уверенный",
    }.get(preparation, "средний")


def _readiness_note(readiness_percent: int, preparation: str) -> str:
    prep = _prep_label(preparation)
    if readiness_percent < 35:
        return (
            f"Индекс готовности {readiness_percent}% и {prep} уровень подготовки — "
            "двигайтесь небольшими шагами, без перегруза."
        )
    if readiness_percent < 60:
        return (
            f"Индекс готовности {readiness_percent}% ({prep} уровень) — "
            "фокус на закрытии разрыва навыков и одном артефакте за этап."
        )
    return (
        f"Индекс готовности {readiness_percent}% — "
        "можно быстрее переходить к практике и откликам, если закрыты базовые пробелы."
    )


def _best_plan_block(
    advice: Optional[Dict[str, Any]],
    scenarios: Dict[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    by = (advice or {}).get("by_plan") or {}
    pid = str(scenarios.get("best_plan_id") or "A")
    block = by.get(pid) or by.get("A") or {}
    return pid, block if isinstance(block, dict) else {}


def _advice_snippets(block: Dict[str, Any], indices: Tuple[int, ...]) -> List[str]:
    out: List[str] = []
    steps = block.get("steps") or []
    for i in indices:
        if i < 0 or i >= len(steps):
            continue
        st = steps[i]
        if isinstance(st, str):
            out.append(st[:220])
        elif isinstance(st, dict):
            t = str(st.get("text") or "").strip()
            if t:
                out.append(t[:220])
    return out


def _materials_from_steps(path_steps: List[Dict[str, Any]], *, limit: int = 4) -> List[Dict[str, Any]]:
    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []
    for step in path_steps:
        for res in step.get("resources") or []:
            url = (res.get("url") or "").strip()
            if not url or url == "#" or url in seen:
                continue
            seen.add(url)
            out.append(
                {
                    "title": res.get("title") or "Материал",
                    "url": url,
                    "kind": res.get("kind") or "ресурс",
                    "provider": res.get("provider"),
                    "path_step": step.get("title"),
                }
            )
            if len(out) >= limit:
                return out
    return out


def _path_steps_slice(
    learning_path: Optional[Dict[str, Any]],
    stage_index: int,
) -> List[Dict[str, Any]]:
    steps = list(learning_path.get("steps") or []) if learning_path else []
    if not steps:
        return []
    n = len(steps)
    if stage_index == 1:
        return steps[: max(1, (n + 2) // 3)]
    if stage_index == 2:
        a = max(1, (n + 2) // 3)
        b = max(a + 1, (2 * n + 2) // 3)
        return steps[a:b]
    a = max(1, (2 * n + 2) // 3)
    return steps[a:]


def _merge_materials(*groups: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []
    for group in groups:
        for m in group:
            url = (m.get("url") or "").strip()
            if url and url not in seen:
                seen.add(url)
                out.append(m)
            if len(out) >= limit:
                return out
    return out


def build_growth_stages(
    *,
    interest: str,
    eff_interest: str,
    preparation_level: str,
    readiness_percent: int,
    profile: Dict[str, Any],
    gap: Dict[str, Any],
    scenarios: Dict[str, Any],
    individual_advice: Optional[Dict[str, Any]],
    learning_path: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Три этапа с привязкой к советам, gap и шагам learning_path."""
    priority = _priority_skills(gap)
    top_skills = ", ".join(priority[:3])
    plan_id, plan_block = _best_plan_block(individual_advice, scenarios)
    plan_name = _plan_label(
        next(
            (p for p in (scenarios.get("plans") or []) if str(p.get("id")) == plan_id),
            {"name": scenarios.get("best_plan_name") or f"План {plan_id}"},
        )
    )
    track = _infer_track_from_plan(plan_name)
    pool = _pool_materials(
        sphere=eff_interest,
        track=track,
        preparation=preparation_level,
        learning_path=learning_path,
    )
    used_urls: Set[str] = set()
    readiness_ctx = _readiness_note(readiness_percent, preparation_level)

    # --- Этап 1 ---
    s1_path = _path_steps_slice(learning_path, 1)
    s1_mats = _merge_materials(
        _materials_from_steps(s1_path, limit=3),
        _pick_materials(
            pool,
            keywords=("курс", "intro", "roadmap", "основ", track or "карьер"),
            limit=2,
            used_urls=used_urls,
        ),
        limit=4,
    )
    s1_advice = _advice_snippets(plan_block, (0, 1, 2))
    s1_body_parts = [
        readiness_ctx,
        f"Опора перед выбором в «{interest}» и приоритетном треке «{plan_name}».",
        "Выписать сильные стороны и примеры; отметить, где энергия; отделить хобби от готовности решать чужие запросы.",
    ]
    if preparation_level == "weak":
        s1_body_parts.append(
            "На этом уровне сначала закройте 1–2 базовых навыка из разрыва: "
            + (top_skills or "логика, самопознание")
            + " — через короткий курс из материалов ниже."
        )
    if s1_advice:
        s1_body_parts.append(
            "Продолжение советов по плану "
            + plan_id
            + ": "
            + s1_advice[0][:180]
            + ("…" if len(s1_advice[0]) > 180 else "")
        )
    horizon_1 = "3–5 недель" if preparation_level == "weak" else "2–4 недели"

    # --- Этап 2 ---
    s2_path = _path_steps_slice(learning_path, 2)
    s2_mats = _merge_materials(
        _materials_from_steps(s2_path, limit=4),
        _pick_materials(
            pool,
            keywords=("практик", "exercism", "git", "резюме", track or ""),
            limit=2,
            used_urls=used_urls,
        ),
        limit=5,
    )
    s2_advice = _advice_snippets(plan_block, (2, 3, 4))
    s2_body_parts = [
        "Связка с этапом 1: опирайтесь на список сильных сторон и ценности при формулировках в резюме.",
        f"Закрываем разрыв по навыкам: {top_skills}.",
        "Черновик резюме под «" + plan_name + "»; 3 достижения с цифрой или фактом.",
    ]
    if preparation_level == "strong":
        s2_body_parts.append(
            "Добавьте pet-проект или PR в open-source — это сильнее абстрактных курсов на вашем уровне."
        )
    elif preparation_level == "medium":
        s2_body_parts.append(
            "Параллельно — одна практика в неделю (задачи, Git) из материалов этапа."
        )
    if s2_advice:
        s2_body_parts.append("Из индивидуальных советов: " + s2_advice[0][:200])

    # --- Этап 3 ---
    s3_path = _path_steps_slice(learning_path, 3)
    s3_mats = _merge_materials(
        _materials_from_steps(s3_path, limit=4),
        _pick_materials(
            pool,
            keywords=("portfolio", "github", "ваканс", "отклик", track or ""),
            limit=2,
            used_urls=used_urls,
        ),
        limit=5,
    )
    s3_advice = _advice_snippets(plan_block, (4, 5))
    s3_body_parts = [
        "После резюме и практики — выход на рынок: отклики с учётом типа среды (Голланд) и комфорта в команде.",
        f"Целевой трек: {plan_name}. Сверяйте вакансии с приоритетными навыками: {top_skills}.",
    ]
    if readiness_percent >= 55:
        s3_body_parts.append(
            "По индексу готовности можно планировать 8–12 откликов и 2–3 собеседования за цикл."
        )
    else:
        s3_body_parts.append(
            "Пока готовность ниже 55% — 5 целевых откликов и разбор каждого отказа, без массовой рассылки."
        )
    if s3_advice:
        s3_body_parts.append("Из советов: " + s3_advice[-1][:200] if s3_advice else "")

    path_titles = lambda sl: [str(s.get("title") or "") for s in sl if s.get("title")]

    return [
        {
            "stage": 1,
            "title": "Самопознание и база навыков",
            "subtitle": f"Опора перед «{plan_name}» · план {plan_id}",
            "body": " ".join(s1_body_parts),
            "horizon": horizon_1,
            "focus_tags": ["трио", "якоря", _prep_label(preparation_level)],
            "milestones": [
                "Список сильных сторон (5 пунктов)",
                "Черновик карьерных ценностей",
                f"1 материал из пути: {path_titles(s1_path)[0]}" if path_titles(s1_path) else "1 вводный курс из блока материалов",
            ],
            "when_next": (
                "Когда ясно, что мотивирует в работе, и вы прошли первый шаг пути обучения "
                + (f"«{path_titles(s1_path)[0]}»" if path_titles(s1_path) else "из списка материалов")
                + "."
            ),
            "readiness_percent": readiness_percent,
            "preparation_level": preparation_level,
            "priority_skills": priority[:3],
            "linked_plan_id": plan_id,
            "advice_refs": s1_advice[:2],
            "path_steps": path_titles(s1_path)[:3],
            "materials": s1_mats,
            "continues_from": None,
        },
        {
            "stage": 2,
            "title": "Практика и резюме",
            "subtitle": f"Разрыв навыков · {top_skills[:60]}",
            "body": " ".join(s2_body_parts),
            "horizon": "2–6 недель",
            "focus_tags": ["резюме", "практика", priority[0][:12] if priority else "навыки"],
            "milestones": [
                "Черновик резюме под выбранный трек",
                "3 формулировки достижений от близких или наставника",
                "Минимум 3 решённые задачи / коммита в Git",
            ],
            "when_next": "Когда резюме можно показать наставнику и есть артефакт практики (репозиторий или кейс).",
            "readiness_percent": readiness_percent,
            "preparation_level": preparation_level,
            "priority_skills": priority[:3],
            "linked_plan_id": plan_id,
            "advice_refs": s2_advice[:2],
            "path_steps": path_titles(s2_path)[:3],
            "materials": s2_mats,
            "continues_from": "Этап 1: ценности и сильные стороны → буллеты в резюме",
        },
        {
            "stage": 3,
            "title": "Рынок и закрепление трека",
            "subtitle": "Отклики и тип среды",
            "body": " ".join(s3_body_parts),
            "horizon": "1–3 месяца",
            "focus_tags": ["отклики", "собес", plan_name[:14]],
            "milestones": [
                "5–12 целевых откликов по треку",
                "2–3 разговора с работодателями или стажировками",
                "Обновление портфолио по итогам этапа 2",
            ],
            "when_next": "Когда есть оффер, стажировка или ясный список, что докрутить по навыкам.",
            "readiness_percent": readiness_percent,
            "preparation_level": preparation_level,
            "priority_skills": priority[:3],
            "linked_plan_id": plan_id,
            "advice_refs": s3_advice[:2],
            "path_steps": path_titles(s3_path)[:3],
            "materials": s3_mats,
            "continues_from": "Этап 2: резюме + практика → целевые отклики",
        },
    ]
