import os
from datetime import timedelta

# Окружение приложения: dev | prod (влияет на строгие проверки безопасности в main.py)
VIBEWORK_ENV = os.environ.get("VIBEWORK_ENV", "dev").strip().lower() or "dev"

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
# Токены, выданные до этой метки (ISO UTC), считаются недействительными. Задайте при полном сбросе аккаунтов.
JWT_INVALID_BEFORE = os.environ.get("JWT_INVALID_BEFORE", "").strip()

# Восстановление пользователей из website/data/vibework.db при входе (по умолчанию выкл.)
ENABLE_LEGACY_WEBSITE_MIGRATION = os.environ.get(
    "ENABLE_LEGACY_WEBSITE_MIGRATION", ""
).strip().lower() in ("1", "true", "yes")

# CORS для браузера. В проде задайте домен(ы) явно: "https://vibework.example,https://www.vibework.example"
# По умолчанию — только локальная разработка.
CORS_ALLOW_ORIGINS = os.environ.get(
    "CORS_ALLOW_ORIGINS",
    "http://127.0.0.1:8000,http://localhost:8000",
).strip()

# Cookie-сессии сайта: Secure включайте при HTTPS (в проде по умолчанию True, если PUBLIC_BASE_URL https://…)
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "").strip()

# Telegram: в проде подпись init_data должна проверяться (иначе можно подделать вход).
REQUIRE_TELEGRAM_BOT_TOKEN = os.environ.get("REQUIRE_TELEGRAM_BOT_TOKEN", "").strip()

# Публичный URL сайта (для ссылок в письмах сброса пароля). Без завершающего слэша.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8000").strip().rstrip("/")

# Админ-панель: /admin (отдельный вход, не связан с аккаунтами пользователей)
ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN", "").strip()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
ADMIN_SESSION_HOURS = int(os.environ.get("ADMIN_SESSION_HOURS", "12") or "12")


def cookie_secure() -> bool:
    """Secure-флаг для httponly-cookie (сессии сайта и админки)."""
    raw = COOKIE_SECURE.strip().lower()
    if raw in ("1", "true", "yes", "y", "on"):
        return True
    if raw in ("0", "false", "no", "n", "off"):
        return False
    # В dev не выставляем Secure по PUBLIC_BASE_URL (часто https в .env при http://127.0.0.1)
    if VIBEWORK_ENV != "prod":
        return False
    return PUBLIC_BASE_URL.lower().startswith("https://")

# Отправитель: "VibeWork <noreply@your-domain.ru>" (домен должен быть верифицирован в Resend).
EMAIL_FROM = os.environ.get("EMAIL_FROM", "").strip()

# Resend: https://resend.com/docs/api-reference/emails/send-email
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
RESEND_BASE_URL = os.environ.get("RESEND_BASE_URL", "https://api.resend.com").strip()

# Обучение: внешние API (опционально; без ключей — каталог, Exercism/Codewars)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
ONET_USERNAME = os.environ.get("ONET_USERNAME", "").strip()
ONET_PASSWORD = os.environ.get("ONET_PASSWORD", "").strip()
ESCO_API_ENABLED = os.environ.get("ESCO_API_ENABLED", "1").strip().lower() in (
    "1",
    "true",
    "yes",
)

# VK Video API (https://dev.vk.com/ru/method/video.search, video.get)
# Сервисный ключ приложения: vk.com/apps → ваше приложение → «Сервисный ключ доступа»
VK_ACCESS_TOKEN = os.environ.get("VK_ACCESS_TOKEN", "").strip()
VK_API_VERSION = os.environ.get("VK_API_VERSION", "5.199").strip() or "5.199"


def _parse_vk_owner_ids(raw: str) -> list[int]:
    out: list[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out


# Сообщества с учебными плейлистами (owner_id со знаком «-», через запятую)
VK_VIDEO_OWNER_IDS = _parse_vk_owner_ids(os.environ.get("VK_VIDEO_OWNER_IDS", ""))
