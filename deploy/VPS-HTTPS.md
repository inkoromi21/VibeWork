# HTTPS на VPS (nginx + Let’s Encrypt)

Приложение (`miniapp/run.py`) слушает **127.0.0.1:8000**; снаружи открывают **80/443** через **nginx** и выдают TLS сертификатом **certbot**.

## Условия

1. **DNS**: у домена A-записи `@` и `www` → **публичный IP** этой ВМ (как в панели Reg.ru).
2. **Порты** 80 и 443 разрешены в панели облака и `ufw` (если включён).
3. **Сервис API** запущен, например: `systemctl status vibework-api` и `curl -s http://127.0.0.1:8000/api/health`.

## Вариант A: скрипт с сервера

Склонируйте репозиторий на ВМ (или обновите `/opt/vibework`) и выполните:

```bash
cd /opt/vibework   # или путь к клону
sudo bash deploy/setup-https.sh
sudo bash deploy/setup-https.sh vibeworkrussia.ru   # другой домен
```

Скрипт поставит `nginx` и `certbot`, положит конфиг, спросит про запуск certbot. Для **без вопросов** с email:

```bash
sudo certbot --nginx -d vibeworkrussia.ru -d www.vibeworkrussia.ru \
  --non-interactive --agree-tos -m you@example.com
```

## Вариант B: вручную

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp deploy/nginx/vibework.conf /etc/nginx/sites-available/vibework
# В файле при необходимости замените server_name на ваш домен.
sudo ln -sf /etc/nginx/sites-available/vibework /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Проверьте `http://ваш-домен/`, затем:

```bash
sudo certbot --nginx -d vibeworkrussia.ru -d www.vibeworkrussia.ru
```

Проверка:

```bash
sudo ss -tlnp | grep -E ':80|:443'
curl -sI https://vibeworkrussia.ru/ | head -5
```

## Переменные окружения

В `/opt/vibework/.env` должны быть согласованы с публичным URL:

- `PUBLIC_BASE_URL=https://vibeworkrussia.ru`
- `TELEGRAM_PUBLIC_BASE_URL` — тот же базовый URL, если используется.

После правок: `sudo systemctl restart vibework-api`.

## Файлы в репозитории

- [nginx/vibework.conf](nginx/vibework.conf) — прокси на `127.0.0.1:8000`
- [setup-https.sh](setup-https.sh) — установка пакетов, конфиг, приглашение certbot
