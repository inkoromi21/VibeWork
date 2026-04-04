# Wibe work

Монорепозиторий из двух продуктов:

1. **`miniapp/`** — карьерный помощник для **Telegram Mini App**: API, бот, фронт, **`miniapp/data/`** (SQLite, JSON), **`miniapp/requirements.txt`**, точка входа API — **`miniapp/run.py`**.
2. **`website/`** — отдельный сайт (**CareerCompass**): **`website/app/`**, **`website/frontend/`**, **`website/data/`** (своя БД), **`website/requirements.txt`**.

Корень репозитория — общий **`venv`** и файл **`.env`** для миниаппы. Сайт живёт в **`website/`** со своим **`.venv`**.

### Запуск из корня (коротко)

| Действие | macOS / Linux | Windows |
|----------|----------------|---------|
| **Весь стек** (API :8000, ngrok, бот, сайт :8765) | `bash "launch files/launch-stack.sh"` | `launch files\launch-stack.bat` |
| Только API (ручной отладочный запуск) | `python miniapp/run.py` | то же |

Отдельные окна поднимает только **`launch files/launch-stack`**. Вспомогательные сценарии лежат в **`launch files/stack/`** и не предназначены для ручного запуска.

Подробности: [miniapp/README.md](miniapp/README.md), [miniapp/bot/README.md](miniapp/bot/README.md), [website/README.md](website/README.md).

## Разработка и CI

- **Локально (как на GitHub Actions):** из корня выполните `./scripts/verify.sh` — во временных venv ставятся зависимости миниаппы и сайта по отдельности, прогоняются `compileall` и дымовые тесты.
- **Вручную:** в активированном venv миниаппы — `pip install -r miniapp/requirements.txt "pytest>=8,<9"`, затем `pytest tests/miniapp -q`. Для сайта — отдельный venv в `website/`, `pip install -r website/requirements.txt "pytest>=8,<9"`, `pytest tests/website -q`.
- После пуша в GitHub срабатывает workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Обновления зависимостей предлагает [Dependabot](.github/dependabot.yml).
- Сообщения об уязвимостях: [SECURITY.md](SECURITY.md).

## Возможности

- Профиль, опросы, интеграция с **HeadHunter** (API `api.hh.ru`)
- Авторизация по email и через Telegram
- Мини-приложение: `GET /miniapp/`
- Интерактивная документация API: `/docs` (Swagger)

## Требования

- **Python 3.10+**
- Для Telegram Mini App с телефона — публичный HTTPS URL (часто используют [ngrok](https://ngrok.com/) или свой домен)

## Быстрый старт

### 1. Клонирование и окружение

```bash
cd wibe-work
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate.bat
pip install -r miniapp/requirements.txt
```

### 2. Переменные окружения

Скопируйте шаблон в **корень** репозитория и заполните секреты:

```bash
cp miniapp/.env.example .env
```

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от [@BotFather](https://t.me/BotFather) |
| `PUBLIC_BASE_URL` | Базовый URL API (локально: `http://127.0.0.1:8000`; с туннелем — URL ngrok) |
| `JWT_SECRET` | Секрет для подписи JWT (**обязательно смените в продакшене**) |
| `DATABASE_PATH` | Необязательно: полный путь к файлу SQLite (по умолчанию `miniapp/data/career.db`) |
| `HH_USER_AGENT` | User-Agent для запросов к HH (по умолчанию задан в коде) |
| `HH_FINALIZE_MIN_COMPLETENESS` | Порог «завершённости» профиля для HH (по умолчанию `0.55`) |
| `HH_MIN_POLL_ANSWERS` | Минимум ответов опроса (по умолчанию `0`) |
| `JWT_EXPIRE_DAYS` | Срок жизни JWT в днях (по умолчанию `30`) |

### Локальная нейросеть: Ollama

Чат и блок «Краткий вывод» в разборе ходят в **OpenAI-совместимый** эндпоинт `/v1/chat/completions`. [Ollama](https://ollama.com) поднимает такой API на вашей машине **без облачного ключа**.

1. **Установите Ollama** с сайта [ollama.com](https://ollama.com) и убедитесь, что демон запущен (в трее на macOS / как сервис на Linux; на Windows — после установки из меню Пуск).

2. **Скачайте модель** (имя должно совпасть с `OLLAMA_MODEL`):

   ```bash
   ollama pull llama3.2
   ```

   Для более устойчивого русского языка можно взять, например, `qwen2.5:7b` или `mistral` — тогда в `.env` укажите то же имя.

3. **Проверьте, что Ollama отвечает:**

   ```bash
   curl -s http://127.0.0.1:11434/api/tags
   ```

4. **В корне проекта в файле `.env` добавьте:**

   ```env
   USE_OLLAMA=1
   OLLAMA_HOST=http://127.0.0.1:11434
   OLLAMA_MODEL=llama3.2
   ```

   Если Ollama на другой машине в сети — подставьте её хост в `OLLAMA_HOST` (должен быть доступен с компьютера, где крутится `python miniapp/run.py`).

5. **Перезапустите API** (`python miniapp/run.py`). Проверка:

   - [http://127.0.0.1:8000/api/health/llm](http://127.0.0.1:8000/api/health/llm) — должно быть `"llm_configured": true`, `"ollama_mode": true`, в `model` — выбранная модель.

6. **Если ответы долго не приходят** (первая генерация грузит модель в RAM), увеличьте таймаут:

   ```env
   LLM_LOCAL_TIMEOUT=180
   ```

**Без `USE_OLLAMA=1`** можно вручную задать только URL (ключ не нужен):

```env
CHAT_API_URL=http://127.0.0.1:11434/v1/chat/completions
CHAT_MODEL=llama3.2
```

### 3. Запуск API

Из корня репозитория:

```bash
python miniapp/run.py
```

Сервер слушает `0.0.0.0:8000`. Проверка: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 4. Telegram-бот и ngrok

Используйте **`bash "launch files/launch-stack.sh"`** (или **`launch files\launch-stack.bat`**): откроются окна API, ngrok, бота и сайта. Для ручной отладки бота из активированного `venv`: `python miniapp/bot/bot.py` (предварительно запустите API).

Бот по `/start` открывает мини-приложение по `{PUBLIC_BASE_URL}/miniapp/`. При запущенном ngrok URL кнопки берётся из `http://127.0.0.1:4040/api/tunnels`.

- **Ollama** (если в `.env`): скрипт стека вызывает `miniapp/scripts/ensure-ollama.sh` / `miniapp\scripts\windows\ensure-ollama.bat`.

## Запуск сайта (`website/`)

Через полный стек — см. выше. Вручную для разработки:

```bash
cd website
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # при необходимости (файл в каталоге website/)
python main.py
```

Браузер: [http://127.0.0.1:8765](http://127.0.0.1:8765) — подробности в [website/README.md](website/README.md).

## Структура проекта

```
wibe-work/
├── tests/                      # дымовые тесты (miniapp / website отдельно)
├── scripts/verify.sh           # локальная проверка как в CI
├── .github/workflows/ci.yml    # GitHub Actions
├── launch files/
│   ├── launch-stack.sh / .bat  # единственная точка входа: весь стек
│   └── stack/                  # внутренние шаги (ngrok, бот, сайт) — не вызывать вручную
├── miniapp/
│   ├── README.md
│   ├── run.py                  # запуск API миниаппы
│   ├── requirements.txt        # зависимости API и бота
│   ├── .env.example            # шаблон переменных (копировать в корень .env)
│   ├── backend/wibe_work/      # пакет FastAPI
│   ├── frontend/               # статика мини-приложения
│   ├── data/                   # SQLite и JSON миниаппы
│   ├── bot/
│   │   ├── README.md
│   │   └── bot.py
│   └── scripts/                # ensure-ollama, extract-frontend-rar, windows/
└── website/
    ├── README.md
    ├── main.py
    ├── requirements.txt
    ├── app/                    # FastAPI (CareerCompass)
    ├── frontend/
    └── data/                   # SQLite сайта (vibework.db)
```

## Полезные URL (локально)

| URL | Назначение |
|-----|------------|
| http://127.0.0.1:8000/miniapp/ | Мини-приложение |
| http://127.0.0.1:8000/docs | Swagger |
| http://127.0.0.1:8000/openapi.json | OpenAPI-схема |
| http://127.0.0.1:8000/api/health/llm | Настроен ли LLM (в т.ч. Ollama) |

## Продакшен

- Задайте надёжный `JWT_SECRET` и не коммитьте `.env`.
- Раздавайте приложение за reverse proxy (nginx, Caddy) с HTTPS.
- Ограничьте CORS под ваши домены (сейчас в коде разрешены все источники — удобно для разработки, для прода это нужно сузить).

## Лицензия

См. файл [LICENSE](LICENSE) (MIT). При необходимости замените год и формулировку правообладателя.
