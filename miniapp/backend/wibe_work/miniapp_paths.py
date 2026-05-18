"""Корень репозитория и пути к артефактам миниаппы."""
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _PACKAGE_DIR.parent
_MINIAPP_ROOT = _BACKEND_ROOT.parent
if _MINIAPP_ROOT.name == "miniapp":
    PROJECT_ROOT = _MINIAPP_ROOT.parent
else:
    PROJECT_ROOT = _BACKEND_ROOT.parent

# Данные миниаппы (SQLite, JSON) — внутри miniapp/data/
DATA_DIR = _MINIAPP_ROOT / "data"
MINIAPP_HTML = _MINIAPP_ROOT / "frontend" / "index.html"
WEBSITE_HTML = PROJECT_ROOT / "website" / "frontend" / "index.html"
RESET_PASSWORD_HTML = _MINIAPP_ROOT / "frontend" / "reset-password.html"
ADMIN_HTML = _MINIAPP_ROOT / "frontend" / "admin" / "index.html"
STATIC_DIR = _MINIAPP_ROOT / "frontend" / "static"


def data_file(name: str) -> Path:
    """Файл из miniapp/data/ или, при отсутствии, из legacy data/ в корне репозитория."""
    primary = DATA_DIR / name
    if primary.is_file():
        return primary
    legacy = PROJECT_ROOT / "data" / name
    if legacy.is_file():
        return legacy
    return primary
