"""Копирайт подбора вакансий под уровень в миниаппе."""

from pathlib import Path


def test_jobs_tab_level_copy_in_miniapp_html() -> None:
    html = (Path(__file__).resolve().parents[2] / "miniapp" / "frontend" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "jobsListingNoticeText" in html
    assert "vacancy_listing_status" in html
    assert "под ваш уровень" in html
    assert "вакансий на hh.ru сейчас не найдено" in html
    assert "могут чуть не совпадать" in html
