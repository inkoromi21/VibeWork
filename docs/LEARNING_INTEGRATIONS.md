# Обучение: интеграции и что нужно настроить вручную

## Уже работает без ключей

| Источник | Как подключено |
|----------|----------------|
| roadmap.sh, Odin, freeCodeCamp, CS50, MDN, DevDocs | Каталог `miniapp/data/learning_catalog.json` |
| Stepik, SQL Academy, Figma, HubSpot, Atlassian, Kaggle, HF, Google, DL.AI | Тот же каталог |
| Microsoft Learn, LinkedIn, Udemy, LeetCode | Ссылки в каталоге (без live API) |
| **Rutube** | Поиск `rutube.ru/api/search/video/` + витрина [education](https://rutube.ru/api/feeds/education?format=json) ([ShowcaseTutorial](https://github.com/rutube/ShowcaseTutorial)) — **без ключа** |
| **VK Video** | [video.search](https://dev.vk.com/ru/method/video.search) + опционально [video.get](https://dev.vk.com/ru/method/video.get) по `VK_VIDEO_OWNER_IDS` — нужен `VK_ACCESS_TOKEN` |
| **Exercism** | API `api.exercism.org` — задачи на шаг |
| **Codewars** | Публичный API kata |
| **ESCO** | API ESCO (включено по умолчанию: `ESCO_API_ENABLED=1`) |
| Пути по шагам | `miniapp/data/learning_paths.json` |
| Прогресс шагов | SQLite `learning_progress`, API `POST /vibework/learning/progress/{user_id}` |

## Нужны ключи / регистрация (опционально, усиливают подбор)

| Переменная `.env` | Сервис | Зачем | Где получить |
|-------------------|--------|-------|--------------|
| `VK_ACCESS_TOKEN` | VK API | Поиск видео в путях обучения (дополняет Rutube) | [vk.com/apps](https://vk.com/apps) → приложение → сервисный ключ |
| `VK_VIDEO_OWNER_IDS` | VK `video.get` | Видео из альбомов указанных сообществ (id со знаком `-`) | ID сообщества в URL группы |
| `VK_API_VERSION` | VK API | Версия API (по умолчанию `5.199`) | — |
| `GITHUB_TOKEN` | GitHub REST | Поиск репозиториев-проектов (выше лимит без 403) | GitHub → Settings → Developer settings → PAT |
| `ONET_USERNAME` + `ONET_PASSWORD` | O*NET Web Services | Профессии/навыки (США) | [onetcenter.org](https://www.onetcenter.org/webowners/) |
| `ESCO_API_ENABLED=0` | ESCO | Отключить запросы к EU API при блокировках | — |

## Нельзя полностью подключить через публичный API

| Сервис | Причина | Что сделано вместо |
|--------|---------|-------------------|
| **LinkedIn Learning** | Нет каталога для сторонних приложений | Ссылка в каталоге |
| **Udemy** | Affiliate/Business API по заявке, платные курсы | Ссылка в каталоге |
| **Kaggle Learn** | Нет API списка микрокурсов | Ссылка в каталоге |
| **LeetCode** | Нет публичного API задач | Ссылка на Explore |
| **Microsoft Learn** | Catalog API требует Azure App | Прямые ссылки на learning paths |
| **DevDocs** | Нет официального API для продакшена | Ссылка devdocs.io |
| **The Odin Project / FCC** | Curriculum на GitHub, без API | Ссылки + путь в `learning_paths.json` |
| **DeepLearning.AI** | Курсы на платформе партнёра | Ссылки на short courses |
| **Figma / Google Design / HubSpot / Atlassian** | Нет course API | Ссылки в каталоге |

## API статус

`GET /vibework/learning/status` — какие интеграции сконфигурированы.

## Метрики пути

В разборе (`learning_path.metrics`):

- `coverage_percent` — доля шагов со статусом `done`
- `current_step_index` — первый незавершённый шаг
- `total_steps` / `completed_steps`

Пользователь отмечает шаги кнопками «В работе» / «Готово» в разделе «Разбор».

## Деплой

После `git pull` перезапустите API. Новые таблицы создаются при первом запросе прогресса.

Добавьте в **корневой** `.env` (см. [ENV.md](ENV.md)):

```env
VK_ACCESS_TOKEN=
VK_VIDEO_OWNER_IDS=
GITHUB_TOKEN=
ONET_USERNAME=
ONET_PASSWORD=
ESCO_API_ENABLED=1
```
