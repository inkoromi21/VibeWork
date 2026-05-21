# website/

Два назначения каталога:

1. **`frontend/`** — общая статика (`/static/...`) и **старый лендинг** на `GET /` (при `miniapp/run.py`).
2. **`app/`** — legacy HTTP API `/api/*` и мосты к `wibe_work` (разбор, learning, симулятор).

Основной UI продукта — **`miniapp/frontend/`** на `/miniapp/`. См. [корневой README](../README.md).

## Режимы запуска

### Unified (как в проде)

Из корня репозитория:

```bash
python miniapp/run.py
```

Один процесс: `/miniapp/`, `/vibework/...`, `/api/...`, `/static/...`, общая SQLite. **`.env` только в корне** — [docs/ENV.md](../docs/ENV.md).

### Изолированный (отладка только `website/app`)

```bash
cd website
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py    # порт 8765 по умолчанию
```

Нет `/miniapp/` и `/vibework/...`. Своя БД: `website/data/vibework.db`, cookie-сессии в `app/`.

### Full stack через `website/main.py`

Тот же API, что `miniapp/run.py`:

```bash
cd website
pip install -r requirements.txt -r requirements-unified.txt
export VIBEWORK_FULL_STACK=1   # Windows: set VIBEWORK_FULL_STACK=1
export PORT=8000               # опционально
python main.py
```

На **Python 3.14 (Windows)** при ошибках сборки pydantic используйте 3.11–3.12 или см. версии в `requirements.txt`.

## `frontend/`

| Файл | Использование |
|------|----------------|
| `style.css`, `miniapp-shell.css`, `vw_shared_ui.js`, … | Подключаются из Mini App как `/static/...` |
| `index.html`, `script.js` | Старый клиент на `/` |
| `register.html` | `GET /register` |

## `app/` (кратко)

| Модуль | Роль |
|--------|------|
| `career_advisor.py` | Чат, jobs, обёртка `/api/analyze` |
| `analysis_bridge.py` | Веб-payload → `wibe_work.services.career_analysis` |
| `*_bridge.py` | Learning, симулятор, quiz bundle |
| `aptitude_quiz_content.py` | Банк вопросов теста (импорт через bridge в wibe_work) |
| `hh_client.py` | hh.ru для legacy `/api/*` |
| `mts_matrix.json` | Каталог для `/api/mts/tracks` (отдельно от `miniapp/data/mts_role_matrix.json`) |
| `orm_models.py`, `account_auth_routes.py` | Только **изолированный** `main.py` |

Примеры API: `/api/analyze`, `/api/chat`, `/api/jobs`, `/api/simulator/start` — полный список в `/docs` запущенного процесса.

Переменные LLM в unified-режиме — **`CHAT_API_*`** в корневом `.env`, не `website/.env`. Пример для изолированного режима: `.env.example` в этом каталоге.
