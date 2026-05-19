"""Подключение банков вопросов из website/app/aptitude_quiz_content.py (10 тех. по сфере)."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO = Path(__file__).resolve().parents[3]
_WEBSITE = _REPO / "website"
if _WEBSITE.is_dir() and str(_WEBSITE) not in sys.path:
    sys.path.insert(0, str(_WEBSITE))

# id сферы в анкете миниаппа → ключ в INTEREST_QUIZZES (сайт)
INTEREST_TO_WEBSITE_QUIZ_KEY: Dict[str, str] = {
    "it_dev": "IT",
    "data": "данные_и_AI",
    "design": "дизайн",
    "marketing": "маркетинг",
    "sales": "продажи",
    "engineering": "инженерия",
    "mgmt": "продукт_и_PMO",
    "finance": "финансы_и_контроль",
    "hr_edu": "HR_и_рекрутинг",
    "logistics": "логистика",
    "medicine": "наука",
    "education": "бизнес",
    "creative": "дизайн",
    "sport": "бизнес",
    "other": "IT",
}

TECHNICAL_COUNT = 10
PERSONALITY_COUNT = 5
PERSONALITY_ID_START = 11


def _normalize_website_question(raw: Dict[str, Any], qid: int) -> Dict[str, Any]:
    opts = []
    for o in raw.get("options") or []:
        if "id" in o:
            opts.append({"id": o["id"], "label": o.get("label", "")})
        else:
            opts.append({"id": o.get("k", "A"), "label": o.get("t", "")})
    return {
        "id": qid,
        "text": str(raw.get("text") or "").strip(),
        "options": opts,
        "block": "technical",
    }


def fetch_technical_from_website(interest: str) -> Optional[List[Dict[str, Any]]]:
    """10 вопросов по сфере через pick_quiz_questions сайта."""
    try:
        from app.aptitude_quiz_content import pick_quiz_questions
    except ImportError:
        return None

    key = INTEREST_TO_WEBSITE_QUIZ_KEY.get((interest or "").strip(), "IT")
    try:
        bank, _resolved = pick_quiz_questions(key, None)
    except Exception:
        return None
    if not bank or len(bank) < TECHNICAL_COUNT:
        return None
    out: List[Dict[str, Any]] = []
    for i, q in enumerate(bank[:TECHNICAL_COUNT], start=1):
        out.append(_normalize_website_question(q, i))
    return out


def personality_track_for_interest(interest: str) -> str:
    k = (interest or "").strip()
    if k in ("it_dev", "data", "engineering"):
        return "tech"
    if k in ("design", "creative", "marketing"):
        return "creative"
    if k in ("sales", "hr_edu", "mgmt", "education"):
        return "people"
    return "general"
