"""Текстовый симулятор «день на работе»."""

from typing import Any, Dict, List

_STORIES: Dict[str, List[Dict[str, Any]]] = {
    "analyst": [
        {
            "id": 0,
            "text": "09:30 — в чате просят срочно проверить метрику «конверсия в заявку» за вчера. Дашборд показывает просадку.",
            "choices": [
                {"id": "deep", "label": "Копаюсь в сырых данных и SQL"},
                {"id": "ask", "label": "Пишу владельцу метрики за уточнениями"},
                {"id": "viz", "label": "Строю быстрый график по сегментам"},
            ],
            "points": {"deep": 3, "ask": 2, "viz": 2},
        },
        {
            "id": 1,
            "text": "12:00 — на встрече спорят: менять определение метрики или чинить пайплайн.",
            "choices": [
                {"id": "doc", "label": "Предлагаю зафиксировать определение в wiki"},
                {"id": "fix", "label": "Иду чинить пайплайн с инженером"},
                {"id": "both", "label": "Делим: я — данные, он — код"},
            ],
            "points": {"doc": 2, "fix": 3, "both": 4},
        },
        {
            "id": 2,
            "text": "17:00 — нужно за 20 минут дать комментарий руководству.",
            "choices": [
                {"id": "short", "label": "Три буллета + риск"},
                {"id": "long", "label": "Подробный разбор в доке"},
                {"id": "call", "label": "Устно на созвоне"},
            ],
            "points": {"short": 4, "long": 2, "call": 3},
        },
    ],
    "designer": [
        {
            "id": 0,
            "text": "10:00 — продукт просит «освежить» онбординг за неделю.",
            "choices": [
                {"id": "research", "label": "Сначала 3 интервью с новичками"},
                {"id": "ui", "label": "Сразу новые экраны в Figma"},
                {"id": "bench", "label": "Смотрю референсы конкурентов"},
            ],
            "points": {"research": 4, "ui": 2, "bench": 2},
        },
        {
            "id": 1,
            "text": "14:00 — разработка говорит, что макет не попадает в гайдлайны.",
            "choices": [
                {"id": "sync", "label": "Созвон и правки компонентов"},
                {"id": "push", "label": "Отстаиваю UX-решение"},
                {"id": "hybrid", "label": "Ищу компромисс вариант"},
            ],
            "points": {"sync": 4, "push": 2, "hybrid": 3},
        },
        {
            "id": 2,
            "text": "18:00 — дедлайн завтра, осталась анимация перехода.",
            "choices": [
                {"id": "mvp", "label": "Упрощаю до fade"},
                {"id": "polish", "label": "Довожу motion как задумано"},
                {"id": "defer", "label": "Прошу сдвиг на день"},
            ],
            "points": {"mvp": 3, "polish": 4, "defer": 1},
        },
    ],
}


def start(role: str) -> Dict[str, Any]:
    r = "designer" if role == "designer" else "analyst"
    steps = _STORIES.get(r) or _STORIES["analyst"]
    first = steps[0]
    return {
        "role": r,
        "step_index": 0,
        "career_points": 0,
        "node": {
            "text": first["text"],
            "choices": first["choices"],
        },
        "done": False,
    }


def step(role: str, step_index: int, career_points: int, choice_id: str) -> Dict[str, Any]:
    r = "designer" if role == "designer" else "analyst"
    steps = _STORIES.get(r) or _STORIES["analyst"]
    idx = max(0, min(len(steps) - 1, int(step_index)))
    cur = steps[idx]
    add = int(cur.get("points", {}).get(choice_id, 1))
    new_points = career_points + add
    next_idx = idx + 1
    if next_idx >= len(steps):
        return {
            "role": r,
            "step_index": next_idx,
            "career_points": new_points,
            "node": None,
            "done": True,
            "summary": "День закончен. Сохраните баланс исследования, коммуникации и скорости.",
        }
    nxt = steps[next_idx]
    return {
        "role": r,
        "step_index": next_idx,
        "career_points": new_points,
        "node": {"text": nxt["text"], "choices": nxt["choices"]},
        "done": False,
    }
