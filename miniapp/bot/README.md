# Telegram-бот

Polling-бот для кнопки **Web App**: открывает мини-приложение VibeWork по URL `{PUBLIC_BASE_URL}/miniapp/`.

## Требования

- Запущенный **API** из корня репозитория (`python miniapp/run.py`, порт **8000**).
- В корне репозитория файл **`.env`** с `TELEGRAM_BOT_TOKEN` (и при необходимости `PUBLIC_BASE_URL`).

Пакет `wibe_work` подхватывается из `miniapp/backend/` через `sys.path`.

## Запуск

### Вариант 1 — из корня монорепозитория (рекомендуется)

```bash
"./launch files/launch-bot.sh"
```

Windows:

```bat
launch files\launch-bot.bat
```

### Вариант 2 — вручную

Из корня репозитория, с активированным `venv`:

```bash
python miniapp/bot/bot.py
```

## Файлы

- `bot.py` — точка входа. Скрипты запуска — в **`launch files/`** в корне репозитория (`launch-bot.sh` / `.bat`).
