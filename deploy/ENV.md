# Переменные окружения на VPS

Все ключи — в **`/opt/vibework/.env`** (корень клона репозитория). Список полей: [../docs/ENV.md](../docs/ENV.md).

1. Локально правите корневой `.env`.
2. На сервер: `.\deploy\sync-env-to-vps.ps1` или вручную тот же файл на VPS.
3. Перезапуск: `sudo bash deploy/vps-update.sh`

Файл `.env` в git не коммитится.
