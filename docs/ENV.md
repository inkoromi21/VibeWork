# Переменные окружения

Единственный файл с секретами: **`.env` в корне репозитория** (на VPS: `/opt/vibework/.env`). В git не попадает.

После правок перезапустите API. Проверка: `python scripts/check_integrations.py`, `GET /api/health/hh`, `GET /vibework/learning/status`.

| Переменная | Назначение |
|------------|------------|
| `TELEGRAM_BOT_TOKEN` | Бот [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_BOT_USERNAME` | Имя бота без `@` (виджет входа) |
| `PUBLIC_BASE_URL` | Базовый URL сайта/API |
| `TELEGRAM_PUBLIC_BASE_URL` | HTTPS для Web App в Telegram |
| `WEBSITE_URL` | Кнопка «Сайт» (пусто = тот же хост) |
| `JWT_SECRET` | Подпись JWT |
| `ADMIN_LOGIN` | Логин входа в админ-панель (`/admin`) |
| `ADMIN_PASSWORD` | Пароль администратора (только в `.env`, не в git) |
| `ADMIN_SESSION_HOURS` | Длительность сессии админа в часах (по умолчанию 12) |
| `HH_USER_AGENT` | Клиент hh.ru с email из заявки |
| `HH_CLIENT_ID` / `HH_CLIENT_SECRET` | OAuth приложения hh.ru |
| `HH_APP_ACCESS_TOKEN` | Альтернатива id+secret |
| `CHAT_API_KEY` / `CHAT_API_URL` / `CHAT_MODEL` | ИИ-чат. Groq: `gsk_…` + `https://api.groq.com/openai/v1/chat/completions`. DeepSeek: `sk-…` + `https://api.deepseek.com/v1/chat/completions` |
| `EMAIL_FROM` / `RESEND_*` | Сброс пароля (Resend) |
| `UNISENDER_*` / `EMAIL_SMTP_*` | Другие провайдеры почты |
| `VK_ACCESS_TOKEN` | VK Video в путях обучения |
| `VK_API_VERSION` | Версия VK API (по умолчанию 5.199) |
| `VK_VIDEO_OWNER_IDS` | Сообщества для `video.get` (id со знаком `-`) |
| `GITHUB_TOKEN` | Поиск репозиториев в обучении |
| `ESCO_API_ENABLED` | ESCO API (1/0) |
| `ONET_USERNAME` / `ONET_PASSWORD` | O*NET (опционально) |
