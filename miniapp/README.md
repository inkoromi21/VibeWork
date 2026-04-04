# Мини-приложение Telegram (VibeWork)

Карьерный навигатор в Telegram: **REST API** (`wibe_work`), **Web App** (статика) и **бот** (long polling). Всё, что относится к миниаппе, лежит в этой папке.

## Структура

| Путь | Назначение |
|------|------------|
| `backend/wibe_work/` | Пакет FastAPI: маршруты, БД, интеграции (HH, LLM и т.д.) |
| `frontend/` | Мини-приложение (`index.html` и ресурсы), отдаётся с `GET /miniapp/` |
| `data/` | SQLite и JSON-данные миниаппы (создаётся при работе; старый `data/` в корне репо подхватывается при миграции) |
| `bot/` | Telegram-бот — [bot/README.md](bot/README.md) |
| `scripts/` | Ollama, распаковка RAR, Windows-обёртки |

Файл **`.env`** для API и бота — в **корне монорепозитория**. Шаблон: из корня выполните **`cp miniapp/.env.example .env`**.

Зависимости: **`miniapp/requirements.txt`** (`pip install -r miniapp/requirements.txt` из корня при активном корневом `venv`).

## Запуск

Из **корня**: полный стек — `bash "launch files/launch-stack.sh"` (Windows: `launch files\launch-stack.bat`); только API для отладки — `python miniapp/run.py`. Подробнее — [README.md](../README.md).
