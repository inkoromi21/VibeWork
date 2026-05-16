"""
Схема анкеты — единый источник в wibe_work.questionnaire_fields (миниапп / API :8000).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "miniapp" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from wibe_work.questionnaire_fields import (  # noqa: E402
    INTEREST_SPHERES,
    get_profile_schema,
)

__all__ = ["INTEREST_SPHERES", "get_profile_schema"]
