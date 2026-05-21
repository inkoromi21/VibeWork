# VibeWork

Карьерная платформа: анкета, тест, ИИ-разбор, чат, вакансии (hh.ru), симулятор. Один сервер FastAPI — веб, Mini App в Telegram, REST API.

**Бот:** [@VibeWorks_bot](https://t.me/VibeWorks_bot)

## Именование

- **VibeWork** — продукт в UI и текстах
- **`wibe_work`** — Python-пакет (`miniapp/backend/wibe_work/`)
- **`vibework`** — БД, cookie, пути на VPS (нижний регистр)
- **@VibeWorks_bot** — Telegram-бот (имя с «s»)

## Архитектура

**Режим по умолчанию:** `python miniapp/run.py` → `wibe_work.main`, порт **8000**, SQLite (`DATABASE_PATH` в `.env` или `miniapp/data/`).

```
miniapp/run.py
    ├── wibe_work/          ядро: /vibework/*, /career/*, auth, admin
    ├── website/app/       legacy-адаптер: /api/* (чат, analyze, jobs…)
    ├── miniapp/frontend/  основной UI → GET /miniapp/
    └── website/frontend/  статика /static/* + старый лендинг → GET /
```

**Маршруты (локально :8000):**

- **`/miniapp/`** — основной продукт (`miniapp/frontend/index.html`, API `/vibework/...`)
- **`/`** — старый веб-клиент (`website/frontend/index.html`, `script.js`)
- **`/static/...`** — CSS/JS из `website/frontend/` (нужны Mini App)
- **`/register`**, **`/reset-password`**, **`/admin`** — отдельные страницы
- **`/docs`** — OpenAPI

В BotFather для Web App укажите **`https://<домен>/miniapp/`**, не корень `/`.

Конфигурация: **`.env` в корне`** — шаблон [.env.example](.env.example), описание [docs/ENV.md](docs/ENV.md).

## Профориентационные методики

В анкете и разделе «Тест» используются **адаптированные** опросники (собственные формулировки и логика подсчёта в `miniapp/backend/wibe_work/services/assessment_modules.py`, `assessment_routing.py`). Бланки из PDF в продукт не копируются. Набор блоков зависит от образования и класса/курса (школа 8–9, 9 класс, 10–11, СПО, вуз).

| Модуль в продукте | Методика | Назначение |
|-------------------|----------|------------|
| `profil` | Профиль (интересы к учёбе) | Склонности к предметам и занятиям |
| `klimov` | Дифференциально-диагностический опросник (ДДО), Е. А. Климов | Предпочтение видов деятельности |
| `jovaisa` | Методика Йовайши | Мотивы и ценности в выборе |
| `holland` | Типология Голланда (упрощённо) | Тип рабочей среды и задач |
| `readiness` | Готовность к профориентационному выбору | Уверенность в решении, план на месяц (школьные треки) |

Дополнительно в общем блоке теста — вопросы эксперта (трио, интерес/работа, резюме и др.) в `aptitude_quiz.py`; часть формулировок опирается на идеи типов среды Голланда и карьерных ценностей, без выдачи пользователю академических терминов в интерфейсе.

**Источники и ориентиры (открытые материалы):**

- **Климов (ДДО):** [Дифференциально-диагностический опросник, Е. А. Климов (PDF)](https://sh6-uzhur-r04.gosweb.gosuslugi.ru/netcat_files/167/2910/Differentsial_no_diagnosticheskiy_oprosnik_DDO_E.A.KLIMOV_.pdf)
- **Йовайша:** [Тест Йовайши (PDF)](https://hordsh52.kmr.muzkult.ru/media/2022/02/21/1293474713/Test_Jovajshi.pdf)
- **Голланд:** [Тест Голланда — определение профессионального типа личности (PDF)](https://cdk-detstvo.centerstart.ru/sites/cdk-detstvo.centerstart.ru/files/2022-12/test_hollanda_opredelenie_professionalnogo_tipa_lichnosti.pdf)
- **Профиль (интересы к учёбе):** [Профессиональный профиль (PDF)](http://www.koin-nkz.ru/media/uploads/material_files/левое_меню/профессиональная_ориентация/6._prof_profil.pdf)
- **Профориентация (готовность к выбору):** [Тест по профориентации (PDF)](https://upravlenieobrazovania.rh.eduru.ru/media/2023/07/05/1279337896/test_po_proforientacii.pdf)

Результаты модулей сводятся в оси «самопознание / люди / структура / баланс» и используются в разборе, сценариях A/B/C и пути обучения. Методики не заменяют консультацию психолога или профориентолога.

## Запуск через Docker

Нужны [Docker](https://docs.docker.com/get-docker/) и Compose v2.

```bash
cp .env.example .env
docker compose up --build
```

После старта:

- http://127.0.0.1:8000/miniapp/ — интерфейс
- http://127.0.0.1:8000/docs — API
- http://127.0.0.1:8000/api/health — проверка процесса

Остановка: `docker compose down`. БД в volume `vibework_data` (`/data/vibework.db` в контейнере). JSON-каталоги обучения — из образа.

## Быстрый старт без Docker

```bash
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r miniapp/requirements.txt
cp .env.example .env
python miniapp/run.py
```

Проверка: `/miniapp/`, `/docs`, `GET /api/health/llm` (поля `llm_configured`, `ok`, `model`).

## Разработка

- **API + UI (Docker):** `docker compose up --build`
- **API + UI (локально):** `python miniapp/run.py`
- **Бот** (API уже запущен): `python miniapp/bot/bot.py`
- **Полный dev-стек** (API, бот, website :8765): `bash "launch files/launch-stack.sh"` или `launch files\launch-stack.bat`
- **Тесты:** `./scripts/verify.sh` или `pytest tests/miniapp -q`

Изолированный веб без Mini App — [website/README.md](website/README.md).

## LLM

В `.env`: `CHAT_API_URL`, `CHAT_API_KEY`, `CHAT_MODEL` (OpenAI-совместимый API). Код: `miniapp/backend/wibe_work/services/llm_client.py`, промпты: `llm_prompts.py`.

## Продакшен

Уникальный `JWT_SECRET`, HTTPS, CORS, `HH_USER_AGENT`. Nginx: [deploy/VPS-HTTPS.md](deploy/VPS-HTTPS.md).

## Документация

- [miniapp/README.md](miniapp/README.md) — каталог `miniapp/`
- [miniapp/bot/README.md](miniapp/bot/README.md) — Telegram-бот
- [website/README.md](website/README.md) — legacy UI и изолированный сервер
- [docs/ENV.md](docs/ENV.md) — переменные окружения
- [docs/LEARNING_INTEGRATIONS.md](docs/LEARNING_INTEGRATIONS.md) — обучение и внешние API (VK Video и др.)
- [SECURITY.md](SECURITY.md) — уязвимости

## Структура репозитория

```
VibeWork/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── miniapp/
│   ├── run.py
│   ├── backend/wibe_work/
│   ├── frontend/
│   ├── data/
│   └── bot/
├── website/
│   ├── app/
│   └── frontend/
├── tests/miniapp|website/
├── scripts/
├── deploy/
└── docs/
```

Лицензия: [LICENSE](LICENSE) (MIT).
