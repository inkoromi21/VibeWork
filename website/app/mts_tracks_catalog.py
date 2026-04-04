"""Каталог профессий из матрицы компетенций МТС (импорт из Excel)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "mts_matrix.json"


class MtsTrack(BaseModel):
    id: str
    title: str
    requirements: list[str]
    duties: list[str]
    profession_tag: str = Field(
        description="Тег для сопоставления с фильтрами интересов / вакансий",
    )


def _slug(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9а-яё]+", "-", s, flags=re.IGNORECASE)
    return s.strip("-")[:80]


def _infer_tag(title: str) -> str:
    t = title.lower()
    if "аналитик" in t and "ai" in t:
        return "IT"
    if "сопровожден" in t and "рабоч" in t:
        return "IT"
    if "инженер" in t or "линейно-кабель" in t:
        return "инженерия"
    if "маркетинг" in t:
        return "маркетинг"
    if "продавец" in t or "рознич" in t:
        return "маркетинг"
    if "продаж" in t or "развития" in t:
        return "маркетинг"
    if "корпоратив" in t or "клиент" in t:
        return "бизнес"
    if "hr" in t or "стажер hr" in t:
        return "бизнес"
    if "юрист" in t:
        return "бизнес"
    if "закуп" in t:
        return "бизнес"
    if "недвижим" in t or "эксплуатац" in t and "здан" in t:
        return "бизнес"
    if "транспорт" in t:
        return "инженерия"
    if "административн" in t or "хозяйствен" in t:
        return "бизнес"
    return "бизнес"


@lru_cache
def load_mts_tracks() -> tuple[MtsTrack, ...]:
    if not DATA_FILE.is_file():
        return ()
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    out: list[MtsTrack] = []
    for item in raw:
        title = item["title"]
        out.append(
            MtsTrack(
                id=_slug(title),
                title=title,
                requirements=list(item.get("requirements") or []),
                duties=list(item.get("duties") or []),
                profession_tag=_infer_tag(title),
            )
        )
    return tuple(out)
