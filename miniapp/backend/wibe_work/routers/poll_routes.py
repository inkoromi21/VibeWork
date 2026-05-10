from typing import List, Tuple

from fastapi import APIRouter, HTTPException, Request

from wibe_work.bearer_auth import require_bearer_matches_user
from wibe_work.sqlite_db import get_db
from wibe_work.api_schemas import PollAnswerRequest

router = APIRouter(prefix="/polls", tags=["polls"])


@router.get("/active/")
async def active_polls():
    return []


@router.post("/take/")
async def take_poll(data: List[PollAnswerRequest], request: Request):
    if data:
        uids = {item.user_id for item in data}
        if len(uids) != 1:
            raise HTTPException(
                status_code=400, detail="В одном запросе допустим один user_id"
            )
        require_bearer_matches_user(request, list(uids)[0])
    text_rows: List[Tuple[str, int, str]] = []
    choice_rows: List[Tuple[str, int, int]] = []
    for item in data:
        for ans in item.answers:
            if ans.text:
                text_rows.append((item.user_id, ans.question_id, ans.text))
            elif ans.choice_id:
                choice_rows.append((item.user_id, ans.question_id, ans.choice_id))
            elif ans.choice_ids:
                for cid in ans.choice_ids:
                    choice_rows.append((item.user_id, ans.question_id, cid))
    with get_db() as conn:
        if text_rows:
            conn.executemany(
                "INSERT INTO answers (user_id, question_id, text_answer) VALUES (?, ?, ?)",
                text_rows,
            )
        if choice_rows:
            conn.executemany(
                "INSERT INTO answers (user_id, question_id, choice_id) VALUES (?, ?, ?)",
                choice_rows,
            )
        conn.commit()
    return {"status": "created"}
