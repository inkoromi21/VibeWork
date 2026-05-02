# Telegram-бот VibeWork

Бот открывает **Telegram Mini App** по адресу **`{PUBLIC_BASE_URL}/miniapp/`** (кнопка Web App). Для работы должен быть доступен HTTP(S) API того же проекта.

## Предварительные условия

1. **Запущенный backend** — как правило **`python miniapp/run.py`** из корня репозитория (порт **8000**), если бот не поднимается единым скриптом стека.
2. **Файл `.env` в корне репозитория** с минимум:
   - `TELEGRAM_BOT_TOKEN` — токен от [@BotFather](https://t.me/BotFather);
   - `PUBLIC_BASE_URL` — публичный базовый URL API (для Telegram на устройстве — **HTTPS**, например через ngrok).

Пакет **`wibe_work`** подключается из `miniapp/backend/` через изменение `sys.path` в **`bot.py`**.

---

## Запуск

В консоли при старте выводятся помеченные строки: **▶ Запуск** → при успехе **✓ Бот запущен** с URL и маской токена; при ошибке — **✗** и подсказка (см. `miniapp/terminal_theme.py`).

**Вместе со стеком** (API, при необходимости туннель и бот):

- Linux/macOS: `bash "launch files/launch-stack.sh"`
- Windows: `launch files\launch-stack.bat`

**Только бот** (при уже работающем API), из корня с активированным `venv`:

```bash
python miniapp/bot/bot.py
```

Полная инструкция по окружению и ngrok: **[README в корне репозитория](../../README.md)**.

---

## Файлы

| Файл | Назначение |
|------|------------|
| `bot.py` | Точка входа, long polling |
