"""Маршруты: схема анкеты, тест, разбор, чат с ИИ, симулятор дня (префикс /vibework для фронта)."""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from wibe_work.sqlite_db import get_db
from wibe_work.bearer_auth import require_bearer_matches_user
from wibe_work.questionnaire_fields import get_profile_schema
from wibe_work.services.user_context import coach_profile_snippet, load_profile, parse_interest_spheres
from wibe_work.services.career_analysis import build_analysis_result, public_analysis_payload
from wibe_work.services.llm_client import career_coach_chat_reply
from wibe_work.services.aptitude_quiz import get_questions_for_interest
from wibe_work.services.aptitude_quiz_grading import (
    compute_quiz_grade,
    quiz_grade_hint,
    quiz_grade_label,
)
from wibe_work.services.workday_simulator import (
    list_simulator_options,
    start as sim_start,
    step as sim_step,
)
from wibe_work.services.ai_chat_sessions import (
    get_messages as load_chat_session_messages,
    list_sessions as list_chat_sessions,
    upsert_session as save_chat_session,
)

_SESSION_ID_RE = re.compile(r"^[0-9A-Za-z\-]{8,64}$")


def _validate_chat_session_id(session_id: str) -> str:
    s = (session_id or "").strip()
    if not s or len(s) > 64 or not _SESSION_ID_RE.match(s):
        raise HTTPException(status_code=422, detail="Некорректный идентификатор чата")
    return s

router = APIRouter(tags=["vibework"])


@router.get("/api/profile/schema")
async def profile_schema():
    """Структура анкеты (зеркало Google Sheet)."""
    return get_profile_schema()


class QuizAnswerIn(BaseModel):
    question_id: int
    choice: str = Field(..., min_length=1, max_length=8)


class AnalyzeRequest(BaseModel):
    answers: List[QuizAnswerIn]
    interest: Optional[str] = None
    preparation_level: Optional[str] = None
    question_timings_ms: Optional[List[int]] = Field(
        default=None,
        description="Длительность ответа в мс в том же порядке, что answers (для behavioral_hint)",
    )


def _save_analysis_snapshot(user_id: str, full: Dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(full, ensure_ascii=False)
    with get_db() as conn:
        conn.execute(
            """INSERT INTO vibework_snapshots (user_id, payload_json, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 payload_json = excluded.payload_json,
                 updated_at = excluded.updated_at""",
            (user_id, payload, now),
        )
        conn.commit()


def _load_analysis_snapshot(user_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT payload_json FROM vibework_snapshots WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["payload_json"])
    except (json.JSONDecodeError, TypeError):
        return None


def _interest_for_user(profile: Dict[str, Any], override: Optional[str]) -> str:
    if override and str(override).strip():
        return str(override).strip()
    ms = (profile.get("main_sphere") or "").strip()
    if ms:
        return ms
    spheres = parse_interest_spheres(profile)
    if spheres:
        return spheres[0]
    return "other"


def _prep_for_user(profile: Dict[str, Any], override: Optional[str]) -> str:
    if override and str(override).strip():
        return str(override).strip()
    p = (profile.get("preparation_level") or "").strip()
    if p in ("weak", "medium", "strong"):
        return p
    return "medium"


miniapp_prefixed_router = APIRouter(prefix="/vibework", tags=["vibework"])


@miniapp_prefixed_router.get("/quiz/questions/{user_id}")
async def quiz_questions(
    user_id: str,
    request: Request,
    interest: Optional[str] = None,
):
    require_bearer_matches_user(request, user_id)
    profile = load_profile(user_id)
    intr = _interest_for_user(profile, interest)
    grade = compute_quiz_grade(profile)
    return {
        "interest": intr,
        "test_grade": grade,
        "test_grade_label": quiz_grade_label(grade),
        "test_grade_hint": quiz_grade_hint(grade),
        "questions": get_questions_for_interest(intr, grade),
    }


@miniapp_prefixed_router.post("/quiz/analyze/{user_id}")
async def quiz_analyze(user_id: str, request: Request, body: AnalyzeRequest):
    require_bearer_matches_user(request, user_id)
    profile = load_profile(user_id)
    if not body.answers:
        raise HTTPException(status_code=400, detail="Нужны ответы на вопросы")
    interest = _interest_for_user(profile, body.interest)
    preparation = _prep_for_user(profile, body.preparation_level)
    education = (profile.get("education_level") or "не указано").strip()
    answers_dicts = [
        {"question_id": a.question_id, "choice": a.choice.strip()} for a in body.answers
    ]
    profile_extra = {
        "city": profile.get("city"),
        "age": profile.get("age"),
    }
    full = build_analysis_result(
        profile,
        profile_extra,
        interest,
        education,
        preparation,
        answers_dicts,
        question_timings_ms=body.question_timings_ms,
    )
    _save_analysis_snapshot(user_id, full)
    return public_analysis_payload(full)


@miniapp_prefixed_router.get("/analysis/{user_id}")
async def get_saved_analysis(user_id: str, request: Request):
    require_bearer_matches_user(request, user_id)
    snap = _load_analysis_snapshot(user_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Сначала пройдите тест и разбор")
    return public_analysis_payload(snap)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class ChatHistorySave(BaseModel):
    messages: List[ChatMessage]


@miniapp_prefixed_router.get("/chat/history/{user_id}")
async def chat_history_list(user_id: str, request: Request):
    require_bearer_matches_user(request, user_id)
    return {"sessions": list_chat_sessions(user_id)}


@miniapp_prefixed_router.get("/chat/history/{user_id}/{session_id}")
async def chat_history_get(user_id: str, session_id: str, request: Request):
    require_bearer_matches_user(request, user_id)
    sid = _validate_chat_session_id(session_id)
    msgs = load_chat_session_messages(user_id, sid)
    if msgs is None:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return {"session_id": sid, "messages": msgs}


@miniapp_prefixed_router.put("/chat/history/{user_id}/{session_id}")
async def chat_history_save(
    user_id: str, session_id: str, request: Request, body: ChatHistorySave
):
    require_bearer_matches_user(request, user_id)
    sid = _validate_chat_session_id(session_id)
    msgs = [{"role": m.role, "content": m.content} for m in body.messages]
    if len(msgs) > 400:
        raise HTTPException(status_code=422, detail="Слишком длинная история сообщений")
    save_chat_session(user_id, sid, msgs)
    return {"ok": True}


@miniapp_prefixed_router.post("/chat/{user_id}")
async def career_coach_chat(user_id: str, request: Request, body: ChatRequest):
    require_bearer_matches_user(request, user_id)
    snap = _load_analysis_snapshot(user_id)
    summary = (
        (snap or {}).get("profile_summary")
        or "Пользователь без сохранённого разбора; отвечайте общими советами для 14–30."
    )
    hint = (snap or {}).get("directions_hint") or ""
    msgs = [{"role": m.role, "content": m.content} for m in body.messages[-20:]]
    snippet = coach_profile_snippet(load_profile(user_id))
    reply, source, notice = career_coach_chat_reply(msgs, summary, hint, snippet)
    return {"reply": reply, "source": source, "notice": notice}


class SimulatorStartBody(BaseModel):
    role: str = "analyst"


@miniapp_prefixed_router.get("/simulator/options")
async def simulator_options():
    """Сферы как в анкете (главная сфера) → сценарий «день на работе»."""
    return {"options": list_simulator_options()}


@miniapp_prefixed_router.post("/simulator/start")
async def simulator_start(body: SimulatorStartBody):
    return sim_start(body.role)


class SimulatorStepBody(BaseModel):
    role: str
    step_index: int = 0
    career_points: int = 0
    choice_id: str


@miniapp_prefixed_router.post("/simulator/step")
async def simulator_step(body: SimulatorStepBody):
    return sim_step(body.role, body.step_index, body.career_points, body.choice_id)
