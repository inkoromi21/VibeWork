"""Полный контекст пользователя для карьерного ИИ-чата."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _trunc(s: str, n: int) -> str:
    t = (s or "").strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def _format_learning_path(lp: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    title = lp.get("title") or "Путь обучения"
    metrics = lp.get("metrics") or {}
    lines.append(
        f"Путь «{title}»: прогресс {metrics.get('coverage_percent', 0)}%, "
        f"шаг {int(metrics.get('current_step_index', 0)) + 1} из {metrics.get('total_steps', '?')}"
    )
    steps = lp.get("steps") or []
    for st in steps[:5]:
        status = st.get("status") or "pending"
        lines.append(f"  — [{status}] {st.get('title', '')}: { _trunc(str(st.get('goal') or ''), 80)}")
        for res in (st.get("resources") or [])[:2]:
            lines.append(f"      · {res.get('title', '')} ({res.get('provider', '')}) {res.get('url', '')}")
    return lines


def _format_advice(advice: Dict[str, Any], scenarios: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    by = advice.get("by_plan") or {}
    if not by:
        return lines
    best = str(scenarios.get("best_plan_id") or "A")
    lines.append(f"Индивидуальные советы (лучший план {best}):")
    block = by.get(best) or by.get("A") or {}
    intro = (block.get("intro") or "").strip()
    if intro:
        lines.append(f"  {_trunc(intro, 200)}")
    for sk in block.get("priority_skills") or []:
        lines.append(f"  Приоритет: {sk}")
    for i, st in enumerate(block.get("steps") or [], 1):
        if isinstance(st, str):
            lines.append(f"  {i}. {_trunc(st, 160)}")
        elif isinstance(st, dict):
            lines.append(f"  {i}. {_trunc(str(st.get('text') or ''), 160)}")
            for m in (st.get("materials") or [])[:2]:
                lines.append(f"      → {m.get('title', '')}: {m.get('url', '')}")
    return lines


def _format_growth_stages(stages: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for s in (stages or [])[:3]:
        intro = _trunc(str(s.get("intro") or s.get("body") or ""), 100)
        lines.append(
            f"Этап {s.get('stage')}: {s.get('title', '')} ({s.get('horizon', '')}) — {intro}"
        )
    return lines


def _format_learning_cards(cards: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for c in (cards or [])[:6]:
        lines.append(f"  · [{c.get('kind', '')}] {c.get('title', '')} — {c.get('url', '')}")
    return lines


def _format_quiz_summary(snap: Dict[str, Any]) -> str:
    answers = snap.get("_quiz_answers")
    if not answers or not isinstance(answers, list):
        return ""
    return f"Опрос: {len(answers)} ответов (полная методика — 15). Используй выводы разбора, не переспрашивай всё заново."


def build_comprehensive_chat_context(
    *,
    analysis_snap: Optional[Dict[str, Any]],
    profile_snippet: str = "",
    directions_hint: str = "",
) -> str:
    """
    Единый блок: анкета, метрики, разбор, материалы, советы, этапы.
    Передаётся в system-prompt чата.
    """
    if not analysis_snap and not profile_snippet:
        return ""

    sections: List[str] = []
    sections.append(
        "Ниже — все данные, которые пользователь уже дал сервису, и что сервис ему посчитал. "
        "Опирайся на них; не выдумывай факты. Если чего-то нет — спроси точечно."
    )

    if profile_snippet.strip():
        sections.append("=== Анкета ===\n" + profile_snippet.strip())

    if not analysis_snap:
        if directions_hint.strip():
            sections.append("=== Направления ===\n" + directions_hint.strip())
        return "\n\n".join(sections)

    snap = analysis_snap
    lines: List[str] = ["=== Разбор и метрики ==="]

    ps = (snap.get("profile_summary") or "").strip()
    if ps:
        lines.append("Сводка: " + _trunc(ps, 500))

    readiness = snap.get("readiness") or {}
    if readiness.get("value_percent") is not None:
        lines.append(f"Индекс готовности: {readiness['value_percent']}%")

    axes = (snap.get("style_radar") or {}).get("axes") or []
    if axes:
        ax = "; ".join(
            f"{a.get('label', '?')}: {a.get('value_percent', '?')}%"
            for a in axes[:8]
        )
        lines.append("Оси методики: " + ax)

    narrative = (snap.get("ai_narrative") or "").strip()
    if narrative:
        lines.append("ИИ-нарратив разбора: " + _trunc(narrative, 600))

    scenarios = snap.get("scenarios") or {}
    plans = scenarios.get("plans") or []
    if plans:
        pl = ", ".join(
            f"{p.get('id')}: {p.get('name', '')} (~{p.get('score_percent', '?')}%)"
            for p in plans[:3]
        )
        lines.append("Планы A/B/C: " + pl)
    inf = snap.get("inferred_profession") or scenarios.get("inferred_profession")
    if isinstance(inf, dict) and inf.get("title"):
        lines.append(f"Уточнённая профессия: {inf.get('title')} (трек {inf.get('track_id', '')})")

    gap = snap.get("gap_analysis") or {}
    closing = gap.get("closing_skills") or []
    if closing:
        lines.append("Закрыть в первую очередь: " + ", ".join(str(x) for x in closing[:6]))
    for bar in (gap.get("bars") or [])[:4]:
        lab = bar.get("label") or bar.get("key")
        pct = bar.get("value_percent") or bar.get("percent")
        if lab is not None and pct is not None:
            lines.append(f"  Навык «{lab}»: {pct}%")

    pain = snap.get("pain_focus") or {}
    if pain.get("label"):
        tips = "; ".join(str(t) for t in (pain.get("tips") or [])[:2] if t)
        lines.append(f"Фокус боли: {pain['label']}" + (f" — {tips}" if tips else ""))

    quiz_line = _format_quiz_summary(snap)
    if quiz_line:
        lines.append(quiz_line)

    bh = (snap.get("behavioral_hint") or "").strip()
    if bh:
        lines.append("Поведение в тесте: " + _trunc(bh, 200))

    sections.append("\n".join(lines))

    lp = snap.get("learning_path") or {}
    if lp.get("steps"):
        sections.append("=== Путь обучения ===\n" + "\n".join(_format_learning_path(lp)))

    learn = snap.get("learning") or []
    if learn:
        sections.append("=== Рекомендованные материалы ===\n" + "\n".join(_format_learning_cards(learn)))

    advice = snap.get("individual_advice") or {}
    adv_lines = _format_advice(advice, scenarios)
    if adv_lines:
        sections.append("=== Индивидуальные советы ===\n" + "\n".join(adv_lines))

    stages = snap.get("growth_stages") or []
    if stages:
        sections.append("=== Этапы роста ===\n" + "\n".join(_format_growth_stages(stages)))

    weekly = snap.get("weekly_roadmap") or []
    if weekly:
        wk_lines = []
        for w in weekly[:2]:
            if w.get("learn"):
                wk_lines.append(
                    f"{w.get('week_range', '')}: изучить — {_trunc(str(w.get('learn')), 80)}; "
                    f"итог — {_trunc(str(w.get('outcome')), 60)}"
                )
            else:
                topics = ", ".join(str(t) for t in (w.get("topics") or [])[:4])
                wk_lines.append(f"{w.get('week_range', '')}: {topics}")
        sections.append("=== План на недели ===\n" + "\n".join(wk_lines))

    mts = (snap.get("mts_matrix") or {}).get("rows") or []
    if mts:
        top = ", ".join(
            f"{r.get('role_name', '')} ({r.get('match_percent', '?')}%)"
            for r in mts[:3]
            if r.get("role_name")
        )
        if top:
            sections.append("=== Роли (матрица) — топ ===\n" + top)

    if directions_hint.strip():
        sections.append("=== Подсказка направлений ===\n" + directions_hint.strip())

    return "\n\n".join(sections)[:12000]


def build_context_aware_fallback(
    last_user: str,
    *,
    analysis_snap: Optional[Dict[str, Any]],
    profile_snippet: str,
) -> str:
    """Ответ без LLM, но с опорой на сохранённые данные."""
    parts: List[str] = []
    if analysis_snap:
        r = (analysis_snap.get("readiness") or {}).get("value_percent")
        narrative = (analysis_snap.get("ai_narrative") or "").strip()
        if narrative:
            parts.append(_trunc(narrative, 280))
        elif r is not None:
            parts.append(f"По вашему разбору индекс готовности {r}%.")
        lp = analysis_snap.get("learning_path") or {}
        steps = lp.get("steps") or []
        if steps:
            idx = int((lp.get("metrics") or {}).get("current_step_index") or 0)
            st = steps[min(idx, len(steps) - 1)]
            parts.append(f"Сейчас по пути обучения: «{st.get('title', '')}».")
    elif profile_snippet.strip():
        parts.append("Разбор ещё не сохранён — пройдите тест во вкладке «Тест».")
    else:
        parts.append("Заполните анкету и пройдите тест — тогда советы станут точными.")

    if last_user:
        parts.append(f"По вашему вопросу («{_trunc(last_user, 80)}»): уточните, если нужен разбор вакансий, обучения или резюме.")
    return " ".join(parts)
