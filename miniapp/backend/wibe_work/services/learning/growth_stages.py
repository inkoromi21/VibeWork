"""Этапы роста: понятный план с привязкой к советам и пути обучения."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from wibe_work.services.learning.personalized_advice import (
    _human_skill_label,
    _infer_track_from_plan,
    _material_card,
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


def _readiness_intro(readiness_percent: int, preparation: str) -> str:
    prep = _prep_label(preparation)
    if readiness_percent < 35:
        return (
            f"Сейчас готовность около {readiness_percent}% — это нормальный старт ({prep} уровень). "
            "Двигайтесь маленькими шагами: один фокус в неделю, без попытки закрыть всё сразу."
        )
    if readiness_percent < 60:
        return (
            f"Готовность около {readiness_percent}% ({prep} уровень). "
            "На этом этапе важно закрыть пару навыков из разрыва и сделать один понятный результат — конспект, задачу или пункт в резюме."
        )
    return (
        f"Готовность около {readiness_percent}% — база уже заметна. "
        "Можно быстрее переходить к практике и откликам, если нет дыр в ключевых навыках."
    )


def _best_plan_block(
    advice: Optional[Dict[str, Any]],
    scenarios: Dict[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    by = (advice or {}).get("by_plan") or {}
    pid = str(scenarios.get("best_plan_id") or "A")
    block = by.get(pid) or by.get("A") or {}
    return pid, block if isinstance(block, dict) else {}


def _plan_step(label: str, text: str) -> Dict[str, str]:
    return {"label": label, "text": text}


def _advice_lines(block: Dict[str, Any], limit: int = 2) -> List[str]:
    """Короткие формулировки из индивидуальных советов (секции или шаги)."""
    out: List[str] = []
    for sec in block.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        for st in sec.get("steps") or []:
            if isinstance(st, dict):
                t = str(st.get("text") or "").strip()
                if t:
                    out.append(t[:220])
            if len(out) >= limit:
                return out
    for st in block.get("steps") or []:
        if isinstance(st, str) and st.strip():
            out.append(st.strip()[:220])
        elif isinstance(st, dict):
            t = str(st.get("text") or "").strip()
            if t:
                out.append(t[:220])
        if len(out) >= limit:
            break
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
            card = _material_card(res)
            card["path_step"] = step.get("title")
            out.append(card)
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


def _path_route(path_steps: List[Dict[str, Any]]) -> str:
    titles = [str(s.get("title") or "").strip() for s in path_steps if s.get("title")]
    return " → ".join(titles[:4]) if titles else ""


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
    """Три этапа: вводный текст, пошаговый план, чеклист, материалы."""
    priority = [_human_skill_label(s) for s in _priority_skills(gap)]
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
    intro_base = _readiness_intro(readiness_percent, preparation_level)
    advice_lines = _advice_lines(plan_block, limit=2)
    like = (profile.get("like_to_do") or "").strip()[:80]

    s1_path = _path_steps_slice(learning_path, 1)
    s1_titles = [str(s.get("title") or "") for s in s1_path if s.get("title")]
    first_path = s1_titles[0] if s1_titles else "первый шаг из пути обучения"
    s1_mats = _merge_materials(
        _materials_from_steps(s1_path, limit=3),
        _pick_materials(
            pool,
            keywords=("курс", "intro", "roadmap", "основ", track or "карьер"),
            limit=2,
            used_urls=used_urls,
            track=track,
        ),
        limit=4,
    )

    s1_plan: List[Dict[str, str]] = [
        _plan_step(
            "Поймите себя",
            "Выпишите 5 сильных сторон — из школы, хобби, помощи людям. "
            "Отметьте, от чего появляется энергия, а что «надо», но не тянет.",
        ),
        _plan_step(
            "Сверьте с направлением",
            f"Посмотрите на трек «{plan_name}» и навыки из разрыва"
            + (f" ({top_skills})" if top_skills else "")
            + ". Решите, что подтянуть в первую очередь — один пункт, не пять.",
        ),
        _plan_step(
            "Начните обучение",
            f"Пройдите «{first_path}» из пути ниже или один материал из списка — "
            "с коротким итогом: что поняли и что сделали руками.",
        ),
    ]
    if preparation_level == "weak":
        s1_plan[2] = _plan_step(
            "Начните с базы",
            f"Возьмите вводный курс или урок по «{plan_name}» — 20–30 минут в день. "
            f"Цель этапа: закрыть 1–2 навыка из разрыва ({top_skills or 'база по сфере'}).",
        )
    if advice_lines:
        s1_plan.append(_plan_step("Из ваших советов", advice_lines[0][:200]))

    s1_intro = intro_base + f" Этап 1 — подготовка к «{plan_name}» (план {plan_id})."
    if like:
        s1_intro += f" В анкете: «{like}» — можно опереться на это при выборе задач."

    horizon_1 = "3–5 недель" if preparation_level == "weak" else "2–4 недели"

    # --- Этап 2 ---
    s2_path = _path_steps_slice(learning_path, 2)
    s2_mats = _merge_materials(
        _materials_from_steps(s2_path, limit=4),
        _pick_materials(
            pool,
            keywords=("практик", "exercism", "git", "stepik", track or ""),
            limit=2,
            used_urls=used_urls,
            track=track,
        ),
        limit=5,
    )
    s2_advice = _advice_lines(plan_block, limit=3)
    s2_plan = [
        _plan_step(
            "Закройте разрыв",
            f"Потренируйтесь в навыках: {top_skills or 'по вашей сфере'}. "
            "Минимум 3 маленькие задачи или один учебный мини-кейс.",
        ),
        _plan_step(
            "Соберите резюме",
            f"Черновик под «{plan_name}»: три пункта «что сделал» с фактом или цифрой. "
            "Можно попросить близких назвать ваши сильные стороны — часто видят то, что вы сами не замечаете.",
        ),
        _plan_step(
            "Закрепите практикой",
            "Pet-проект, репозиторий на GitHub или учебный кейс — что можно показать ссылкой.",
        ),
    ]
    if preparation_level == "strong":
        s2_plan[2] = _plan_step(
            "Углубите практику",
            "Pet-проект или вклад в open-source сильнее ещё одного курса на вашем уровне.",
        )
    elif preparation_level == "medium":
        s2_plan[2] = _plan_step(
            "Ритм практики",
            "Одна практическая задача в неделю (код, Git, макет — по сфере) + фиксация в конспекте.",
        )
    if len(s2_advice) > 1:
        s2_plan.append(_plan_step("Подсказка из советов", s2_advice[1][:200]))

    # --- Этап 3 ---
    s3_path = _path_steps_slice(learning_path, 3)
    s3_mats = _merge_materials(
        _materials_from_steps(s3_path, limit=4),
        _pick_materials(
            pool,
            keywords=("portfolio", "github", "ваканс", "отклик", track or ""),
            limit=2,
            used_urls=used_urls,
            track=track,
        ),
        limit=5,
    )
    s3_advice = _advice_lines(plan_block, limit=3)
    apply_hint = (
        "8–12 точечных откликов и 2–3 разговора с работодателями."
        if readiness_percent >= 55
        else "5 целевых откликов: после каждого — что спросили и что подтянуть, без массовой рассылки."
    )
    s3_plan = [
        _plan_step(
            "Выходите на рынок",
            f"Откликайтесь под «{plan_name}» — с сопроводительным под конкретную вакансию. {apply_hint}",
        ),
        _plan_step(
            "Сверяйте с вакансиями",
            f"Сравнивайте требования с вашими навыками: {top_skills or 'список из разрыва'}.",
        ),
        _plan_step(
            "Докрутите портфолио",
            "Обновите кейс или проект с этапа 2 по обратной связи с откликов и собеседований.",
        ),
    ]
    if s3_advice:
        s3_plan.append(_plan_step("Из ваших советов", s3_advice[-1][:200]))

    def _stage(
        *,
        stage: int,
        title: str,
        subtitle: str,
        intro: str,
        horizon: str,
        focus_tags: List[str],
        plan: List[Dict[str, str]],
        checklist: List[str],
        when_next: str,
        path_steps: List[Dict[str, Any]],
        materials: List[Dict[str, Any]],
        continues_from: Optional[str] = None,
        advice_refs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        route = _path_route(path_steps)
        return {
            "stage": stage,
            "title": title,
            "subtitle": subtitle,
            "intro": intro,
            "body": intro,
            "horizon": horizon,
            "focus_tags": focus_tags,
            "plan": plan,
            "checklist": checklist,
            "milestones": checklist,
            "when_next": when_next,
            "path_route": route,
            "path_steps": [str(s.get("title") or "") for s in path_steps if s.get("title")][:4],
            "readiness_percent": readiness_percent,
            "preparation_level": preparation_level,
            "priority_skills": priority[:3],
            "linked_plan_id": plan_id,
            "advice_refs": advice_refs or [],
            "materials": materials,
            "continues_from": continues_from,
        }

    return [
        _stage(
            stage=1,
            title="Разберитесь с собой и заложите базу",
            subtitle=f"К «{plan_name}» · план {plan_id}",
            intro=s1_intro,
            horizon=horizon_1,
            focus_tags=["Старт", _prep_label(preparation_level).capitalize()],
            plan=s1_plan[:4],
            checklist=[
                "5 сильных сторон — с примерами из жизни",
                "Коротко: что для вас важно в работе (рост, стабильность, творчество…)",
                f"Пройден «{first_path}» или один материал из списка ниже",
            ],
            when_next=(
                "Когда понятно, что вас мотивирует, и есть первый результат обучения "
                f"({first_path})."
            ),
            path_steps=s1_path,
            materials=s1_mats,
            advice_refs=advice_lines[:1],
        ),
        _stage(
            stage=2,
            title="Практика и резюме",
            subtitle=f"Подтягиваем: {top_skills[:50] or 'навыки из разрыва'}",
            intro=(
                f"Этап 2 — из «кто я» к «что могу показать работодателю» по треку «{plan_name}». "
                "Опирайтесь на сильные стороны с этапа 1 в формулировках резюме."
            ),
            horizon="2–6 недель",
            focus_tags=["Практика", "Резюме"],
            plan=s2_plan[:4],
            checklist=[
                f"Черновик резюме под «{plan_name}»",
                "3 достижения с фактом или цифрой",
                "Артефакт практики: репозиторий, кейс или макет",
            ],
            when_next="Когда резюме можно показать наставнику или другу, и есть ссылка на работу (GitHub, Behance, документ).",
            path_steps=s2_path,
            materials=s2_mats,
            continues_from="С этапа 1: сильные стороны и ценности → три пункта в резюме",
            advice_refs=s2_advice[:2],
        ),
        _stage(
            stage=3,
            title="Рынок и закрепление трека",
            subtitle=f"Отклики · {plan_name[:40]}",
            intro=(
                f"Этап 3 — проверка «{plan_name}» на реальном рынне. "
                "Резюме и практика с этапа 2 — основа для откликов."
            ),
            horizon="1–3 месяца",
            focus_tags=["Отклики", "Собеседования"],
            plan=s3_plan[:4],
            checklist=[
                "5–12 целевых откликов (по уровню готовности)",
                "2–3 разговора с работодателем или на стажировку",
                "Портфолио обновлено по обратной связи",
            ],
            when_next="Когда есть стажировка, оффер или чёткий список навыков, которые докрутить дальше.",
            path_steps=s3_path,
            materials=s3_mats,
            continues_from="С этапа 2: резюме + практика → точечные отклики",
            advice_refs=s3_advice[-1:] if s3_advice else [],
        ),
    ]
