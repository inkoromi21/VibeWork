# Переменные окружения

Файл с секретами: **`.env` в корне репозитория`** (на VPS: `/opt/vibework/.env`). В git не коммитится. Шаблон: [.env.example](../.env.example).

После правок перезапустите API. Проверка: `python scripts/check_integrations.py`, `GET /api/health/hh`, `GET /vibework/learning/status`, `GET /api/health/llm`.

## Telegram и URL

- **`TELEGRAM_BOT_TOKEN`** — токен от [@BotFather](https://t.me/BotFather)
- **`TELEGRAM_BOT_USERNAME`** — имя бота без `@` (виджет входа)
- **`PUBLIC_BASE_URL`** — базовый URL сайта/API (локально `http://127.0.0.1:8000`)
- **`TELEGRAM_PUBLIC_BASE_URL`** — HTTPS для Web App в Telegram
- **`WEBSITE_URL`** — кнопка «Сайт» в боте (пусто = тот же хост, корень `/`)

## Безопасность и аккаунты

- **`JWT_SECRET`** — подпись JWT (в проде — уникальное значение)
- **`JWT_INVALID_BEFORE`** — ISO UTC: старые токены недействительны (после `scripts/reset_all_users.py`)
- **`VIBEWORK_ENV`** — `dev` или `prod` (в prod строже проверки при старте)
- **`ENABLE_LEGACY_WEBSITE_MIGRATION`** — `1`: подтянуть пользователей из `website/data/vibework.db` при входе (по умолчанию выкл.)
- **`ADMIN_LOGIN`**, **`ADMIN_PASSWORD`** — вход в `/admin`
- **`ADMIN_SESSION_HOURS`** — длительность сессии админа (по умолчанию 12)
- **`DATABASE_PATH`** — путь к SQLite (в Docker задаётся в `docker-compose.yml`)

## hh.ru

- **`HH_USER_AGENT`** — User-Agent с email из заявки на dev.hh.ru
- **`HH_CLIENT_ID`**, **`HH_CLIENT_SECRET`** — OAuth приложения
- **`HH_APP_ACCESS_TOKEN`** — альтернатива паре id/secret

## LLM (чат и разбор)

- **`USE_OLLAMA`** — `1` для локального Ollama; при `CHAT_API_URL` на `127.0.0.1` локальный режим включается и при `USE_OLLAMA=0`
- **`CHAT_PROVIDER`** — `ollama` / `groq` / `deepseek` / `zai`, если `CHAT_API_URL` пустой
- **`OLLAMA_API_KEY`** — то же, что `CHAT_API_KEY`, для Ollama Cloud
- **`CHAT_API_KEY`**, **`CHAT_API_URL`**, **`CHAT_MODEL`** — OpenAI-совместимый API. Проверка: `GET /api/health/llm` (поле **`ok`**). Пример Ollama Cloud: `https://ollama.com/v1/chat/completions`, модель `gpt-oss:120b-cloud`

## Почта

- **`EMAIL_FROM`**, **`RESEND_API_KEY`**, **`RESEND_BASE_URL`** — сброс пароля (Resend)
- **`UNISENDER_*`**, **`EMAIL_SMTP_*`** — альтернативные провайдеры

## Обучение (опционально)

- **`VK_ACCESS_TOKEN`** — VK Video в путях обучения
- **`VK_API_VERSION`** — версия VK API (по умолчанию 5.199)
- **`VK_VIDEO_OWNER_IDS`** — сообщества для `video.get` (id со знаком `-`)
- **`GITHUB_TOKEN`** — поиск репозиториев в обучении
- **`ESCO_API_ENABLED`** — ESCO API (`1` / `0`)
- **`ONET_USERNAME`**, **`ONET_PASSWORD`** — O*NET (опционально)

Подробнее по интеграциям обучения: [LEARNING_INTEGRATIONS.md](LEARNING_INTEGRATIONS.md).
