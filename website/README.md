# CareerCompass — карьерный консультант (16–22)

Веб-приложение: диагностика интересов и навыков, тест склонностей, персональный план развития, демо-подбор вакансий.

В монорепозитории **wibe-work** эта папка — отдельный продукт рядом с `miniapp/`; у сайта своё виртуальное окружение и зависимости.

## Быстрый запуск

Из **корня** монорепозитория:

```bash
"./launch files/launch-website.sh"
```

Windows: `launch files\launch-website.bat`

Перед первым запуском создайте окружение (см. ниже).

## Требования

- Python 3.10+

## Установка

```bash
cd website
python3 -m venv .venv
```

Активируйте виртуальное окружение (Windows PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

## Переменные окружения (опционально)

Создайте файл `.env` в корне проекта или экспортируйте переменные:

| Переменная | Описание |
|------------|----------|
| `DEEPSEEK_API_KEY` | Ключ API Deepseek. Если пусто — используется текст-заглушка без внешних запросов. |
| `DEEPSEEK_API_URL` | По умолчанию `https://api.deepseek.com/v1/chat/completions` |
| `DEEPSEEK_MODEL` | По умолчанию `deepseek-chat` |

## Запуск

Из корня проекта:

```bash
python main.py
```

Откройте в браузере: [http://127.0.0.1:8765](http://127.0.0.1:8765)

По умолчанию используется порт **8765** (на Windows порт 8000 иногда недоступен — ошибка WinError 10013). Свой порт: `set PORT=9000` и снова `python main.py`.

Альтернатива:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

## API

- `POST /api/analyze` — диагностика + опционально `question_timings` (мс на вопрос) для поведенческой подсказки; ответ: сценарии A/B/C, gap-analysis, недельный спринт, планы.
- `GET /api/jobs` — те же фильтры + `interest` (код из профиля, по умолчанию `IT`). Данные с [hh.ru API](https://api.hh.ru/openapi/redoc); при сбое — демо-список. В `.env` задайте `HH_USER_AGENT` в формате из документации hh.ru.
- `POST /api/jobs/match` — тело `{ interests, skills, …фильтры }` — вакансии с матч-%; источник тот же (hh.ru или демо).
- `GET /api/simulator/start?role=analyst|designer` и `POST /api/simulator/step` — текстовый симулятор дня.
- `GET /api/mts/tracks` — полный список **13 ролей** (`app/mts_matrix.json`).
- `POST /api/mts/preview` — тело `{ interests, skills, test_answers? }` (тест только если **все 5** ответов); ранжирование матрицы под профиль и тест. В отчёте `/api/analyze` то же приходит в поле `mts_matrix`.
- `GET /api/health` — проверка живости сервиса.

## Аккаунты и база

- SQLite-файл: `data/vibework.db` (создаётся при первом запуске).
- В шапке: **Регистрация** / **Войти** (email + пароль от 8 символов). Cookie-сессия ~30 дней.
- API: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `PUT /api/auth/snapshot` (снимок профиля, теста, разбора, чата).
- Без входа по-прежнему работает сохранение в `localStorage` в браузере.
- **Забыли пароль:** сброса по email в приложении нет — зарегистрируйте новый аккаунт на другой почте или удалите пользователя из `data/vibework.db` (для локальной разработки).

## Структура

- `app/main.py` — FastAPI, CORS, раздача `frontend/`.
- `app/api_schemas.py` — Pydantic-модели и валидация.
- `app/questionnaire_fields.py` — поля анкеты (структура как в Google Sheet).
- `app/career_advisor.py` — правила рекомендаций и LLM (при настройке).
- `app/aptitude_quiz_content.py` — вопросы тестов по сферам и личности.
- `app/mts_tracks_catalog.py` — каталог треков МТС (роли).
- `app/hh_client.py` — поиск вакансий через API hh.ru.
- `app/sqlite_async_session.py`, `app/orm_models.py`, `app/account_auth_routes.py` — SQLite и вход пользователя.
- `frontend/` — интерфейс; результаты анализа сохраняются в `localStorage`.
