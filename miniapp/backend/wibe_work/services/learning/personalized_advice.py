"""Персональные советы по планам A/B/C с привязкой к материалам обучения."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from wibe_work.services.learning.catalog import resource_to_card, resources_by_id
from wibe_work.services.learning.engine import build_learning_path_payload
from wibe_work.services.llm_client import fetch_llm_completion, llm_configured
from wibe_work.services.llm_prompts import (
    ADVICE_JSON_SYSTEM,
    build_advice_user_prompt,
)

# Ключевые слова направления в названии плана → track для каталога
_TRACK_HINTS: List[Tuple[str, Tuple[str, ...]]] = [
    ("devops", ("devops", "релиз", "инфраструкт", "docker", "kubernetes", "ci/cd")),
    ("backend", ("backend", "бэкенд", "python", "api", "сервер", "fastapi")),
    ("frontend", ("frontend", "фронт", "javascript", "вёрст", "react", "html")),
    ("data", ("data", "аналит", "sql", "pandas", "ml", "данн")),
    ("design", ("design", "дизайн", "ux", "ui", "figma")),
    ("marketing", ("маркет", "smm", "digital", "реклам")),
    ("qa", ("qa", "тест", "quality")),
]


def _plan_label(plan: Dict[str, Any]) -> str:
    name = str(plan.get("name") or "")
    return re.sub(r"^План [ABC]:\s*", "", name, flags=re.I).strip() or name


def _infer_track_from_plan(plan_name: str) -> Optional[str]:
    low = plan_name.lower()
    for track, kws in _TRACK_HINTS:
        if any(k in low for k in kws):
            return track
    return None


def _priority_skills(gap: Dict[str, Any]) -> List[str]:
    closing = gap.get("closing_skills") or []
    if closing:
        return [str(x) for x in closing[:5]]
    out: List[str] = []
    for bar in gap.get("bars") or []:
        lab = bar.get("label") or bar.get("key")
        if lab:
            out.append(str(lab))
    if out:
        return out[:5]
    return ["самопознание", "карьерные ценности", "резюме и отклики"]


def _flatten_path_resources(learning_path: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not learning_path:
        return []
    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []
    for step in learning_path.get("steps") or []:
        for res in step.get("resources") or []:
            url = (res.get("url") or "").strip()
            if not url or url == "#" or url in seen:
                continue
            seen.add(url)
            out.append(dict(res))
    return out


def _catalog_resources_for_track(
    sphere: str,
    track: Optional[str],
    preparation: str,
    *,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Ресурсы из каталога под направление плана."""
    by_id = resources_by_id()
    track_l = (track or "").lower()
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for r in by_id.values():
        score = 0
        spheres = r.get("spheres") or []
        tracks = [str(t).lower() for t in (r.get("tracks") or [])]
        skills = " ".join(str(s) for s in (r.get("skills") or [])).lower()
        title = str(r.get("title") or "").lower()
        if sphere in spheres:
            score += 4
        if track_l and track_l in tracks:
            score += 12
        if track_l and track_l in title:
            score += 6
        if track_l and track_l in skills:
            score += 4
        level = str(r.get("level") or "")
        if preparation == "weak" and level == "beginner":
            score += 3
        if preparation == "strong" and level == "intermediate":
            score += 2
        if score > 0:
            scored.append((score, resource_to_card(r)))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:limit]]


def _pool_materials(
    *,
    sphere: str,
    track: Optional[str],
    preparation: str,
    learning_path: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    def add(card: Dict[str, Any]) -> None:
        url = (card.get("url") or "").strip()
        if url and url != "#" and url not in seen:
            seen.add(url)
            merged.append(card)

    for c in _flatten_path_resources(learning_path):
        add(c)
    for c in _catalog_resources_for_track(sphere, track, preparation, limit=6):
        add(c)
    return merged[:14]


def _pick_materials(
    materials: List[Dict[str, Any]],
    *,
    keywords: Tuple[str, ...],
    limit: int = 2,
    used_urls: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    used = used_urls if used_urls is not None else set()
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for m in materials:
        url = m.get("url") or ""
        if url in used:
            continue
        blob = " ".join(
            str(m.get(k) or "")
            for k in ("title", "description", "kind", "provider", "step_title")
        ).lower()
        score = sum(3.0 for kw in keywords if kw and kw in blob)
        if score > 0:
            scored.append((score, m))
    if not scored and materials:
        for m in materials:
            if (m.get("url") or "") not in used:
                scored.append((0.5, m))
    scored.sort(key=lambda x: -x[0])
    picked: List[Dict[str, Any]] = []
    for _, m in scored[:limit]:
        url = m.get("url") or ""
        if url:
            used.add(url)
        picked.append(
            {
                "title": m.get("title"),
                "url": url,
                "kind": m.get("kind") or "ресурс",
                "provider": m.get("provider"),
            }
        )
    return picked


def _step(
    text: str,
    materials: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {"text": text, "materials": materials or []}


def _rule_based_plan_advice(
    plan: Dict[str, Any],
    *,
    preparation: str,
    profile: Dict[str, Any],
    gap: Dict[str, Any],
    sphere: str,
    materials: List[Dict[str, Any]],
    pain_step: Optional[str],
    priority: List[str],
) -> Dict[str, Any]:
    plan_name = _plan_label(plan)
    track = _infer_track_from_plan(plan_name)
    used: Set[str] = set()
    steps: List[Dict[str, Any]] = []

    intro_kw = ("курс", "intro", "beginner", "основ", "python", track or "обучен")
    if preparation == "weak":
        intro_m = _pick_materials(materials, keywords=intro_kw, limit=2, used_urls=used)
        steps.append(
            _step(
                f"Начните с короткого вводного трека по «{plan_name}» (10–15 ч): закрепите базу перед откликами.",
                intro_m,
            )
        )
    elif preparation == "medium":
        steps.append(
            _step(
                f"Закрепите средний уровень по «{plan_name}»: один учебный модуль + одна практическая задача в неделю.",
                _pick_materials(materials, keywords=(track or "practice", "практик", "exercism"), limit=2, used_urls=used),
            )
        )
    else:
        steps.append(
            _step(
                f"У вас уже сильная база — углубите «{plan_name}» через pet-проект или open-source на 2–3 недели.",
                _pick_materials(materials, keywords=("github", "portfolio", "project", track or ""), limit=2, used_urls=used),
            )
        )

    if pain_step:
        steps.insert(0, _step(pain_step, _pick_materials(materials, keywords=("карьер", "резюме"), limit=1, used_urls=used)))

    skill_focus = priority[0] if priority else "навыки из разрыва"
    steps.append(
        _step(
            f"Закройте приоритет «{skill_focus}»: выберите 1 материал, доведите до артефакта (конспект, мини-кейс или код).",
            _pick_materials(
                materials,
                keywords=tuple(re.split(r"\s+", skill_focus.lower())[:3]) + (track or "",),
                limit=2,
                used_urls=used,
            ),
        )
    )

    steps.append(
        _step(
            "Трио самоисследования: сильные стороны, текущие интересы, готовность решать запросы других (не только «для себя»).",
        )
    )
    steps.append(
        _step(
            "Зафиксируйте карьерные ценности (якоря Шейна): что в работе опора — экспертиза, автономия, вызов или баланс.",
        )
    )
    steps.append(
        _step(
            "Резюме и отклики: обновите 3 буллета под «"
            + plan_name
            + "»; попросите близких назвать ваши сильные стороны.",
            _pick_materials(materials, keywords=("резюме", "карьер", "stepik", "roadmap"), limit=1, used_urls=used),
        )
    )
    steps.append(
        _step(
            "Сопоставьте тип среды (Голланд) и комфорт в команде: общение vs регламент, логика vs отношения.",
        )
    )

    return {
        "title": plan.get("name", "План"),
        "plan_direction": plan_name,
        "track": track,
        "priority_skills": priority[:3],
        "steps": steps[:6],
        "source": "rules",
    }


def _parse_llm_advice_json(raw: str) -> Optional[Dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return None
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _merge_llm_plan(
    plan_id: str,
    plan: Dict[str, Any],
    llm_block: Dict[str, Any],
    *,
    fallback: Dict[str, Any],
) -> Dict[str, Any]:
    steps_in = llm_block.get("steps") or []
    steps: List[Dict[str, Any]] = []
    for item in steps_in[:6]:
        if isinstance(item, str):
            steps.append(_step(item))
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("step") or "").strip()
            if not text:
                continue
            mats = []
            for m in item.get("materials") or []:
                if isinstance(m, dict) and m.get("url"):
                    mats.append(
                        {
                            "title": m.get("title") or "Материал",
                            "url": m.get("url"),
                            "kind": m.get("kind") or "ресурс",
                            "provider": m.get("provider"),
                        }
                    )
            steps.append(_step(text, mats))
    if not steps:
        return fallback
    return {
        "title": llm_block.get("title") or plan.get("name") or f"План {plan_id}",
        "plan_direction": _plan_label(plan),
        "track": fallback.get("track"),
        "priority_skills": llm_block.get("priority_skills") or fallback.get("priority_skills"),
        "steps": steps,
        "source": "llm",
    }


def build_individual_advice(
    *,
    scenarios: Dict[str, Any],
    preparation_level: str,
    profile: Dict[str, Any],
    gap: Dict[str, Any],
    interest: str,
    learning_path: Optional[Dict[str, Any]] = None,
    profile_summary: str = "",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Советы по планам A/B/C с материалами.
    При наличии LLM — персонализация; иначе правила + каталог/путь обучения.
    """
    from wibe_work.services.career_analysis import _PAIN_FIRST_STEP, _resolve_effective_interest

    plans = scenarios.get("plans") or []
    sphere = _resolve_effective_interest(profile, interest)
    pain_id = (profile.get("primary_pain") or "").strip()
    pain_step = _PAIN_FIRST_STEP.get(pain_id) if pain_id else None
    priority = _priority_skills(gap)

    if learning_path is None and user_id is not None:
        learning_path = build_learning_path_payload(
            user_id=user_id,
            profile=profile,
            interest=interest,
            preparation_level=preparation_level,
            scenarios=scenarios,
            gap=gap,
        )

    by_plan: Dict[str, Any] = {}
    materials_global = _pool_materials(
        sphere=sphere,
        track=_infer_track_from_plan(_plan_label(plans[0]) if plans else ""),
        preparation=preparation_level,
        learning_path=learning_path,
    )

    # LLM: один запрос на все планы
    llm_by_plan: Dict[str, Any] = {}
    if llm_configured() and plans and profile_summary:
        mat_lines = []
        for i, m in enumerate(materials_global[:12], 1):
            mat_lines.append(
                f"{i}. [{m.get('kind')}] {m.get('title')} — {m.get('url')} ({m.get('provider')})"
            )
        prompt = build_advice_user_prompt(
            profile_summary=profile_summary,
            preparation_level=preparation_level,
            priority_skills=priority,
            plans=plans,
            materials_list="\n".join(mat_lines) or "—",
            pain_hint=pain_step or "",
        )
        raw, _ = fetch_llm_completion(
            prompt,
            max_tokens=1200,
            temperature=0.45,
            system_prompt=ADVICE_JSON_SYSTEM,
        )
        parsed = _parse_llm_advice_json(raw or "")
        if parsed:
            llm_by_plan = parsed.get("by_plan") or parsed

    for p in plans:
        pid = str(p.get("id") or "A")
        track = _infer_track_from_plan(_plan_label(p))
        mats = _pool_materials(
            sphere=sphere,
            track=track,
            preparation=preparation_level,
            learning_path=learning_path,
        )
        fallback = _rule_based_plan_advice(
            p,
            preparation=preparation_level,
            profile=profile,
            gap=gap,
            sphere=sphere,
            materials=mats,
            pain_step=pain_step if pid == "A" else None,
            priority=priority,
        )
        llm_block = llm_by_plan.get(pid) if isinstance(llm_by_plan, dict) else None
        if isinstance(llm_block, dict) and llm_block.get("steps"):
            by_plan[pid] = _merge_llm_plan(pid, p, llm_block, fallback=fallback)
        else:
            by_plan[pid] = fallback

    return {
        "by_plan": by_plan,
        "source": "llm" if any(b.get("source") == "llm" for b in by_plan.values()) else "rules",
    }
