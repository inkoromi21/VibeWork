"""Подшаги пути обучения и прогресс по ним."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.learning.engine import merge_learning_progress_in_snapshot
from wibe_work.services.learning.progress import apply_progress_to_steps, compute_metrics, set_step_status
from wibe_work.services.learning.substeps import attach_substeps_to_step, build_substeps_for_step


def test_build_substeps_from_resources() -> None:
    subs = build_substeps_for_step(
        goal="Понять основы",
        resources=[{"title": "Курс A", "url": "https://example.com/a", "kind": "курс"}],
    )
    assert len(subs) == 1
    assert subs[0]["sub_id"] == "res0"
    assert subs[0]["title"] == "Курс A"
    assert not any(s["sub_id"] == "goal" for s in subs)


def test_substep_progress_updates_parent_and_metrics() -> None:
    uid = "u_sub_" + uuid.uuid4().hex[:8]
    step = attach_substeps_to_step(
        {
            "step_id": "be-1",
            "title": "Шаг 1",
            "goal": "Цель",
            "resources": [{"title": "Roadmap", "url": "https://roadmap.sh"}],
        }
    )
    snap = {"learning_path": {"path_id": "p_sub", "steps": [step]}}
    set_step_status(uid, "p_sub", "be-1__res0", "done", steps=[step])
    merged = merge_learning_progress_in_snapshot(snap, uid)
    lp = merged["learning_path"]
    assert lp["steps"][0]["substeps"][0]["status"] == "done"
    assert lp["steps"][0]["status"] == "done"
    m = lp["metrics"]
    assert m["total_substeps"] >= 1
    assert m["completed_substeps"] == 1


def test_parent_checkbox_marks_all_substeps() -> None:
    uid = "u_par_" + uuid.uuid4().hex[:8]
    step = attach_substeps_to_step(
        {
            "step_id": "s1",
            "title": "A",
            "goal": "G",
            "resources": [],
        }
    )
    set_step_status(uid, "p_par", "s1", "done", steps=[step])
    merged = merge_learning_progress_in_snapshot(
        {"learning_path": {"path_id": "p_par", "steps": [step]}},
        uid,
    )
    subs = merged["learning_path"]["steps"][0]["substeps"]
    assert all(s["status"] == "done" for s in subs)
    assert merged["learning_path"]["steps"][0]["status"] == "done"
    assert merged["learning_path"]["metrics"]["coverage_percent"] == 100
