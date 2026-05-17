"""Мини-план на 4 недели."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.career_analysis import _weekly_roadmap


def test_weekly_roadmap_mini_plan_fields() -> None:
    weeks = _weekly_roadmap("Метрики и контроль качества", "it_dev", preparation="medium")
    assert len(weeks) == 2
    w0 = weeks[0]
    assert w0["week_range"] == "Недели 1–2"
    assert w0.get("learn") and w0.get("practice") and w0.get("outcome")
    blob = " ".join(w0[k] for k in ("learn", "practice", "outcome"))
    assert "ваканс" in blob.lower() or "рынок" in blob.lower() or "git" in blob.lower()


def test_weekly_roadmap_weak_prep() -> None:
    weeks = _weekly_roadmap("Backend", "it_dev", preparation="weak")
    assert "окруж" in weeks[0]["learn"].lower() or "вводн" in weeks[0]["practice"].lower()
