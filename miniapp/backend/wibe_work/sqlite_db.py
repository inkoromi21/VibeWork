"""SQLite-хранилище миниаппы: профили, опросы, JWT-сессии, снимки разбора."""

import json
import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from wibe_work.miniapp_paths import DATA_DIR, PROJECT_ROOT


def _db_path() -> Path:
    env = os.environ.get("DATABASE_PATH")
    if env:
        return Path(env)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    legacy = DATA_DIR / "career.db"
    if legacy.is_file():
        return legacy
    return DATA_DIR / "vibework.db"


_legacy_done = False


def _migrate_legacy_sqlite_once() -> None:
    global _legacy_done
    if _legacy_done:
        return
    target = _db_path()
    for legacy in (
        PROJECT_ROOT / "career.db",
        PROJECT_ROOT / "data" / "career.db",
        PROJECT_ROOT / "data" / "vibework.db",
    ):
        if legacy.exists() and not target.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy, target)
            break
    _legacy_done = True


@contextmanager
def get_db():
    _migrate_legacy_sqlite_once()
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


_PROFILE_EXTRA_COLS = [
    ("nickname", "TEXT"),
    ("main_sphere", "TEXT"),
    ("education_detail", "TEXT"),
    ("preparation_level", "TEXT"),
    ("motivation_ai", "TEXT"),
    ("work_format_pref", "TEXT"),
    ("study_form", "TEXT"),
    ("interest_spheres", "TEXT"),
    ("languages", "TEXT"),
    ("programming_skills", "TEXT"),
    ("social_media_skills", "TEXT"),
    ("extra_education", "TEXT"),
    ("soft_communication", "INTEGER"),
    ("soft_teamwork", "INTEGER"),
    ("soft_organization", "INTEGER"),
    ("soft_stress", "INTEGER"),
    ("soft_creativity", "INTEGER"),
    ("soft_analytical", "INTEGER"),
    ("experience_official", "TEXT"),
    ("experience_side", "TEXT"),
    ("experience_volunteer", "TEXT"),
    ("experience_projects", "TEXT"),
    ("achievements", "TEXT"),
    ("internship_ready", "TEXT"),
    ("hours_per_week", "INTEGER"),
    ("has_resume_portfolio", "TEXT"),
    ("acquisition_source", "TEXT"),
    ("career_priority", "TEXT"),
    ("monthly_focus_skill", "TEXT"),
    ("monthly_focus_project", "TEXT"),
    ("weekly_progress_note", "TEXT"),
]

_JOB_EXTRA_COLS = [
    ("work_format", "TEXT"),
    ("entry_level", "INTEGER DEFAULT 0"),
    ("salary_from", "INTEGER"),
    ("salary_to", "INTEGER"),
    ("free_resources_hint", "TEXT"),
]


def _ensure_columns(conn, table: str, col_defs):
    existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, ddl in col_defs:
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def _migrate(conn):
    _ensure_columns(conn, "user_profiles", _PROFILE_EXTRA_COLS)
    _ensure_columns(conn, "job_vacancies", _JOB_EXTRA_COLS)


def _seed_vacancies(conn):
    n = conn.execute("SELECT COUNT(*) AS c FROM job_vacancies").fetchone()["c"]
    if n > 0:
        return
    now = datetime.now(timezone.utc)
    rows = [
        (
            "Junior Python-разработчик",
            "TechStart LLC",
            "Backend, REST API, PostgreSQL. Гибрид.",
            18,
            45,
            "бакалавр",
            json.dumps(["python", "sql", "git"], ensure_ascii=False),
            (now - timedelta(days=5)).isoformat(),
            1,
            "hybrid",
            0,
            120000,
            200000,
            None,
        ),
        (
            "Стажёр аналитики данных",
            "DataHub",
            "SQL, отчёты, дашборды. Можно без опыта.",
            18,
            30,
            "неполное высшее",
            json.dumps(["sql", "excel"], ensure_ascii=False),
            (now - timedelta(days=40)).isoformat(),
            1,
            "remote",
            1,
            None,
            None,
            "Бесплатно: Kaggle Learn SQL, Stepik «Введение в данные»",
        ),
        (
            "Младший дизайнер интерфейсов",
            "Creative Studio",
            "Figma, UI-киты, мобильные приложения.",
            20,
            35,
            "среднее специальное",
            json.dumps(["figma", "ui"], ensure_ascii=False),
            (now - timedelta(days=2)).isoformat(),
            1,
            "hybrid",
            0,
            80000,
            120000,
            None,
        ),
        (
            "Менеджер проектов (junior)",
            "ConsultPro",
            "Agile, коммуникации с заказчиком.",
            22,
            50,
            "бакалавр",
            json.dumps(["проект", "коммуникац"], ensure_ascii=False),
            (now - timedelta(days=100)).isoformat(),
            1,
            "office",
            0,
            90000,
            140000,
            None,
        ),
        (
            "Разработчик игр (Unity)",
            "IndieGames",
            "C#, Unity. Удалённо.",
            18,
            40,
            "среднее специальное",
            json.dumps(["unity", "c#"], ensure_ascii=False),
            (now - timedelta(days=15)).isoformat(),
            1,
            "remote",
            0,
            70000,
            150000,
            None,
        ),
    ]
    conn.executemany(
        """INSERT INTO job_vacancies
        (title, company, description, min_age, max_age, min_education, required_skills,
         posted_at, is_active, work_format, entry_level, salary_from, salary_to, free_resources_hint)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def _seed_mts_catalog(conn):
    c = conn.execute(
        "SELECT COUNT(*) AS c FROM job_vacancies WHERE company = ?", ("МТС (матрица ролей)",)
    ).fetchone()["c"]
    if c > 0:
        return
    now = datetime.now(timezone.utc)
    conn.execute(
        """INSERT INTO job_vacancies
        (title, company, description, min_age, max_age, min_education, required_skills,
         posted_at, is_active, work_format, entry_level, salary_from, salary_to, free_resources_hint)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "Стажёр направление продаж и развития",
            "МТС (матрица ролей)",
            "По матрице компетенций: звонки клиентам, встречи, документы, CRM. См. /career/mts-match/",
            18,
            30,
            "неполное высшее",
            json.dumps(["продаж", "коммуникац", "презентац", "excel"], ensure_ascii=False),
            now.isoformat(),
            1,
            "hybrid",
            1,
            None,
            None,
            "Тренинги по продажам: открытые лекции, YouTube по B2B-воронке",
        ),
    )
    conn.execute(
        """INSERT INTO job_vacancies
        (title, company, description, min_age, max_age, min_education, required_skills,
         posted_at, is_active, work_format, entry_level, salary_from, salary_to, free_resources_hint)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "Стажёр HR",
            "МТС (матрица ролей)",
            "Резюме, скрининг, hh.ru, первичные интервью. Матрица компетенций МТС.",
            18,
            28,
            "неполное высшее",
            json.dumps(["коммуникац", "многозадач", "поиск информац", "excel"], ensure_ascii=False),
            now.isoformat(),
            1,
            "office",
            1,
            None,
            None,
            "Курсы рекрутинга на Stepik, материалы hh.ru для начинающих",
        ),
    )


def init_db():
    _migrate_legacy_sqlite_once()
    with get_db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY, age INTEGER, city TEXT, education_level TEXT,
            course_or_grade INTEGER, interests TEXT, like_to_do TEXT, dislike_to_do TEXT,
            work_format_preference TEXT, relocation_ready TEXT, work_schedule TEXT,
            software_skills TEXT, target_salary INTEGER, profile_completed BOOLEAN DEFAULT 0)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS telegram_users (
            telegram_id INTEGER PRIMARY KEY, user_id TEXT UNIQUE, first_name TEXT,
            username TEXT, auth_date TEXT)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, question_id INTEGER,
            text_answer TEXT, choice_id INTEGER)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS user_competencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            name TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 3,
            UNIQUE(user_id, name))"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS job_vacancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, company TEXT,
            description TEXT, min_age INTEGER, max_age INTEGER, min_education TEXT,
            required_skills TEXT, posted_at TEXT, is_active INTEGER DEFAULT 1)"""
        )
        conn.commit()
        _migrate(conn)
        conn.commit()
        _seed_vacancies(conn)
        _seed_mts_catalog(conn)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS user_hh_state (
            user_id TEXT PRIMARY KEY,
            tests_completed INTEGER NOT NULL DEFAULT 0,
            tests_completed_at TEXT,
            hh_filter_json TEXT,
            hh_area_id TEXT,
            updated_at TEXT
        )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS email_users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_at TEXT NOT NULL
        )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_password_reset_user ON password_reset_tokens(user_id)"
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS vibework_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS vibework_snapshots (
            user_id TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS ai_chat_sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            messages_json TEXT NOT NULL DEFAULT '[]',
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_chat_sessions_user ON ai_chat_sessions(user_id, updated_at DESC)"
        )
        conn.commit()
