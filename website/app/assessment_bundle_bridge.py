"""Мост к wibe_work.quiz_web_bundle для веб-опроса (общий код с миниаппом)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "miniapp" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from wibe_work.services.quiz_web_bundle import quiz_bundle_for_web  # noqa: E402


def quiz_bundle_for_website(profile: dict[str, Any], form_interest: str) -> dict[str, Any]:
    """Совместимое имя для вызовов из career_advisor."""
    return quiz_bundle_for_web(profile, form_interest)
