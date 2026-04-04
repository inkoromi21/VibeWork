from fastapi import APIRouter, Request

from wibe_work.bearer_auth import require_bearer_matches_user
from wibe_work.sqlite_db import get_db
from wibe_work.api_schemas import ProfileData

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/{nickname}")
async def get_profile(nickname: str, request: Request):
    require_bearer_matches_user(request, nickname)
    with get_db() as conn:
        profile = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?", (nickname,)
        ).fetchone()
        return dict(profile) if profile else {}


@router.post("/{nickname}")
async def save_profile(nickname: str, data: ProfileData, request: Request):
    require_bearer_matches_user(request, nickname)
    with get_db() as conn:
        existing = conn.execute(
            "SELECT 1 FROM user_profiles WHERE user_id = ?", (nickname,)
        ).fetchone()
        data_dict = data.model_dump(exclude_unset=True)
        if existing:
            if data_dict:
                sets = ", ".join([f"{k} = ?" for k in data_dict.keys()])
                conn.execute(
                    f"UPDATE user_profiles SET {sets} WHERE user_id = ?",
                    list(data_dict.values()) + [nickname],
                )
        elif data_dict:
            cols = ", ".join(data_dict.keys())
            placeholders = ", ".join(["?"] * len(data_dict))
            conn.execute(
                f"INSERT INTO user_profiles (user_id, {cols}) VALUES (?, {placeholders})",
                [nickname] + list(data_dict.values()),
            )
        else:
            conn.execute(
                "INSERT INTO user_profiles (user_id) VALUES (?)",
                (nickname,),
            )
        conn.commit()
    return {"status": "ok"}
