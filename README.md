# VibeWork

Карьерная платформа: анкета, тест, ИИ-разбор, чат, вакансии (hh.ru), симулятор. Один сервер FastAPI — веб, Mini App в Telegram, REST API.

**Бот:** [@VibeWorks_bot](https://t.me/VibeWorks_bot)

## Именование

| Контекст | Форма |
|----------|--------|
| Продукт в UI и текстах | **VibeWork** |
| Python-пакет | `wibe_work` (`miniapp/backend/wibe_work/`) |
| БД, cookie, пути на VPS | `vibework` (нижний регистр) |
| Telegram | @VibeWorks_bot |

## Архитектура

**Режим по умолчанию:** `python miniapp/run.py` → `wibe_work.main`, порт **8000**, одна SQLite (путь — `DATABASE_PATH` в `.env`, иначе `miniapp/data/`).

```
miniapp/run.py
    ├── wibe_work/          ядро: /vibework/*, /career/*, auth, admin
    ├── website/app/       legacy-адаптер: /api/* (чат, analyze, jobs…)
    ├── miniapp/frontend/  основной UI → GET /miniapp/
    └── website/frontend/  статика /static/* + старый лендинг → GET /
```

| URL | Что отдаётся |
|-----|----------------|
| `/miniapp/` | **Основной продукт** — `miniapp/frontend/index.html`, API `/vibework/...` |
| `/` | **Старый веб-клиент** — `website/frontend/index.html` + `script.js` |
| `/static/...` | CSS/JS из `website/frontend/` (нужны и Mini App) |
| `/register`, `/reset-password`, `/admin` | Отдельные страницы |
| `/docs` | OpenAPI |

Для Telegram Web App в BotFather указывайте **`https://<домен>/miniapp/`**, не корень `/`.

Конфигурация: **`.env` в корне репозитория** — полный список в [docs/ENV.md](docs/ENV.md).

## Быстрый старт

```bash
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r miniapp/requirements.txt
# создайте .env в корне (см. docs/ENV.md)
python miniapp/run.py
```

Проверка: `http://127.0.0.1:8000/miniapp/`, `http://127.0.0.1:8000/docs`, `GET /api/health/llm` (поля `llm_configured`, `ok`, `model`).

## Разработка

| Задача | Команда |
|--------|---------|
| API + UI | `python miniapp/run.py` |
| Бот (API уже запущен) | `python miniapp/bot/bot.py` |
| API + бот + website :8765 | `bash "launch files/launch-stack.sh"` или `launch files\launch-stack.bat` |
| Тесты | `./scripts/verify.sh` или `pytest tests/miniapp -q` |

Изолированный веб без Mini App — [website/README.md](website/README.md).

## LLM

OpenAI-совместимый `CHAT_API_URL` + `CHAT_API_KEY` + `CHAT_MODEL` в корневом `.env`. Промпты: `miniapp/backend/wibe_work/services/llm_prompts.py`. Логика вызова: `llm_client.py`.

## Продакшен

HTTPS, уникальный `JWT_SECRET`, CORS, `HH_USER_AGENT`. Nginx: [deploy/VPS-HTTPS.md](deploy/VPS-HTTPS.md).

## Документация

| Файл | О чём |
|------|--------|
| [miniapp/README.md](miniapp/README.md) | Каталог `miniapp/` |
| [miniapp/bot/README.md](miniapp/bot/README.md) | Telegram-бот |
| [website/README.md](website/README.md) | Legacy UI и изолированный сервер |
| [docs/ENV.md](docs/ENV.md) | Переменные окружения |
| [docs/LEARNING_INTEGRATIONS.md](docs/LEARNING_INTEGRATIONS.md) | Обучение, Rutube, VK |
| [SECURITY.md](SECURITY.md) | Уязвимости |

## Структура репозитория

```
VibeWork/
├── miniapp/
│   ├── run.py                 # вход :8000
│   ├── backend/wibe_work/     # FastAPI-пакет
│   ├── frontend/              # Mini App (HTML)
│   ├── data/                  # JSON, SQLite по умолчанию
│   └── bot/
├── website/
│   ├── app/                   # /api/*, мосты к wibe_work
│   └── frontend/              # /static, лендинг /
├── tests/miniapp|website/
├── scripts/                   # verify.sh, check_integrations.py
├── deploy/
└── docs/
```

Лицензия: [LICENSE](LICENSE) (MIT).
