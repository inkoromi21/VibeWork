"""Мост веб-API симулятора к wibe_work.workday_simulator (все сферы анкеты)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "miniapp" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from wibe_work.services.workday_simulator import (  # noqa: E402
    ROLE_LABELS,
    list_simulator_options,
    normalize_role,
    start as sim_start,
    step as sim_step,
    story_steps_for_role,
)

from app.api_schemas import SimulatorAdvance, SimulatorChoice, SimulatorState, SimulatorStep

_STEP_TITLES = (
    "Утро",
    "Середина дня",
    "Вечер",
    "Итог",
)


def simulator_options_list() -> list[dict[str, str]]:
    return list_simulator_options()


def _step_title(role: str, step_index: int, *, is_final: bool) -> str:
    if is_final:
        prof = ROLE_LABELS.get(role, role)
        return f"Итог дня — {prof}"
    if step_index < len(_STEP_TITLES) - 1:
        return f"{_STEP_TITLES[step_index]} ({ROLE_LABELS.get(role, role)})"
    return ROLE_LABELS.get(role, role)


def _points_for_choice(raw_step: dict[str, Any], choice_id: str) -> int:
    pts = raw_step.get("points") or {}
    return int(pts.get(choice_id, 1))


def _to_simulator_step(raw: dict[str, Any]) -> SimulatorStep:
    role = str(raw.get("role") or "analyst")
    idx = int(raw.get("step_index") or 0)
    pts = int(raw.get("career_points") or 0)
    if raw.get("done"):
        narrative = str(raw.get("day_recap") or raw.get("summary") or "").strip()
        return SimulatorStep(
            step_index=idx,
            title=_step_title(role, idx, is_final=True),
            narrative=narrative,
            choices=[],
            career_points=pts,
            is_final=True,
            sim_role=role,
            day_path=list(raw.get("day_path") or []),
        )
    node = raw.get("node") or {}
    story_steps = story_steps_for_role(role)
    cur = story_steps[min(idx, len(story_steps) - 1)]
    choices = [
        SimulatorChoice(
            id=str(c["id"]),
            label=str(c["label"]),
            points_delta=_points_for_choice(cur, str(c["id"])),
        )
        for c in node.get("choices") or []
    ]
    return SimulatorStep(
        step_index=idx,
        title=_step_title(role, idx, is_final=False),
        narrative=str(node.get("text") or ""),
        choices=choices,
        career_points=pts,
        is_final=False,
        sim_role=role,
        day_path=list(raw.get("day_path") or []),
    )


def simulator_start(role_key: str) -> SimulatorStep:
    raw = sim_start(role_key)
    return _to_simulator_step(raw)


def simulator_advance(adv: SimulatorAdvance) -> SimulatorStep:
    st = adv.state
    day_path = list(st.day_path) if st.day_path else None
    raw = sim_step(
        st.role_key,
        st.step_index,
        st.career_points,
        adv.choice_id,
        day_path,
    )
    return _to_simulator_step(raw)
