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

# Отправитель: "VibeWork <noreply@your-domain.ru>" (домен должен быть верифицирован в Resend).
EMAIL_FROM = os.environ.get("EMAIL_FROM", "").strip()

# Resend: https://resend.com/docs/api-reference/emails/send-email
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
RESEND_BASE_URL = os.environ.get("RESEND_BASE_URL", "https://api.resend.com").strip()
