# Telegram-бот

Long polling. Кнопки `/start`:

- **Сайт** — `WEBSITE_URL` (обычно корень `/`, старый лендинг).
- **Mini App** — `{PUBLIC_BASE_URL}/miniapp/` (основной интерфейс).

В [@BotFather](https://t.me/BotFather) для Menu Button / Web App URL должен быть **`…/miniapp/`**.

## Требования

1. Запущен **`python miniapp/run.py`** (порт 8000) — маршрут `/miniapp/` и API.
2. **`.env` в корне:** `TELEGRAM_BOT_TOKEN`; для Web App с телефона — `TELEGRAM_PUBLIC_BASE_URL` (HTTPS).

Изолированный `website/main.py` **без** `VIBEWORK_FULL_STACK=1` не отдаёт Mini App — см. [website/README.md](../../website/README.md).

## Запуск

```bash
# из корня, API уже работает
python miniapp/bot/bot.py
```

Со стеком: `bash "launch files/launch-stack.sh"` или `launch files\launch-stack.bat`.

Конфигурация: [README в корне](../../README.md), [docs/ENV.md](../../docs/ENV.md).
