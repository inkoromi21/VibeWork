"""Cookie Secure не должен ломать вход по http://127.0.0.1 в dev."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))


def test_cookie_secure_false_in_dev_even_if_public_base_https(monkeypatch):
    monkeypatch.setenv("VIBEWORK_ENV", "dev")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://production.example.com")
    monkeypatch.delenv("COOKIE_SECURE", raising=False)

    import wibe_work.config as cfg

    importlib.reload(cfg)
    assert cfg.cookie_secure() is False


def test_cookie_secure_true_in_prod_with_https(monkeypatch):
    monkeypatch.setenv("VIBEWORK_ENV", "prod")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://production.example.com")
    monkeypatch.delenv("COOKIE_SECURE", raising=False)

    import wibe_work.config as cfg

    importlib.reload(cfg)
    assert cfg.cookie_secure() is True
