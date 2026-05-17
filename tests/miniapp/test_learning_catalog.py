"""Описания материалов в пути обучения."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.learning.catalog import get_resource, resource_to_card


def test_curated_resources_have_description() -> None:
    for rid in ("roadmap_backend", "cs50_intro", "stepik_python"):
        r = get_resource(rid)
        assert r is not None
        card = resource_to_card(r)
        assert card["description"]
        assert len(card["description"]) > 20
