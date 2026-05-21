# website/

Два назначения:

1. **`frontend/`** — общая статика (`/static/...`) и **старый лендинг** на `GET /` (при `miniapp/run.py`).
2. **`app/`** — legacy API `/api/*` и мосты к `wibe_work`.

Основной UI — **`miniapp/frontend/`** на `/miniapp/`. См. [корневой README](../README.md).

## Режимы запуска

### Unified (как в проде)

Из **корня** репозитория:

```bash
python miniapp/run.py
# или
docker compose up --build
```

Один процесс: `/miniapp/`, `/vibework/...`, `/api/...`, `/static/...`, одна SQLite. **`.env` только в корне** — [docs/ENV.md](../docs/ENV.md).

### Изолированный (только `website/app`)

```bash
cd website
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py    # порт 8765
```

Нет `/miniapp/` и `/vibework/...`. БД: `website/data/vibework.db`, cookie-сессии в `app/`.

### Full stack через `website/main.py`

Тот же API, что `miniapp/run.py`:

```bash
cd website
pip install -r requirements.txt -r requirements-unified.txt
export VIBEWORK_FULL_STACK=1   # Windows: set VIBEWORK_FULL_STACK=1
export PORT=8000               # по желанию
python main.py
```

На Python 3.14 (Windows) при сбое сборки pydantic — Python 3.11–3.12.

## `frontend/`

- **`style.css`**, **`miniapp-shell.css`**, **`vw_shared_ui.js`**, … — Mini App подключает как `/static/...`
- **`index.html`**, **`script.js`** — старый клиент на `/`
- **`register.html`** — `GET /register`

## `app/` (кратко)

- **`career_advisor.py`** — чат, jobs, обёртка `/api/analyze`
- **`analysis_bridge.py`** — веб-payload → `wibe_work.services.career_analysis`
- **`*_bridge.py`** — learning, симулятор, quiz
- **`aptitude_quiz_content.py`** — банк вопросов теста
- **`hh_client.py`** — hh.ru для legacy `/api/*`
- **`mts_matrix.json`** — `/api/mts/tracks` (отдельно от `miniapp/data/mts_role_matrix.json`)
- **`orm_models.py`**, **`account_auth_routes.py`** — только изолированный `main.py`

Примеры API: `/api/analyze`, `/api/chat`, `/api/jobs`, `/api/simulator/start` — полный список в `/docs` у запущенного процесса.

LLM в unified-режиме — **`CHAT_API_*`** в корневом `.env`. Для изолированного режима — `website/.env.example`.
