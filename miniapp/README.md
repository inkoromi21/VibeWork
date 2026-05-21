# miniapp/

Ядро продукта: **`wibe_work`**, Mini App, данные, бот. HTTP-вход — **`python miniapp/run.py`** из **корня репозитория** (не из этого каталога).

- Архитектура и Docker: [README в корне](../README.md)
- Переменные: [docs/ENV.md](../docs/ENV.md)

## Маршруты (при `run.py` на :8000)

- **`/miniapp/`** — `frontend/index.html`
- **`/vibework/...`** — анкета, тест, разбор, чат (`routers/assessment_routes.py`)
- **`/career/...`** — hh.ru, вакансии, отчёт (`career_routes.py`)
- **`/static/...`** — статика из `../website/frontend/`

## Содержимое каталога

- **`run.py`** — uvicorn → `wibe_work.main:app`
- **`backend/wibe_work/`** — FastAPI, SQLite, LLM, learning, hh
- **`frontend/`** — Mini App; `admin/`, `reset-password.html`
- **`data/`** — `learning_paths.json`, `mts_role_matrix.json`; SQLite по умолчанию
- **`bot/`** — [bot/README.md](bot/README.md)
- **`terminal_theme.py`** — вывод в консоль для `run.py` и бота
- **`scripts/`** — утилиты (не рантайм)

## Запуск

```bash
# из корня репозитория
python miniapp/run.py
```

Или из корня: `docker compose up --build` (см. корневой README).
