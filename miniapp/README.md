# miniapp/

Ядро продукта: пакет **`wibe_work`**, Mini App, данные, бот. HTTP-вход — **`python miniapp/run.py`** из **корня репозитория** (не из этого каталога).

Общая архитектура и запуск: [README в корне](../README.md). Переменные: [docs/ENV.md](../docs/ENV.md).

## Маршруты (при `run.py`)

| Путь | Файл / API |
|------|------------|
| `/miniapp/` | `frontend/index.html` |
| `/vibework/...` | `backend/wibe_work/routers/assessment_routes.py` — анкета, тест, разбор, чат |
| `/career/...` | `career_routes.py` — hh, вакансии, отчёт |
| `/static/...` | Статика из `../website/frontend/` |

## Каталог

| Путь | Назначение |
|------|------------|
| `run.py` | uvicorn → `wibe_work.main:app`, :8000 |
| `backend/wibe_work/` | Роутеры, SQLite, сервисы (LLM, learning, hh) |
| `frontend/` | Mini App; `admin/`, `reset-password.html` |
| `data/` | `learning_paths.json`, `mts_role_matrix.json`, БД по умолчанию |
| `bot/` | [bot/README.md](bot/README.md) |
| `terminal_theme.py` | Вывод в консоль для `run.py` и бота |
| `scripts/` | Утилиты (не рантайм) |

## Запуск

```bash
# из корня репозитория
python miniapp/run.py
```
