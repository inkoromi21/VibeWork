"""Путь обучения и каталог."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.learning.engine import build_learning_for_analysis
from wibe_work.services.learning.catalog import pick_path


def test_pick_backend_path() -> None:
    p = pick_path("it_dev", "backend", "medium")
    assert p is not None
    assert p.get("id") == "it_dev_backend_junior"


def test_learning_pack_backend_has_steps() -> None:
    profile = {"main_sphere": "it_dev", "preparation_level": "medium"}
    scenarios = {"inferred_profession": {"track_id": "backend", "label": "Backend"}}
    pack = build_learning_for_analysis(
        user_id=None,
        profile=profile,
        interest="it_dev",
        preparation_level="medium",
        scenarios=scenarios,
        gap=None,
    )
    lp = pack.get("learning_path") or {}
    steps = lp.get("steps") or []
    assert len(steps) >= 5
    first = steps[0]
    assert first.get("resources")
    names = " ".join(
        (r.get("title") or "") for s in steps for r in (s.get("resources") or [])
    ).lower()
    assert "python" in names or "cs50" in names or "roadmap" in names
    assert pack.get("learning")
