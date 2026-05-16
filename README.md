# VibeWork

Карьерная платформа для молодых специалистов: анкета, диагностика, разбор компетенций, ИИ-чат, подбор вакансий и ролевой симулятор. Доступны **веб-интерфейс**, **Telegram Mini App** и **REST API** на одном сервере FastAPI.

**Telegram-бот:** [@VibeWorks_bot](https://t.me/VibeWorks_bot)

---

## Содержание

- [Возможности](#возможности)
- [Архитектура репозитория](#архитектура-репозитория)
- [Требования](#требования)
- [Быстрый старт](#быстрый-старт)
- [Конфигурация](#конфигурация)
- [Запуск для разработки](#запуск-для-разработки)
- [Модели LLM (облако и совместимый API)](#модели-llm-облако-и-совместимый-api)
- [Проверка качества и тесты](#проверка-качества-и-тесты)
- [Отдельный веб-сервер (каталог website)](#отдельный-веб-сервер-каталог-website)
- [Эксплуатация в продакшене](#эксплуатация-в-продакшене)
- [Документация по подпроектам](#документация-по-подпроектам)
- [Лицензия и безопасность](#лицензия-и-безопасность)

---

## Возможности

| Область | Описание |
|--------|----------|
| Профиль | Динамическая анкета, сохранение в SQLite |
| Диагностика | Тесты и метрики для последующего разбора |
| Разбор и план | Аналитика и рекомендации на основе данных профиля |
| ИИ-чат | Облачные провайдеры (Groq, DeepSeek, OpenAI и др.) или локальный OpenAI-совместимый эндпоинт |
| Вакансии | Интеграция с API hh.ru; при недоступности — демо-данные и ссылки |
| Симулятор | Сценарий «день на работе» с ветвлением |
| Аутентификация | Вход по e-mail/паролю и сценарии для Telegram |

Интерактивная спецификация API: **`/docs`** (Swagger UI) и **`/openapi.json`**.

---

## Архитектура репозитория

Монорепозиторий: **бэкенд** (`wibe_work` + при необходимости пакет `website/app`), **статика** веб-UI и **мини-приложение** в `miniapp/frontend/`, **данные** — один файл **SQLite** (путь задаётся переменной окружения).

**Рекомендуемый режим:** один процесс **`python miniapp/run.py`** (порт **8000**). Он обслуживает корень сайта, мини-приложение и все API в едином контексте БД.

| URL (локально) | Назначение |
|----------------|------------|
| `http://127.0.0.1:8000/` | Веб-интерфейс — тот же UI, что в Telegram Mini App (`miniapp/frontend/index.html`) |
| `http://127.0.0.1:8000/miniapp/` | Тот же интерфейс (удобно как URL для бота) |
| `http://127.0.0.1:8000/docs` | OpenAPI (Swagger) |
| `http://127.0.0.1:8000/api/health` | Быстрая проверка: сервис отвечает |
| `http://127.0.0.1:8000/api/health/llm` | Конфигурация LLM (JSON: `llm_configured`, `model`) |

Интерфейс в браузере совпадает с мини-приложением; исходник — **`miniapp/frontend/`**. Каталог **`website/frontend/`** — прежняя статика (по-прежнему доступна как `/static/...`). Код веб-API в **`website/app/`** подключается к общему приложению через `sys.path` (см. `miniapp/run.py`).

---

## Требования

- **Python 3.10+** для основного стека (`miniapp/requirements.txt`). На **Python 3.14** (Windows) для изолированного пакета `website/` см. примечание в [website/README.md](website/README.md) — там обновлены версии **pydantic**, чтобы ставились готовые колёса без сборки Rust.
- Для **изолированного** запуска только пакета `website/` — отдельное окружение и `website/requirements.txt` (см. [website/README.md](website/README.md)).
- Для Mini App в Telegram с устройства — **HTTPS** (свой домен, обратный прокси или внешний туннель с HTTPS).

---

## Быстрый старт

### 1. Клонирование и виртуальное окружение

```bash
git clone <repository-url>
cd VibeWork
python3 -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate
pip install -r miniapp/requirements.txt
```

### 2. Переменные окружения

Из корня репозитория:

```bash
cp miniapp/.env.example .env   # Linux/macOS
# Windows (CMD):  copy miniapp\.env.example .env
```

Отредактируйте `.env`. Ключевые параметры:

| Переменная | Назначение |
|------------|------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от [@BotFather](https://t.me/BotFather) |
| `PUBLIC_BASE_URL` | Базовый URL API; локально `http://127.0.0.1:8000`; на проде **`https://ваш-домен`** (тот же хост, что открывает nginx → приложение) |
| `TELEGRAM_PUBLIC_BASE_URL` | HTTPS для кнопок Web App в Telegram; на проде тот же **`https://ваш-домен`**, что и `PUBLIC_BASE_URL` (задайте вручную в `.env`) |
| `WEBSITE_URL` | Кнопка «Сайт»: корень сайта (`/`). Пусто — берётся та же база, что и для миниаппа; не задавайте `/miniapp/` |
| `JWT_SECRET` | Секрет подписи JWT; в продакшене обязательно уникальное значение |
| `DATABASE_PATH` | Путь к файлу SQLite (необязательно; иначе используется путь по умолчанию в коде) |
| `HH_USER_AGENT` | Идентификатор клиента для API hh.ru в формате из их документации |
| `HH_CLIENT_ID` / `HH_CLIENT_SECRET` | После одобрения заявки на [dev.hh.ru](https://dev.hh.ru/admin) — OAuth `client_credentials` (см. `scripts/test_hh_api.py`, `GET /api/health/hh`) |
| `HH_APP_ACCESS_TOKEN` | Альтернатива паре id/secret — готовый access token из кабинета |

### 3. Запуск API

```bash
python miniapp/run.py
```

Откройте в браузере `http://127.0.0.1:8000/docs`.

---

## Конфигурация

Подробности по окружению для веб-пакета изолированно — в [website/README.md](website/README.md).  
Шаблон переменных мини-приложения — **`miniapp/.env.example`** (копируется в корневой `.env`).

---

## Запуск для разработки

| Задача | Команда |
|--------|---------|
| Только API и статика (порт 8000) | `python miniapp/run.py` |
| Полный стек | macOS/Linux: `bash "launch files/launch-stack.sh"` · Windows: `launch files\launch-stack.bat` — открывает отдельные окна: API **:8000**, Telegram-бот, веб **:8765** (`website/main.py`) |
| Только Telegram-бот (при уже запущенном API) | `python miniapp/bot/bot.py` |

Вспомогательные сценарии лежат в **`launch files/stack/`**. Документация по боту: [miniapp/bot/README.md](miniapp/bot/README.md).

---

## Модели LLM (облако и совместимый API)

Чат использует эндпоинт **`/v1/chat/completions`** (формат OpenAI). Задайте в `.env` **`CHAT_API_URL`**, **`CHAT_API_KEY`** (при необходимости) и **`CHAT_MODEL`** — например Groq, DeepSeek или OpenAI. Для URL с `127.0.0.1` / `localhost` ключ не обязателен, если так настроен ваш локальный сервер.

Диагностика: `GET http://127.0.0.1:8000/api/health/llm` — поля `llm_configured`, `model`.

При долгом ответе локального URL увеличьте `LLM_LOCAL_TIMEOUT` (по умолчанию выше для localhost).

Детали переменных окружения — в **`miniapp/backend/wibe_work/services/llm_client.py`**.

Системные промпты (чат, разбор, заголовки сессий) собраны в одном месте: **`miniapp/backend/wibe_work/services/llm_prompts.py`** — правки формулировок ИИ удобно делать там.

---

## Проверка качества и тесты

Единый скрипт верификации (изоляция зависимостей в временных venv):

```bash
./scripts/verify.sh
```

Он устанавливает зависимости мини-приложения и сайта, выполняет `compileall` и pytest:

- `tests/miniapp` — смоук-тесты бэкенда мини-приложения  
- `tests/website` — смоук-тесты изолированного пакета `website/app`

Вручную:

```bash
pip install -r miniapp/requirements.txt "pytest>=8,<9"
pytest tests/miniapp -q
```

Для пакета сайта — отдельное окружение и `pip install -r website/requirements.txt`, затем `pytest tests/website -q`.

Политика уязвимостей и контакты: **[SECURITY.md](SECURITY.md)**.

---

## Отдельный веб-сервер (каталог website)

Для отладки только веб-пакета без общего `miniapp` можно запустить **`python main.py`** из каталога **`website/`** (порт по умолчанию **8765**). База и сессии в этом режиме отделены от unified-стека — см. [website/README.md](website/README.md).

В повседневной разработке обычно достаточно **`miniapp/run.py`** на порту **8000**.

---

## Эксплуатация в продакшене

- Надёжный **`JWT_SECRET`**, файл **`.env`** не попадает в систему контроля версий.
- Транспорт **HTTPS** — готовый пример nginx и certbot: **[deploy/VPS-HTTPS.md](deploy/VPS-HTTPS.md)** (скрипт `deploy/setup-https.sh`, конфиг `deploy/nginx/vibework.conf`).
- Ограничьте **CORS** доверенными источниками.
- Задайте корректный **`HH_USER_AGENT`** для соответствия требованиям hh.ru.

---

## Документация по подпроектам

| Документ | Содержание |
|----------|------------|
| [miniapp/README.md](miniapp/README.md) | Структура мини-приложения, фронт, `wibe_work`, данные |
| [miniapp/bot/README.md](miniapp/bot/README.md) | Telegram-бот и Web App |
| [website/README.md](website/README.md) | Изолированный веб-сервер, переменные, API |

---

## Структура каталогов (обзор)

```
VibeWork/
├── README.md
├── LICENSE
├── SECURITY.md
├── scripts/
│   └── verify.sh          # локальная верификация (venv + pytest)
├── launch files/          # сценарии запуска стека
├── tests/
│   ├── miniapp/
│   └── website/
├── miniapp/
│   ├── run.py             # точка входа API :8000
│   ├── terminal_theme.py # цветной вывод в терминал (run.py, bot.py)
│   ├── requirements.txt
│   ├── backend/wibe_work/ # основной пакет FastAPI
│   │   └── services/
│   │       ├── llm_client.py   # вызовы chat/completions
│   │       └── llm_prompts.py  # системные промпты ИИ
│   ├── frontend/          # Mini App
│   ├── bot/
│   ├── data/
│   └── scripts/
└── website/
    ├── main.py            # опционально :8765
    ├── app/
    └── frontend/
```

---

## Лицензия и безопасность

- Лицензия: **[LICENSE](LICENSE)** (MIT).
- Сообщения об уязвимостях: см. **[SECURITY.md](SECURITY.md)**.
