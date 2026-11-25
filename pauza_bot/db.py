"""PostgreSQL (Supabase) persistence for applications and coach notes."""

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator

import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

_pool: asyncpg.Pool | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return _pool


@asynccontextmanager
async def connection() -> AsyncIterator[asyncpg.Connection]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


def _decode_application(row: asyncpg.Record | dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    # Явное приведение к dict для анализатора типов
    item: dict[str, Any] = dict(row)
    for column, key in (("days_json", "days"), ("times_json", "times")):
        try:
            item[key] = json.loads(item.get(column) or "[]")
        except (TypeError, json.JSONDecodeError):
            item[key] = []
    return item


async def init_db() -> None:
    async with connection() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                tg_username TEXT,
                full_name TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                contact TEXT NOT NULL,
                school TEXT NOT NULL DEFAULT 'no',
                school_name TEXT,
                school_years TEXT,
                height_cm INTEGER NOT NULL,
                weight_kg DOUBLE PRECISION NOT NULL,
                primary_position TEXT NOT NULL,
                secondary_position TEXT NOT NULL,
                working_foot TEXT NOT NULL,
                level TEXT NOT NULL,
                achievements TEXT,
                video_link TEXT,
                days_json TEXT NOT NULL DEFAULT '[]',
                times_json TEXT NOT NULL DEFAULT '[]',
                injuries TEXT NOT NULL DEFAULT 'no',
                injury_details TEXT,
                referral_source TEXT NOT NULL,
                about TEXT,
                additional_info TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                taken_by_id BIGINT,
                taken_by_name TEXT,
                taken_at TEXT,
                action_by_name TEXT,
                admin_message_id BIGINT,
                created_at TEXT NOT NULL,
                status_updated_at TEXT NOT NULL,
                audition_details TEXT
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_applications_user_status ON applications(user_id, status)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_applications_created_at ON applications(created_at DESC)"
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id BIGSERIAL PRIMARY KEY,
                application_id BIGINT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
                admin_id BIGINT NOT NULL,
                admin_name TEXT NOT NULL,
                note_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_notes_application ON notes(application_id, created_at)"
        )


async def application_gate(user_id: int) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    async with connection() as db:
        active = await db.fetchrow(
            """
            SELECT id, status FROM applications
            WHERE user_id = $1 AND status IN ('new', 'in_progress')
            ORDER BY id DESC LIMIT 1
            """,
            user_id,
        )
        rejected = await db.fetchrow(
            """
            SELECT status_updated_at FROM applications
            WHERE user_id = $1 AND status = 'rejected'
            ORDER BY status_updated_at DESC LIMIT 1
            """,
            user_id,
        )
    if active:
        return {"allowed": False, "reason": "active", "application_id": active["id"]}
    if rejected:
        try:
            rejected_at = datetime.fromisoformat(rejected["status_updated_at"])
            if rejected_at.tzinfo is None:
                rejected_at = rejected_at.replace(tzinfo=timezone.utc)
            available_at = rejected_at + timedelta(days=14)
            if now < available_at:
                return {"allowed": False, "reason": "cooldown", "available_at": available_at}
        except (TypeError, ValueError):
            pass
    return {"allowed": True}


async def create_application_if_allowed(
    user_id: int, tg_username: str | None, data: dict[str, Any]
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat(timespec="seconds")
    async with connection() as db:
        async with db.transaction():
            active = await db.fetchrow(
                """
                SELECT id FROM applications
                WHERE user_id = $1 AND status IN ('new', 'in_progress')
                ORDER BY id DESC LIMIT 1
                """,
                user_id,
            )
            if active:
                return {"ok": False, "reason": "active", "application_id": active["id"]}
            rejected = await db.fetchrow(
                """
                SELECT status_updated_at FROM applications
                WHERE user_id = $1 AND status = 'rejected'
                ORDER BY status_updated_at DESC LIMIT 1
                """,
                user_id,
            )
            if rejected:
                try:
                    rejected_at = datetime.fromisoformat(rejected["status_updated_at"])
                    if rejected_at.tzinfo is None:
                        rejected_at = rejected_at.replace(tzinfo=timezone.utc)
                    available_at = rejected_at + timedelta(days=14)
                    if now < available_at:
                        return {"ok": False, "reason": "cooldown", "available_at": available_at}
                except (TypeError, ValueError):
                    pass
            application_id = await db.fetchval(
                """
                INSERT INTO applications (
                    user_id, tg_username, full_name, birth_date, contact, school,
                    school_name, school_years, height_cm, weight_kg, primary_position,
                    secondary_position, working_foot, level, achievements, video_link,
                    days_json, times_json, injuries, injury_details, referral_source,
                    about, additional_info, created_at, status_updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25)
                RETURNING id
                """,
                user_id,
                tg_username,
                data["full_name"],
                data["birth_date"],
                data["contact"],
                data.get("school", "no"),
                data.get("school_name"),
                data.get("school_years"),
                data["height_cm"],
                data["weight_kg"],
                data["primary_position"],
                data["secondary_position"],
                data["working_foot"],
                data["level"],
                data.get("achievements"),
                data.get("video_link"),
                json.dumps(data.get("days", []), ensure_ascii=False),
                json.dumps(data.get("times", []), ensure_ascii=False),
                data.get("injuries", "no"),
                data.get("injury_details"),
                data.get("referral_source", ""),
                data.get("about"),
                data.get("additional_info"),
                timestamp,
                timestamp,
            )
    return {"ok": True, "application_id": application_id}


async def get_application(application_id: int) -> dict[str, Any] | None:
    async with connection() as db:
        row = await db.fetchrow("SELECT * FROM applications WHERE id = $1", application_id)
    return _decode_application(row)


async def get_latest_application(user_id: int) -> dict[str, Any] | None:
    async with connection() as db:
        row = await db.fetchrow(
            "SELECT * FROM applications WHERE user_id = $1 ORDER BY id DESC LIMIT 1",
            user_id,
        )
    return _decode_application(row)


async def set_admin_message_id(application_id: int, message_id: int) -> None:
    async with connection() as db:
        await db.execute(
            "UPDATE applications SET admin_message_id = $1 WHERE id = $2",
            message_id,
            application_id,
        )


async def update_status(
    application_id: int,
    expected_statuses: tuple[str, ...],
    new_status: str,
    admin_id: int,
    admin_name: str,
    *,
    claim: bool = False,
    audition_details: str | None = None,
) -> dict[str, Any] | None:
    if not expected_statuses:
        return None
    placeholders = ", ".join(f"${i + 4}" for i in range(len(expected_statuses)))
    timestamp = utc_now()
    claim_sql = ", taken_by_id = $4, taken_by_name = $5, taken_at = $6" if claim else ""
    base_params: list[Any] = [new_status, timestamp, admin_name]
    if claim:
        base_params.extend([admin_id, admin_name, timestamp])
    audition_idx = len(base_params) + 1
    audition_sql = f", audition_details = ${audition_idx}" if audition_details is not None else ""
    if audition_details is not None:
        base_params.append(audition_details)
    id_idx = len(base_params) + 1
    status_params_start = len(base_params) + 2
    params = list(base_params)
    params.append(application_id)
    params.extend(expected_statuses)
    status_placeholders = ", ".join(
        f"${status_params_start + i}" for i in range(len(expected_statuses))
    )
    async with connection() as db:
        result = await db.execute(
            f"""
            UPDATE applications
            SET status = $1, status_updated_at = $2, action_by_name = $3
                {claim_sql} {audition_sql}
            WHERE id = ${id_idx} AND status IN ({status_placeholders})
            """,
            *params,
        )
    if result != "UPDATE 1":
        return None
    return await get_application(application_id)


async def add_note(
    application_id: int, admin_id: int, admin_name: str, note_text: str
) -> None:
    async with connection() as db:
        await db.execute(
            """
            INSERT INTO notes (application_id, admin_id, admin_name, note_text, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            application_id,
            admin_id,
            admin_name,
            note_text,
            utc_now(),
        )
        await db.execute(
            "UPDATE applications SET action_by_name = $1 WHERE id = $2",
            admin_name,
            application_id,
        )


async def get_notes(application_id: int) -> list[dict[str, Any]]:
    async with connection() as db:
        rows = await db.fetch(
            "SELECT * FROM notes WHERE application_id = $1 ORDER BY id ASC",
            application_id,
        )
    return [dict(row) for row in rows]


async def list_applications(
    *,
    statuses: tuple[str, ...] | None = None,
    limit: int | None = None,
    before_id: int | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM applications"
    params: list[Any] = []
    conditions = []
    if statuses:
        placeholders = ", ".join(f"${i + 1}" for i in range(len(statuses)))
        conditions.append(f"status IN ({placeholders})")
        params.extend(statuses)
    if before_id is not None:
        params.append(before_id)
        conditions.append(f"id < ${len(params)}")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"
    if limit is not None:
        query += f" LIMIT ${len(params) + 1}"
        params.append(limit)

    async with connection() as db:
        rows = await db.fetch(query, *params)

    result: list[dict[str, Any]] = []
    for row in rows:
        decoded = _decode_application(row)
        if decoded is not None:
            result.append(decoded)
    return result


async def find_applications(name: str, limit: int = 10) -> list[dict[str, Any]]:
    async with connection() as db:
        rows = await db.fetch(
            """
            SELECT * FROM applications
            WHERE full_name ILIKE $1
            ORDER BY id DESC LIMIT $2
            """,
            f"%{name}%",
            limit,
        )

    result: list[dict[str, Any]] = []
    for row in rows:
        decoded = _decode_application(row)
        if decoded is not None:
            result.append(decoded)
    return result


async def all_applications_for_export() -> list[dict[str, Any]]:
    return await list_applications()


async def get_statistics() -> dict[str, Any]:
    async with connection() as db:
        status_rows = await db.fetch(
            "SELECT status, COUNT(*) AS amount FROM applications GROUP BY status"
        )
        statuses = {row["status"]: row["amount"] for row in status_rows}
        position_rows = await db.fetch(
            """
            SELECT primary_position, COUNT(*) AS amount FROM applications
            GROUP BY primary_position ORDER BY amount DESC LIMIT 5
            """
        )
        positions = [dict(row) for row in position_rows]
        birth_rows = await db.fetch("SELECT birth_date FROM applications")

    ages = []
    today = datetime.now(timezone.utc).date()
    for row in birth_rows:
        value = row["birth_date"]
        try:
            birth = datetime.strptime(value, "%d.%m.%Y").date()
            age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            ages.append(age)
        except (TypeError, ValueError):
            continue
    return {
        "total": sum(statuses.values()),
        "statuses": statuses,
        "positions": positions,
        "average_age": round(sum(ages) / len(ages), 1) if ages else None,
    }
