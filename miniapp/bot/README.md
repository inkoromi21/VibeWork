# Telegram-бот VibeWork

Команда **`/start`**: первая кнопка — **сайт** (`WEBSITE_URL`), вторая — **мини-приложение** (`{PUBLIC_BASE_URL}/miniapp/`). Подписи можно задать в `.env`: `WEBSITE_BUTTON_LABEL`, `MINIAPP_BUTTON_LABEL`. Для Web App в Telegram нужен **HTTPS** и тот же API.

## Предварительные условия

1. **Запущенный backend с маршрутом `/miniapp/`** — приложение **`wibe_work.main`**: обычно **`python miniapp/run.py`** (порт **8000**). Изолированный **`python website/main.py`** без переменной **`VIBEWORK_FULL_STACK=1`** отдаёт только веб-клиент из `website/app` — **Mini App и API мини-приложения не работают** (в Telegram может открываться только «полный сайт» или 404). Альтернатива: `cd website`, установите зависимости из **`requirements-unified.txt`**, затем **`set VIBEWORK_FULL_STACK=1`** и **`python main.py`** (см. [website/README.md](../../website/README.md)).
2. В **[@BotFather](https://t.me/BotFather)** для **Menu Button / Web App** укажите URL с суффиксом **`/miniapp/`** (не корень **`/`**, иначе откроется полный сайт).
3. **Файл `.env` в корне репозитория** с минимум:
   - `TELEGRAM_BOT_TOKEN` — токен от [@BotFather](https://t.me/BotFather);
   - для Web App — **HTTPS**. Запустите стек с **`launch-stack.bat`**: при появлении URL туннеля в `.env` допишется **`TELEGRAM_PUBLIC_BASE_URL`**. Затем в чате с ботом выполните **`/start`** — вторая кнопка станет настоящим Web App (не ссылкой в браузер).

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

Полная инструкция по окружению: **[README в корне репозитория](../../README.md)**.

---

## Файлы

| Файл | Назначение |
|------|------------|
| `bot.py` | Точка входа, long polling |
