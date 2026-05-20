"""
Поисковые фразы для hh.ru: id сферы анкеты и код Interest → короткий text для API и web.

Синхронизировано с miniapp/wibe_work/services/hh_filter.py (_SPHERE_ID_TO_HH_PHRASE).
"""

from __future__ import annotations

import re
from typing import Optional

from app.api_schemas import Interest

# id сферы в анкете → поле text (GET /vacancies, web /search/vacancy)
SPHERE_ID_TO_HH_TEXT: dict[str, str] = {
    "it_dev": "разработчик программист",
    "data": "аналитик данных",
    "design": "UX дизайнер",
    "creative": "дизайнер креатив",
    "marketing": "маркетолог",
    "sales": "менеджер по продажам",
    "logistics": "логист",
    "medicine": "медицинский регистратор",
    "education": "преподаватель",
    "engineering": "инженер",
    "mgmt": "менеджер проектов",
    "finance": "финансовый аналитик",
    "hr_edu": "рекрутер HR",
    "sport": "тренер инструктор",
    "other": "стажировка начинающий специалист",
}

# Значение Interest (как в API) → text
INTEREST_TO_HH_TEXT: dict[str, str] = {
    Interest.IT.value: "разработчик программист",
    Interest.DATA_AI.value: "аналитик данных",
    Interest.DEVOPS.value: "devops инженер",
    Interest.DESIGN.value: "UX дизайнер",
    Interest.MARKETING.value: "маркетолог",
    Interest.SALES.value: "менеджер по продажам",
    Interest.ENGINEERING.value: "инженер",
    Interest.SCIENCE.value: "лаборант научный сотрудник",
    Interest.BUSINESS.value: "менеджер проектов",
    Interest.FINANCE.value: "финансовый аналитик",
    Interest.HR.value: "рекрутер HR",
    Interest.LEGAL.value: "юрист",
    Interest.PROCUREMENT.value: "менеджер по закупкам",
    Interest.LOGISTICS.value: "логист",
    Interest.REAL_ESTATE.value: "специалист недвижимость",
    Interest.ADMIN.value: "офис менеджер администратор",
    Interest.PRODUCT.value: "product manager",
    Interest.SUPPORT.value: "специалист поддержки",
}


def _label_to_sphere_id(label: str) -> Optional[str]:
    from wibe_work.questionnaire_fields import INTEREST_SPHERES

    low = label.strip().lower()
    if not low:
        return None
    for s in INTEREST_SPHERES:
        sid = str(s.get("id") or "")
        if low == sid.lower() or low == str(s.get("label") or "").lower():
            return sid
    return None


def search_text_for_match(
    *,
    interest: str | None = None,
    sphere_id: str | None = None,
    profession: str | None = None,
    track_hint: str | None = None,
) -> str:
    """
    Короткая фраза для hh.ru (без OR-простыней): сфера анкеты → роль, иначе Interest / план из разбора.
    """
    raw = (profession or sphere_id or "").strip()
    if raw:
        if raw in SPHERE_ID_TO_HH_TEXT:
            return SPHERE_ID_TO_HH_TEXT[raw]
        sid = _label_to_sphere_id(raw)
        if sid and sid in SPHERE_ID_TO_HH_TEXT:
            return SPHERE_ID_TO_HH_TEXT[sid]
        if len(raw) >= 4 and " or " not in raw.lower():
            return raw[:120]

    hint = (track_hint or "").strip()
    if hint:
        clean = re.sub(r"^(Вариант|План)\s+[ABC]:\s*", "", hint, flags=re.IGNORECASE).strip()
        if len(clean) > 4:
            return clean[:120]

    intr = (interest or "").strip()
    if intr:
        if intr in INTEREST_TO_HH_TEXT:
            return INTEREST_TO_HH_TEXT[intr]
        try:
            ie = Interest(intr)
            return INTEREST_TO_HH_TEXT.get(ie.value, "вакансии")
        except ValueError:
            return intr[:120]

    return "вакансии"
