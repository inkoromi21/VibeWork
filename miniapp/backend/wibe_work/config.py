import os
from datetime import timedelta

HH_USER_AGENT = os.environ.get(
    "HH_USER_AGENT",
    # hh.ru просит корректный User-Agent с контактом разработчика.
    # Замените email на ваш в .env: HH_USER_AGENT=MyApp/1.0 (you@example.com)
    "VibeWork/1.0 (dev@localhost)",
)

HH_API_BASE = "https://api.hh.ru"

HH_FINALIZE_MIN_COMPLETENESS = float(os.environ.get("HH_FINALIZE_MIN_COMPLETENESS", "0.55"))

HH_MIN_POLL_ANSWERS = int(os.environ.get("HH_MIN_POLL_ANSWERS", "0"))

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-change-me-in-production-vibework")
JWT_EXPIRE_DAYS = int(os.environ.get("JWT_EXPIRE_DAYS", "30"))
JWT_EXPIRE_DELTA = timedelta(days=JWT_EXPIRE_DAYS)
