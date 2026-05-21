# VibeWork

Карьерная платформа: анкета, тест, ИИ-разбор, чат, вакансии (hh.ru), симулятор. Один сервер FastAPI — веб, Mini App в Telegram, REST API.

**Бот:** [@VibeWorks_bot](https://t.me/VibeWorks_bot)

## Именование

- **VibeWork** — продукт в UI и текстах
- **`wibe_work`** — Python-пакет (`miniapp/backend/wibe_work/`)
- **`vibework`** — БД, cookie, пути на VPS (нижний регистр)
- **@VibeWorks_bot** — Telegram-бот (имя с «s»)

## Архитектура

**Режим по умолчанию:** `python miniapp/run.py` → `wibe_work.main`, порт **8000**, SQLite (`DATABASE_PATH` в `.env` или `miniapp/data/`).

```
miniapp/run.py
    ├── wibe_work/          ядро: /vibework/*, /career/*, auth, admin
    ├── website/app/       legacy-адаптер: /api/* (чат, analyze, jobs…)
    ├── miniapp/frontend/  основной UI → GET /miniapp/
    └── website/frontend/  статика /static/* + старый лендинг → GET /
```

**Маршруты (локально :8000):**

- **`/miniapp/`** — основной продукт (`miniapp/frontend/index.html`, API `/vibework/...`)
- **`/`** — старый веб-клиент (`website/frontend/index.html`, `script.js`)
- **`/static/...`** — CSS/JS из `website/frontend/` (нужны Mini App)
- **`/register`**, **`/reset-password`**, **`/admin`** — отдельные страницы
- **`/docs`** — OpenAPI

В BotFather для Web App укажите **`https://<домен>/miniapp/`**, не корень `/`.

Конфигурация: **`.env` в корне`** — шаблон [.env.example](.env.example), описание [docs/ENV.md](docs/ENV.md).

## Запуск через Docker

Нужны [Docker](https://docs.docker.com/get-docker/) и Compose v2.

```bash
cp .env.example .env
docker compose up --build
```

После старта:

- http://127.0.0.1:8000/miniapp/ — интерфейс
- http://127.0.0.1:8000/docs — API
- http://127.0.0.1:8000/api/health — проверка процесса

Остановка: `docker compose down`. БД в volume `vibework_data` (`/data/vibework.db` в контейнере). JSON-каталоги обучения — из образа.

## Быстрый старт без Docker

```bash
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r miniapp/requirements.txt
cp .env.example .env
python miniapp/run.py
```

Проверка: `/miniapp/`, `/docs`, `GET /api/health/llm` (поля `llm_configured`, `ok`, `model`).

## Разработка

- **API + UI (Docker):** `docker compose up --build`
- **API + UI (локально):** `python miniapp/run.py`
- **Бот** (API уже запущен): `python miniapp/bot/bot.py`
- **Полный dev-стек** (API, бот, website :8765): `bash "launch files/launch-stack.sh"` или `launch files\launch-stack.bat`
- **Тесты:** `./scripts/verify.sh` или `pytest tests/miniapp -q`

Изолированный веб без Mini App — [website/README.md](website/README.md).

## LLM

В `.env`: `CHAT_API_URL`, `CHAT_API_KEY`, `CHAT_MODEL` (OpenAI-совместимый API). Код: `miniapp/backend/wibe_work/services/llm_client.py`, промпты: `llm_prompts.py`.

## Продакшен

Уникальный `JWT_SECRET`, HTTPS, CORS, `HH_USER_AGENT`. Nginx: [deploy/VPS-HTTPS.md](deploy/VPS-HTTPS.md).

## Документация

- [miniapp/README.md](miniapp/README.md) — каталог `miniapp/`
- [miniapp/bot/README.md](miniapp/bot/README.md) — Telegram-бот
- [website/README.md](website/README.md) — legacy UI и изолированный сервер
- [docs/ENV.md](docs/ENV.md) — переменные окружения
- [docs/LEARNING_INTEGRATIONS.md](docs/LEARNING_INTEGRATIONS.md) — обучение и внешние API (VK Video и др.)
- [SECURITY.md](SECURITY.md) — уязвимости

## Структура репозитория

```
VibeWork/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── miniapp/
│   ├── run.py
│   ├── backend/wibe_work/
│   ├── frontend/
│   ├── data/
│   └── bot/
├── website/
│   ├── app/
│   └── frontend/
├── tests/miniapp|website/
├── scripts/
├── deploy/
└── docs/
```

Лицензия: [LICENSE](LICENSE) (MIT).
