#!/usr/bin/env bash
# Запуск на VPS (Ubuntu), от root или через sudo.
# Предполагается: приложение слушает 127.0.0.1:8000 (vibework-api / miniapp/run.py).
#
# Использование:
#   sudo bash deploy/setup-https.sh
#   sudo CERTBOT_EMAIL=you@example.com bash deploy/setup-https.sh
#   sudo bash deploy/setup-https.sh example.com
#
# До запуска: DNS A/@ и A/www → публичный IP этой ВМ, порты 80 и 443 открыты.

set -euo pipefail

DOMAIN="${1:-vibeworkrussia.ru}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DEFAULT="/opt/vibework"

if [[ -f "$SCRIPT_DIR/nginx/vibework.conf" ]]; then
  CONF_SRC="$SCRIPT_DIR/nginx/vibework.conf"
elif [[ -f "$REPO_DEFAULT/deploy/nginx/vibework.conf" ]]; then
  CONF_SRC="$REPO_DEFAULT/deploy/nginx/vibework.conf"
else
  echo "Не найден deploy/nginx/vibework.conf (рядом со скриптом или в $REPO_DEFAULT/deploy/)." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y nginx certbot python3-certbot-nginx

install -m 644 "$CONF_SRC" /etc/nginx/sites-available/vibework
ln -sf /etc/nginx/sites-available/vibework /etc/nginx/sites-enabled/vibework
if [[ -L /etc/nginx/sites-enabled/default ]]; then
  rm -f /etc/nginx/sites-enabled/default
fi

nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo ""
echo "HTTP прокси готов. Проверьте: curl -sI http://127.0.0.1/ -H \"Host: $DOMAIN\""
echo ""

if [[ -n "${CERTBOT_EMAIL:-}" ]]; then
  certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
    --non-interactive --agree-tos -m "$CERTBOT_EMAIL" --redirect
  systemctl reload nginx
  systemctl enable --now certbot.timer 2>/dev/null || true
  echo "HTTPS включён. Проверка: curl -sI https://$DOMAIN/ | head -5"
else
  echo "Чтобы выпустить сертификат, выполните (подставьте свой email):"
  echo "  sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
  echo ""
  echo "Или повторите этот скрипт с переменной:"
  echo "  sudo CERTBOT_EMAIL=you@example.com bash $0 $DOMAIN"
fi
