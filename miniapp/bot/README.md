# Telegram-бот

Polling-бот для кнопки **Web App**: открывает мини-приложение VibeWork по URL `{PUBLIC_BASE_URL}/miniapp/`.

## Требования

- Запущенный **API** из корня репозитория (`python miniapp/run.py`, порт **8000**), если поднимаете бота отдельно.
- В корне репозитория файл **`.env`** с `TELEGRAM_BOT_TOKEN` (и при необходимости `PUBLIC_BASE_URL`).

Пакет `wibe_work` подхватывается из `miniapp/backend/` через `sys.path`.

## Запуск

Обычно бот поднимается вместе со всем стеком из корня репозитория:

```bash
bash "launch files/launch-stack.sh"
```

Windows: `launch files\launch-stack.bat`

Для отладки вручную (из корня, активированный `venv`):

```bash
python miniapp/bot/bot.py
```

## Файлы

- `bot.py` — точка входа. Полный запуск — только через **`launch files/launch-stack`**.
