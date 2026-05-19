"""Слияние двух user_id в один (канонический): Telegram-only ↔ аккаунт с почтой."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from wibe_work.sqlite_db import get_db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def merge_snapshots(conn, keep_uid: str, drop_uid: str) -> None:
    row_k = conn.execute(
        "SELECT payload_json FROM vibework_snapshots WHERE user_id = ?", (keep_uid,)
    ).fetchone()
    row_d = conn.execute(
        "SELECT payload_json FROM vibework_snapshots WHERE user_id = ?", (drop_uid,)
    ).fetchone()
    if not row_k and not row_d:
        return
    try:
        js_k = json.loads(row_k["payload_json"]) if row_k else {}
    except (json.JSONDecodeError, TypeError):
        js_k = {}
    try:
        js_d = json.loads(row_d["payload_json"]) if row_d else {}
    except (json.JSONDecodeError, TypeError):
        js_d = {}
    merged = dict(js_d)
    merged.update(js_k)
    raw = json.dumps(merged, ensure_ascii=False)
    conn.execute(
        """INSERT INTO vibework_snapshots (user_id, payload_json, updated_at)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET payload_json = excluded.payload_json,
             updated_at = excluded.updated_at""",
        (keep_uid, raw, _now_iso()),
    )
    conn.execute("DELETE FROM vibework_snapshots WHERE user_id = ?", (drop_uid,))


def merge_user_profiles(conn, keep_uid: str, drop_uid: str) -> None:
    rk = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (keep_uid,)).fetchone()
    rd = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (drop_uid,)).fetchone()
    if not rk and not rd:
        return
    dk = dict(rk) if rk else {}
    dd = dict(rd) if rd else {}
    dk.pop("user_id", None)
    dd.pop("user_id", None)
    merged: dict[str, Any] = {}
    all_k = set(dk.keys()) | set(dd.keys())
    for k in all_k:
        vk, vd = dk.get(k), dd.get(k)
        if vk not in (None, "", []):
            merged[k] = vk
        elif vd not in (None, "", []):
            merged[k] = vd
        else:
            merged[k] = vk if vk is not None else vd
    conn.execute("DELETE FROM user_profiles WHERE user_id IN (?, ?)", (keep_uid, drop_uid))
    if merged:
        cols = list(merged.keys())
        ph = ", ".join(["?"] * (len(cols) + 1))
        cn = "user_id, " + ", ".join(cols)
        conn.execute(
            f"INSERT INTO user_profiles ({cn}) VALUES ({ph})",
            [keep_uid] + [merged[c] for c in cols],
        )


def merge_users_into(conn, keep_user_id: str, drop_user_id: str) -> None:
    """
    Переносит данные с drop_user_id на keep_user_id.
    keep_user_id — канонический (часто аккаунт с почтой).
    """
    if keep_user_id == drop_user_id:
        return

    merge_user_profiles(conn, keep_user_id, drop_user_id)

    conn.execute(
        """DELETE FROM answers WHERE user_id = ? AND question_id IN (
            SELECT question_id FROM answers WHERE user_id = ?
        )""",
        (drop_user_id, keep_user_id),
    )
    conn.execute(
        "UPDATE answers SET user_id = ? WHERE user_id = ?",
        (keep_user_id, drop_user_id),
    )

    rows = conn.execute(
        "SELECT name, level FROM user_competencies WHERE user_id = ?",
        (drop_user_id,),
    ).fetchall()
    for row in rows:
        name = row["name"]
        level = row["level"]
        ex = conn.execute(
            "SELECT level FROM user_competencies WHERE user_id = ? AND name = ?",
            (keep_user_id, name),
        ).fetchone()
        if ex:
            mx = max(int(ex["level"]), int(level))
            conn.execute(
                "UPDATE user_competencies SET level = ? WHERE user_id = ? AND name = ?",
                (mx, keep_user_id, name),
            )
        else:
            conn.execute(
                "INSERT INTO user_competencies (user_id, name, level) VALUES (?, ?, ?)",
                (keep_user_id, name, level),
            )
    conn.execute("DELETE FROM user_competencies WHERE user_id = ?", (drop_user_id,))

    rk = conn.execute(
        "SELECT * FROM user_hh_state WHERE user_id = ?", (keep_user_id,)
    ).fetchone()
    rd = conn.execute(
        "SELECT * FROM user_hh_state WHERE user_id = ?", (drop_user_id,)
    ).fetchone()
    if rk or rd:
        dk = dict(rk) if rk else {}
        dd = dict(rd) if rd else {}
        dk.pop("user_id", None)
        dd.pop("user_id", None)
        merged_hh = dict(dd)
        for k, v in dk.items():
            if v not in (None, "", []):
                merged_hh[k] = v
        conn.execute("DELETE FROM user_hh_state WHERE user_id IN (?, ?)", (keep_user_id, drop_user_id))
        cols = [k for k, v in merged_hh.items() if k != "user_id" and v is not None]
        if cols:
            ph = ", ".join(["?"] * (len(cols) + 1))
            cns = "user_id, " + ", ".join(cols)
            conn.execute(
                f"INSERT INTO user_hh_state ({cns}) VALUES ({ph})",
                [keep_user_id] + [merged_hh[c] for c in cols],
            )

    conn.execute(
        "UPDATE ai_chat_sessions SET user_id = ? WHERE user_id = ?",
        (keep_user_id, drop_user_id),
    )

    merge_snapshots(conn, keep_user_id, drop_user_id)

    conn.execute(
        "UPDATE telegram_users SET user_id = ? WHERE user_id = ?",
        (keep_user_id, drop_user_id),
    )

    em_drop = conn.execute(
        "SELECT email FROM email_users WHERE user_id = ?", (drop_user_id,)
    ).fetchone()
    em_keep = conn.execute(
        "SELECT email FROM email_users WHERE user_id = ?", (keep_user_id,)
    ).fetchone()
    if em_drop and not em_keep:
        conn.execute(
            "UPDATE email_users SET user_id = ? WHERE user_id = ?",
            (keep_user_id, drop_user_id),
        )
    elif em_drop and em_keep:
        conn.execute("DELETE FROM email_users WHERE user_id = ?", (drop_user_id,))

    conn.execute("DELETE FROM vibework_sessions WHERE user_id = ?", (drop_user_id,))


def merge_users_into_transaction(keep_user_id: str, drop_user_id: str) -> None:
    with get_db() as conn:
        merge_users_into(conn, keep_user_id, drop_user_id)
        conn.commit()
