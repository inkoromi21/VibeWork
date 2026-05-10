"""Текстовый симулятор «день на работе» — сценарии под сферы из анкеты (INTEREST_SPHERES)."""

from __future__ import annotations

from typing import Any, Dict, List

from wibe_work.questionnaire_fields import INTEREST_SPHERES

# Главная сфера (id из анкеты) → внутренний ключ сценария в _STORIES
SPHERE_TO_SIM: Dict[str, str] = {
    "it_dev": "developer",
    "data": "analyst",
    "design": "designer",
    "marketing": "marketing",
    "sales": "sales",
    "mgmt": "pm",
    "engineering": "engineer",
    "finance": "finance",
    "hr_edu": "hr",
    "other": "analyst",
}

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
                {"id": "hybrid", "label": "Ищу компромиссный вариант"},
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
    "developer": [
        {
            "id": 0,
            "text": "10:15 — в бэклоге три задачи: баг в проде, фича к релизу, рефакторинг модуля.",
            "choices": [
                {"id": "bug", "label": "Сначала баг — прод лежит"},
                {"id": "feat", "label": "Фича — обещали заказчику"},
                {"id": "ref", "label": "Рефакторинг — потом быстрее всё"},
            ],
            "points": {"bug": 4, "feat": 3, "ref": 2},
        },
        {
            "id": 1,
            "text": "14:30 — на ревью спорят: упростить API или добавить флаг совместимости.",
            "choices": [
                {"id": "simple", "label": "Упрощаем контракт"},
                {"id": "flag", "label": "Флаг + дока для старых клиентов"},
                {"id": "pair", "label": "Парное ревью и компромисс"},
            ],
            "points": {"simple": 3, "flag": 4, "pair": 4},
        },
        {
            "id": 2,
            "text": "18:45 — пайплайн зелёный, но деплой можно только ночью.",
            "choices": [
                {"id": "now", "label": "Катим сейчас с мониторингом"},
                {"id": "night", "label": "Переношу на окно ночью"},
                {"id": "canary", "label": "Canary на часть трафика"},
            ],
            "points": {"now": 2, "night": 3, "canary": 4},
        },
    ],
    "marketing": [
        {
            "id": 0,
            "text": "09:00 — кампания в соцсетях даёт CTR ниже плана на треть.",
            "choices": [
                {"id": "creative", "label": "Меняю креативы и заголовки"},
                {"id": "audience", "label": "Пересобираю сегмент аудитории"},
                {"id": "report", "label": "Сводка для руководства + гипотезы"},
            ],
            "points": {"creative": 3, "audience": 4, "report": 2},
        },
        {
            "id": 1,
            "text": "13:00 — контент-директор просит «виральное» видео к пятнице при нулевом бюджете.",
            "choices": [
                {"id": "ugc", "label": "Запускаю UGC с пользователями"},
                {"id": "clip", "label": "Короткий ролик своими силами"},
                {"id": "honest", "label": "Честно пишу про ограничения бюджета"},
            ],
            "points": {"ugc": 4, "clip": 3, "honest": 4},
        },
        {
            "id": 2,
            "text": "17:30 — нужно согласовать пост с юристами и брендом за час.",
            "choices": [
                {"id": "parallel", "label": "Параллельно пишу двум спискам правок"},
                {"id": "soft", "label": "Мягкая версия без спорных формулировок"},
                {"id": "move", "label": "Перенос на понедельник с превью"},
            ],
            "points": {"parallel": 4, "soft": 3, "move": 2},
        },
    ],
    "sales": [
        {
            "id": 0,
            "text": "11:00 — лид из холодной базы ответил: интересно, но цена высокая.",
            "choices": [
                {"id": "value", "label": "Письмо с ценностью и кейсом"},
                {"id": "call", "label": "Сразу звонок — уточнить боли"},
                {"id": "trial", "label": "Предлагаю пробный формат"},
            ],
            "points": {"value": 3, "call": 4, "trial": 4},
        },
        {
            "id": 1,
            "text": "15:00 — клиент просит скидку 25%, иначе уйдёт к конкуренту.",
            "choices": [
                {"id": "bundle", "label": "Пакет услуг вместо скидки"},
                {"id": "mgmt", "label": "Подключаю руководителя"},
                {"id": "walk", "label": "Вежливо отпускаю — маржа важнее"},
            ],
            "points": {"bundle": 4, "mgmt": 3, "walk": 2},
        },
        {
            "id": 2,
            "text": "18:00 — в CRM висят задачи, дедлайн отчёта по воронке — сегодня.",
            "choices": [
                {"id": "auto", "label": "Автозаполнение из CRM + ручные правки"},
                {"id": "honest2", "label": "Честный статус «часть данных завтра»"},
                {"id": "night2", "label": "Доделываю вечером"},
            ],
            "points": {"auto": 4, "honest2": 3, "night2": 2},
        },
    ],
    "pm": [
        {
            "id": 0,
            "text": "09:45 — в спринт добавили «ещё маленькую фичу» без оценки.",
            "choices": [
                {"id": "no", "label": "Не берём — переносим в бэклог"},
                {"id": "trade", "label": "Меняем приоритет: выкидываем другое"},
                {"id": "timebox", "label": "Берём с таймбоксом 1 день"},
            ],
            "points": {"no": 3, "trade": 4, "timebox": 3},
        },
        {
            "id": 1,
            "text": "14:00 — две команды блокируют друг друга общим сервисом.",
            "choices": [
                {"id": "sync2", "label": "Общий синк и договорённости в письме"},
                {"id": "tmp", "label": "Временный контракт API"},
                {"id": "escalate", "label": "Эскалация архитектору"},
            ],
            "points": {"sync2": 4, "tmp": 4, "escalate": 2},
        },
        {
            "id": 2,
            "text": "17:15 — руководство просит ETA по релизу «на вчера».",
            "choices": [
                {"id": "range", "label": "Диапазон дат + риски"},
                {"id": "mvp2", "label": "MVP-дата и полный релиз отдельно"},
                {"id": "no2", "label": "Отказываюсь фиксировать без буфера"},
            ],
            "points": {"range": 4, "mvp2": 4, "no2": 2},
        },
    ],
    "engineer": [
        {
            "id": 0,
            "text": "08:30 — испытание прототипа: параметр не вписывается в допуск.",
            "choices": [
                {"id": "measure", "label": "Перепроверяю методику и датчики"},
                {"id": "redesign", "label": "Корректирую конструкцию"},
                {"id": "report2", "label": "Фиксирую отчёт и следующий шаг"},
            ],
            "points": {"measure": 4, "redesign": 3, "report2": 3},
        },
        {
            "id": 1,
            "text": "12:30 — поставщик задерживает комплектующие на две недели.",
            "choices": [
                {"id": "alt", "label": "Ищу альтернативного поставщика"},
                {"id": "planb", "label": "План Б без этих узлов"},
                {"id": "contract", "label": "Юридическое письмо по договору"},
            ],
            "points": {"alt": 4, "planb": 3, "contract": 2},
        },
        {
            "id": 2,
            "text": "16:45 — нужно подписать акт приёмки и передать заказчику.",
            "choices": [
                {"id": "strict", "label": "Только после повторных тестов"},
                {"id": "cond", "label": "Акт с условиями и списком доработок"},
                {"id": "sign", "label": "Подписываю — доработки отдельным этапом"},
            ],
            "points": {"strict": 4, "cond": 4, "sign": 2},
        },
    ],
    "finance": [
        {
            "id": 0,
            "text": "10:00 — фактические расходы отклоняются от прогноза на 12%.",
            "choices": [
                {"id": "drill", "label": "Дрилл-даун по статьям и центрам"},
                {"id": "forecast", "label": "Обновляю прогноз и сценарии"},
                {"id": "meet", "label": "Созвон с владельцами бюджетов"},
            ],
            "points": {"drill": 4, "forecast": 3, "meet": 4},
        },
        {
            "id": 1,
            "text": "14:30 — аудит запросил документы по прошлому кварталу до конца дня.",
            "choices": [
                {"id": "pack", "label": "Собираю пакет из того, что есть"},
                {"id": "partial", "label": "Частичная выгрузка + план добора"},
                {"id": "help", "label": "Подключаю коллег из учёта"},
            ],
            "points": {"pack": 3, "partial": 4, "help": 4},
        },
        {
            "id": 2,
            "text": "18:30 — руководитель просит дашборд «одним экраном» к утру.",
            "choices": [
                {"id": "mvp3", "label": "Упрощённый дашборд в таблице"},
                {"id": "bi", "label": "Черновик в BI с фильтрами"},
                {"id": "morning", "label": "Честно: к утру только KPI"},
            ],
            "points": {"mvp3": 3, "bi": 4, "morning": 4},
        },
    ],
    "hr": [
        {
            "id": 0,
            "text": "09:15 — кандидат на финальном этапе перестал выходить на связь.",
            "choices": [
                {"id": "wait", "label": "Ещё одно нейтральное напоминание"},
                {"id": "close", "label": "Закрываю воронку и фиксирую причину"},
                {"id": "backup", "label": "Ускоряю запасного кандидата"},
            ],
            "points": {"wait": 2, "close": 3, "backup": 4},
        },
        {
            "id": 1,
            "text": "13:00 — обучение для сотрудников накладывается на релиз проекта.",
            "choices": [
                {"id": "split", "label": "Делю на два потока"},
                {"id": "record", "label": "Запись + живой Q&A позже"},
                {"id": "shift", "label": "Перенос даты с согласования"},
            ],
            "points": {"split": 4, "record": 3, "shift": 3},
        },
        {
            "id": 2,
            "text": "17:00 — конфликт между руководителем и сотрудником, оба пишут вам.",
            "choices": [
                {"id": "1to1", "label": "Отдельные 1:1, потом совместно"},
                {"id": "policy", "label": "По регламенту и документирование"},
                {"id": "mediate", "label": "Медиация с нейтральным местом"},
            ],
            "points": {"1to1": 4, "policy": 3, "mediate": 4},
        },
    ],
}


def normalize_role(role_or_sphere: str) -> str:
    """Принимает ключ сценария или id сферы из анкеты; возвращает ключ из _STORIES."""
    key = (role_or_sphere or "").strip()
    if not key:
        return "analyst"
    if key in SPHERE_TO_SIM:
        key = SPHERE_TO_SIM[key]
    if key in _STORIES:
        return key
    return "analyst"


def _choice_label(step: Dict[str, Any], choice_id: str) -> str:
    for c in step.get("choices") or []:
        if c.get("id") == choice_id:
            return str(c.get("label") or choice_id)
    return choice_id


def _format_day_recap(
    path: List[Dict[str, Any]], total_points: int, closing: str
) -> str:
    lines: List[str] = ["Как вы прошли день:", ""]
    for i, item in enumerate(path, 1):
        scene = str(item.get("scene") or "").strip()
        choice = str(item.get("choice") or "").strip()
        pts = int(item.get("points") or 0)
        lines.append(f"{i}. {scene}")
        lines.append(f"   → Ваш выбор: «{choice}» (+{pts} оч.).")
        lines.append("")
    lines.append(f"Итого за день: {total_points} карьерных очков.")
    lines.append(closing)
    return "\n".join(lines)


def list_simulator_options() -> List[Dict[str, str]]:
    """Одна строка на каждую рекомендуемую сферу — как в главной сфере анкеты."""
    out: List[Dict[str, str]] = []
    for s in INTEREST_SPHERES:
        sid = s["id"]
        label = s["label"]
        role = normalize_role(sid)
        out.append({"sphere_id": sid, "label": label, "role": role})
    return out


def start(role: str) -> Dict[str, Any]:
    r = normalize_role(role)
    steps = _STORIES.get(r) or _STORIES["analyst"]
    first = steps[0]
    return {
        "role": r,
        "step_index": 0,
        "career_points": 0,
        "day_path": [],
        "node": {
            "text": first["text"],
            "choices": first["choices"],
        },
        "done": False,
    }


def step(
    role: str,
    step_index: int,
    career_points: int,
    choice_id: str,
    day_path: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    r = normalize_role(role)
    steps = _STORIES.get(r) or _STORIES["analyst"]
    idx = max(0, min(len(steps) - 1, int(step_index)))
    cur = steps[idx]
    add = int(cur.get("points", {}).get(choice_id, 1))
    new_points = career_points + add
    path = list(day_path) if day_path else []
    path.append(
        {
            "scene": cur.get("text") or "",
            "choice": _choice_label(cur, choice_id),
            "points": add,
        }
    )
    next_idx = idx + 1
    closing = "День закончен. Сохраняйте баланс глубины, коммуникации и скорости — так растёт и реальная карьера."
    if next_idx >= len(steps):
        return {
            "role": r,
            "step_index": next_idx,
            "career_points": new_points,
            "day_path": path,
            "node": None,
            "done": True,
            "summary": closing,
            "day_recap": _format_day_recap(path, new_points, closing),
        }
    nxt = steps[next_idx]
    return {
        "role": r,
        "step_index": next_idx,
        "career_points": new_points,
        "day_path": path,
        "node": {"text": nxt["text"], "choices": nxt["choices"]},
        "done": False,
    }
