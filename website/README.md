# Веб-клиент и пакет `website`

В этом каталоге находятся **статический фронтенд** VibeWork (`frontend/`) и **изолированное FastAPI-приложение** (`app/`), которое можно запускать отдельно от основного стека.

## Два режима работы

### 1. Рекомендуемый: единый сервер (`miniapp/run.py`)

В повседневной разработке статика из **`website/frontend/`** раздаётся процессом **`python miniapp/run.py`** (порт **8000**). Запросы к **`/api/...`** обрабатываются тем же приложением, что и API мини-приложения; используется **единая SQLite** мини-приложения. Регистрация и профиль совместимы с сценарием Telegram Mini App.

**Точка входа:** корень репозитория → см. [README в корне](../README.md).

### 2. Изолированный сервер (`website/main.py`)

Отдельный процесс на порту **8765** (по умолчанию) — для отладки только веб-пакета без поднятия полного `miniapp`. В этом режиме **нет URL `/miniapp/`** и API `/vibework/...` — для Telegram Mini App это выглядит как «открывается только сайт».

**Полный стек из каталога `website/`** (как `miniapp/run.py`: корень `/`, мини-приложение `/miniapp/`, общая БД):

```bash
cd website
pip install -r requirements.txt -r requirements-unified.txt
set VIBEWORK_FULL_STACK=1          # Windows CMD
set PORT=8000                      # по желанию; иначе 8765
python main.py
```

В `.env` для бота задайте **`PUBLIC_BASE_URL=http://127.0.0.1:8000`** (или ваш порт), **`WEBSITE_URL`** на тот же хост. В [@BotFather](https://t.me/BotFather) у Web App / меню бота URL должен оканчиваться на **`/miniapp/`**, а не на `/`.

Изолированный режим (по умолчанию без переменной) — своя БД и механизм сессий (см. код в `app/`).

```bash
cd website
python3 -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # при необходимости
python main.py
```

**Python 3.14 на Windows:** в `requirements.txt` заданы `pydantic>=2.11` и совместимый `pydantic-core`, чтобы ставились **готовые колёса** и не требовалась сборка Rust. Если установка всё же падает, используйте **Python 3.12 или 3.11**.

Браузер: **http://127.0.0.1:8765**

На Windows порт **8000** иногда занят системой; для изолированного сервера по умолчанию выбран **8765**. Свой порт:

```bash
# Windows CMD
set PORT=9000
python main.py
```

Через uvicorn напрямую:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

---

## Переменные окружения

При работе **только** из каталога `website/` ключи для LLM и интеграций задаются в **`website/.env`**.

При работе через **`miniapp/run.py`** используйте **корневой `.env`** репозитория — там же задаются `HH_USER_AGENT`, параметры LLM и прочее (см. корневой README).

Пример переменных для облачного чата (изолированный режим):

| Переменная | Назначение |
|------------|------------|
| `DEEPSEEK_API_KEY` | Ключ API; без ключа возможны заглушки без внешних запросов |
| `DEEPSEEK_API_URL` | По умолчанию `https://api.deepseek.com/v1/chat/completions` |
| `DEEPSEEK_MODEL` | По умолчанию `deepseek-chat` |

Для запросов к **hh.ru** в продакшене задайте **`HH_USER_AGENT`** в формате из официальной документации API.

---

## API пакета `app`

Эндпоинты соответствуют потребностям фронтенда. При unified-запуске через порт **8000** они доступны там же.

Примеры областей (полный список — в **`/docs`** у запущенного процесса):

- разбор и аналитика (`/api/analyze` и связанные маршруты);
- вакансии и матчинг (`/api/jobs`, `/api/jobs/match`);
- симулятор (`/api/simulator/start`, `/api/simulator/step`);
- каталог МТС-треков (`/api/mts/tracks`, `/api/mts/preview`);
- здоровье: `GET /api/health`, `GET /api/health/llm`.

При **`miniapp/run.py` на порту 8000** те же префиксы `/api/...` обслуживаются общим приложением вместе с API мини-приложения (один OpenAPI в `/docs`).

---

## Учётные записи и данные

| Режим | Хранилище |
|-------|-----------|
| **`miniapp/run.py`** | SQLite мини-приложения; см. `DATABASE_PATH` в корневом `.env` |
| **`python main.py` в `website/`** | Отдельный файл, по умолчанию **`website/data/vibework.db`**, cookie-сессии, маршруты регистрации в `app/` |

Без авторизации фронтенд может использовать черновик профиля в **localStorage** браузера.

---

## Структура

| Компонент | Описание |
|-----------|----------|
| `app/main.py` | FastAPI: CORS, монтирование статики `frontend/` |
| `app/career_advisor.py` | Логика разбора, чата, матчинга |
| `app/hh_client.py` | Клиент API hh.ru |
| `app/sqlite_async_session.py`, `orm_models.py`, `account_auth_routes.py` | Сессии и пользователи для **изолированного** запуска сайта |
| `frontend/` | HTML/CSS/JS веб-интерфейса |
