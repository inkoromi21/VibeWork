"""Подшаги внутри этапа пути обучения (материалы и цель)."""

from __future__ import annotations

from typing import Any, Dict, List

SUBSTEP_SEP = "__"


def substep_storage_id(step_id: str, sub_id: str) -> str:
    return f"{step_id}{SUBSTEP_SEP}{sub_id}"


def parse_storage_id(storage_id: str) -> tuple[str, str | None]:
    if SUBSTEP_SEP in storage_id:
        parent, sub = storage_id.split(SUBSTEP_SEP, 1)
        return parent, sub or None
    return storage_id, None


def build_substeps_for_step(
    *,
    goal: str | None,
    resources: List[Dict[str, Any]] | None,
) -> List[Dict[str, Any]]:
    """Контракт подшага для UI и прогресса (только материалы; цель — в шапке этапа)."""
    substeps: List[Dict[str, Any]] = []
    goal_txt = (goal or "").strip()
    for i, res in enumerate(resources or []):
        title = str(res.get("title") or "Материал").strip() or "Материал"
        substeps.append(
            {
                "sub_id": f"res{i}",
                "title": title,
                "url": (res.get("url") or "").strip(),
                "kind": str(res.get("kind") or "").strip(),
                "description": str(res.get("description") or "")[:240],
                "provider": res.get("provider"),
                "status": "pending",
            }
        )
    if not substeps:
        substeps.append(
            {
                "sub_id": "main",
                "title": "Выполнить этап",
                "description": goal_txt,
                "status": "pending",
            }
        )
    return substeps


def attach_substeps_to_step(step: Dict[str, Any]) -> Dict[str, Any]:
    row = dict(step)
    if not row.get("substeps"):
        row["substeps"] = build_substeps_for_step(
            goal=row.get("goal"),
            resources=row.get("resources"),
        )
    return row
