"""Маршруты: схема анкеты, тест, разбор, чат с ИИ, симулятор дня (префикс /vibework для фронта)."""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from wibe_work.sqlite_db import get_db
from wibe_work.bearer_auth import optional_user_id_from_bearer, require_bearer_matches_user
from wibe_work.questionnaire_fields import get_profile_schema
from wibe_work.services.user_context import coach_profile_snippet, load_profile, parse_interest_spheres
from wibe_work.services.career_analysis import (
    build_analysis_result,
    public_analysis_payload,
    refresh_mts_matrix_in_snapshot,
)
from wibe_work.services.learning.engine import build_learning_path_payload
from wibe_work.services.learning.progress import set_step_status
from wibe_work.services.llm_client import career_coach_chat_reply
from wibe_work.services.aptitude_quiz import get_questions_for_interest
from wibe_work.services.aptitude_quiz_grading import (
    compute_quiz_grade,
    quiz_grade_hint,
    quiz_grade_label,
)
from wibe_work.services.simulator_progress import save_progress as save_simulator_progress
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
    from wibe_work.services.aptitude_quiz import get_quiz_bundle

    bundle = get_quiz_bundle(intr, grade)
    return {
        "interest": bundle["interest"],
        "test_grade": grade,
        "test_grade_label": quiz_grade_label(grade),
        "test_grade_hint": quiz_grade_hint(grade),
        "technical_count": bundle["technical_count"],
        "personality_count": bundle["personality_count"],
        "technical": bundle["technical"],
        "personality": bundle["personality"],
        "questions": bundle["questions"],
    }


@miniapp_prefixed_router.post("/quiz/analyze/{user_id}")
async def quiz_analyze(user_id: str, request: Request, body: AnalyzeRequest):
    require_bearer_matches_user(request, user_id)
    profile = load_profile(user_id)
    if not body.answers:
        raise HTTPException(status_code=400, detail="Нужны ответы на вопросы")
    qids = {int(a.question_id) for a in body.answers}
    expected = set(range(1, 16))
    if qids != expected:
        missing = sorted(expected - qids)
        raise HTTPException(
            status_code=400,
            detail=f"Нужны ответы на все 15 вопросов (1–10 по сфере, 11–15 личностные). Не хватает: {missing}",
        )
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
    profile = dict(profile)
    profile["_user_id"] = user_id
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


@miniapp_prefixed_router.get("/analysis/{user_id}/status")
async def analysis_exists(user_id: str, request: Request):
    """Быстрая проверка наличия разбора без пересборки learning path."""
    require_bearer_matches_user(request, user_id)
    return {"exists": bool(_load_analysis_snapshot(user_id))}


@miniapp_prefixed_router.get("/analysis/{user_id}")
async def get_saved_analysis(user_id: str, request: Request):
    require_bearer_matches_user(request, user_id)
    snap = _load_analysis_snapshot(user_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Сначала пройдите тест и разбор")
    profile = load_profile(user_id)
    profile_extra = {
        "city": profile.get("city"),
        "age": profile.get("age"),
    }
    refreshed = refresh_mts_matrix_in_snapshot(snap, profile, profile_extra)
    if refreshed is not snap:
        _save_analysis_snapshot(user_id, refreshed)

    lp = refreshed.get("learning_path")
    has_path = isinstance(lp, dict) and bool(lp.get("steps"))
    if has_path:
        from wibe_work.services.learning.engine import merge_learning_progress_in_snapshot

        refreshed = merge_learning_progress_in_snapshot(refreshed, user_id)
    else:
        eff = str(refreshed.get("_analysis_interest") or _interest_for_user(profile, None))
        prep = _prep_for_user(profile, None)
        from wibe_work.services.learning.engine import build_learning_for_analysis

        pack = build_learning_for_analysis(
            user_id=user_id,
            profile=profile,
            interest=eff,
            preparation_level=prep,
            scenarios=refreshed.get("scenarios"),
            gap=refreshed.get("gap_analysis"),
        )
        refreshed = dict(refreshed)
        refreshed["learning_path"] = pack.get("learning_path")
        refreshed["learning"] = pack.get("learning")
        _save_analysis_snapshot(user_id, refreshed)

    return public_analysis_payload(refreshed)


class LearningStepBody(BaseModel):
    path_id: str
    step_id: str
    status: str = Field(description="pending | in_progress | done")


@miniapp_prefixed_router.post("/learning/progress/{user_id}")
async def learning_progress_update(
    user_id: str, request: Request, body: LearningStepBody
):
    require_bearer_matches_user(request, user_id)
    set_step_status(user_id, body.path_id.strip(), body.step_id.strip(), body.status.strip())
    snap = _load_analysis_snapshot(user_id)
    lp = (snap or {}).get("learning_path")
    if isinstance(lp, dict) and lp.get("steps") and str(lp.get("path_id") or "") == body.path_id.strip():
        from wibe_work.services.learning.engine import merge_learning_progress_in_snapshot

        merged = merge_learning_progress_in_snapshot(snap, user_id)
        return {"ok": True, "learning_path": merged.get("learning_path") or lp}
    profile = load_profile(user_id)
    eff = _interest_for_user(profile, None)
    if snap and snap.get("_analysis_interest"):
        eff = str(snap["_analysis_interest"])
    lp = build_learning_path_payload(
        user_id=user_id,
        profile=profile,
        interest=eff,
        preparation_level=_prep_for_user(profile, None),
        scenarios=(snap or {}).get("scenarios"),
        gap=(snap or {}).get("gap_analysis"),
    )
    return {"ok": True, "learning_path": lp}


@miniapp_prefixed_router.get("/learning/status")
async def learning_integration_status():
    from wibe_work.services.learning import get_integration_status

    return get_integration_status()


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
    profile = load_profile(user_id)
    snippet = coach_profile_snippet(profile)
    reply, source, notice = career_coach_chat_reply(
        msgs,
        summary,
        hint,
        snippet,
        profile=profile,
        analysis_snap=snap,
    )
    return {"reply": reply, "source": source, "notice": notice}


class SimulatorStartBody(BaseModel):
    role: str = "analyst"


@miniapp_prefixed_router.get("/simulator/options")
async def simulator_options():
    """Сферы как в анкете (главная сфера) → сценарий «день на работе»."""
    return {"options": list_simulator_options()}


@miniapp_prefixed_router.post("/simulator/start")
async def simulator_start(body: SimulatorStartBody, request: Request):
    result = sim_start(body.role)
    uid = optional_user_id_from_bearer(request)
    if uid:
        save_simulator_progress(uid, result)
    return result


class SimulatorStepBody(BaseModel):
    role: str
    step_index: int = 0
    career_points: int = 0
    choice_id: str
    day_path: List[Dict[str, Any]] | None = None


@miniapp_prefixed_router.post("/simulator/step")
async def simulator_step(body: SimulatorStepBody, request: Request):
    result = sim_step(
        body.role,
        body.step_index,
        body.career_points,
        body.choice_id,
        body.day_path,
    )
    uid = optional_user_id_from_bearer(request)
    if uid:
        save_simulator_progress(uid, result)
    return result
