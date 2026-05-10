import os
from datetime import timedelta

HH_USER_AGENT = os.environ.get(
    "HH_USER_AGENT",
    # hh.ru просит корректный User-Agent с контактом разработчика.
    # Замените email на ваш в .env: HH_USER_AGENT=MyApp/1.0 (you@example.com)
    "VibeWork/1.0 (dev@localhost)",
)

HH_API_BASE = "https://api.hh.ru"

# Опционально: токен приложения (https://dev.hh.ru/admin) или client_id/client_secret
# для POST https://api.hh.ru/token (grant_type=client_credentials). См. docs в репозитории hhru/api.
HH_APP_ACCESS_TOKEN = os.environ.get("HH_APP_ACCESS_TOKEN", "").strip()
HH_CLIENT_ID = os.environ.get("HH_CLIENT_ID", "").strip()
HH_CLIENT_SECRET = os.environ.get("HH_CLIENT_SECRET", "").strip()

HH_FINALIZE_MIN_COMPLETENESS = float(os.environ.get("HH_FINALIZE_MIN_COMPLETENESS", "0.55"))

HH_MIN_POLL_ANSWERS = int(os.environ.get("HH_MIN_POLL_ANSWERS", "0"))

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-change-me-in-production-vibework")
JWT_EXPIRE_DAYS = int(os.environ.get("JWT_EXPIRE_DAYS", "30"))
JWT_EXPIRE_DELTA = timedelta(days=JWT_EXPIRE_DAYS)

# Публичный URL сайта (для ссылок в письмах сброса пароля). Без завершающего слэша.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8000").strip().rstrip("/")

# Mailgun: https://documentation.mailgun.com/en/latest/api-sending.html
MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY", "").strip()
MAILGUN_DOMAIN = os.environ.get("MAILGUN_DOMAIN", "").strip()
# us | eu — хост API
MAILGUN_REGION = os.environ.get("MAILGUN_REGION", "us").strip().lower()
# Отправитель: "VibeWork <noreply@mg.example.com>" или "VibeWork <you@yandex.ru>"
EMAIL_FROM = os.environ.get("EMAIL_FROM", "").strip()

# Unisender Go (транзакционные письма по HTTPS API): https://goapi.unisender.ru
UNISENDER_API_KEY = os.environ.get("UNISENDER_API_KEY", "").strip()
UNISENDER_GO_BASE_URL = os.environ.get(
    "UNISENDER_GO_BASE_URL", "https://goapi.unisender.ru"
).strip()

# Unisender Web API (sendEmail) — базовый тариф Unisender, требует list_id и подтверждённого sender_email.
UNISENDER_LIST_ID = os.environ.get("UNISENDER_LIST_ID", "").strip()
UNISENDER_WEB_BASE_URL = os.environ.get(
    "UNISENDER_WEB_BASE_URL", "https://api.unisender.com"
).strip()

# SMTP (бесплатно с Яндекс / Mail.ru / хостингом — пароль приложения). Приоритетнее Mailgun, если задан хост.
def _smtp_port() -> int:
    raw = os.environ.get("EMAIL_SMTP_PORT", "587").strip()
    try:
        return max(1, min(65535, int(raw)))
    except ValueError:
        return 587


EMAIL_SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "").strip()
EMAIL_SMTP_PORT = _smtp_port()
EMAIL_SMTP_USER = os.environ.get("EMAIL_SMTP_USER", "").strip()
EMAIL_SMTP_PASSWORD = os.environ.get("EMAIL_SMTP_PASSWORD", "").strip()
EMAIL_SMTP_USE_SSL = os.environ.get("EMAIL_SMTP_USE_SSL", "").strip().lower() in (
    "1",
    "true",
    "yes",
)
