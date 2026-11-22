"""SQLite persistence for applications and coach notes."""

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "pauza.db"
DB_PATH = Path(os.getenv("PAUZA_DB_PATH", str(DEFAULT_DB_PATH)))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@asynccontextmanager
async def connection() -> AsyncIterator[aiosqlite.Connection]:
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


def _dict(row: aiosqlite.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _decode_application(row: aiosqlite.Row | dict[str, Any] | None) -> dict[str, Any] | None:
    item = _dict(row) if row is not None and not isinstance(row, dict) else row
    if not item:
        return None
    for column, key in (("days_json", "days"), ("times_json", "times")):
        try:
            item[key] = json.loads(item.get(column) or "[]")
        except (TypeError, json.JSONDecodeError):
            item[key] = []
    return item


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with connection() as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tg_username TEXT,
                full_name TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                contact TEXT NOT NULL,
                school TEXT NOT NULL DEFAULT 'no',
                school_name TEXT,
                school_years TEXT,
                height_cm INTEGER NOT NULL,
                weight_kg REAL NOT NULL,
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
                taken_by_id INTEGER,
                taken_by_name TEXT,
                taken_at TEXT,
                action_by_name TEXT,
                admin_message_id INTEGER,
                created_at TEXT NOT NULL,
                status_updated_at TEXT NOT NULL,
                audition_details TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_applications_user_status
                ON applications(user_id, status);
            CREATE INDEX IF NOT EXISTS idx_applications_created_at
                ON applications(created_at DESC);
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL,
                admin_id INTEGER NOT NULL,
                admin_name TEXT NOT NULL,
                note_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(application_id) REFERENCES applications(id)
                    ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_notes_application
                ON notes(application_id, created_at);
            """
        )
        await db.commit()


async def application_gate(user_id: int) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    async with connection() as db:
        async with db.execute(
            """
            SELECT id, status FROM applications
            WHERE user_id = ? AND status IN ('new', 'in_progress')
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,),
        ) as cursor:
            active = await cursor.fetchone()
        async with db.execute(
            """
            SELECT status_updated_at FROM applications
            WHERE user_id = ? AND status = 'rejected'
            ORDER BY status_updated_at DESC LIMIT 1
            """,
            (user_id,),
        ) as cursor:
            rejected = await cursor.fetchone()
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
        await db.execute("BEGIN IMMEDIATE")
        async with db.execute(
            """
            SELECT id FROM applications
            WHERE user_id = ? AND status IN ('new', 'in_progress')
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,),
        ) as cursor:
            active = await cursor.fetchone()
        if active:
            await db.rollback()
            return {"ok": False, "reason": "active", "application_id": active["id"]}
        async with db.execute(
            """
            SELECT status_updated_at FROM applications
            WHERE user_id = ? AND status = 'rejected'
            ORDER BY status_updated_at DESC LIMIT 1
            """,
            (user_id,),
        ) as cursor:
            rejected = await cursor.fetchone()
        if rejected:
            try:
                rejected_at = datetime.fromisoformat(rejected["status_updated_at"])
                if rejected_at.tzinfo is None:
                    rejected_at = rejected_at.replace(tzinfo=timezone.utc)
                available_at = rejected_at + timedelta(days=14)
                if now < available_at:
                    await db.rollback()
                    return {"ok": False, "reason": "cooldown", "available_at": available_at}
            except (TypeError, ValueError):
                pass
        values = (
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
        cursor = await db.execute(
            """
            INSERT INTO applications (
                user_id, tg_username, full_name, birth_date, contact, school,
                school_name, school_years, height_cm, weight_kg, primary_position,
                secondary_position, working_foot, level, achievements, video_link,
                days_json, times_json, injuries, injury_details, referral_source,
                about, additional_info, created_at, status_updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        application_id = cursor.lastrowid
        await db.commit()
    return {"ok": True, "application_id": application_id}


async def get_application(application_id: int) -> dict[str, Any] | None:
    async with connection() as db:
        async with db.execute(
            "SELECT * FROM applications WHERE id = ?", (application_id,)
        ) as cursor:
            return _decode_application(await cursor.fetchone())


async def get_latest_application(user_id: int) -> dict[str, Any] | None:
    async with connection() as db:
        async with db.execute(
            "SELECT * FROM applications WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ) as cursor:
            return _decode_application(await cursor.fetchone())


async def set_admin_message_id(application_id: int, message_id: int) -> None:
    async with connection() as db:
        await db.execute(
            "UPDATE applications SET admin_message_id = ? WHERE id = ?",
            (message_id, application_id),
        )
        await db.commit()


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
    placeholders = ",".join("?" for _ in expected_statuses)
    timestamp = utc_now()
    claim_sql = ", taken_by_id = ?, taken_by_name = ?, taken_at = ?" if claim else ""
    audition_sql = ", audition_details = ?" if audition_details is not None else ""
    parameters: list[Any] = [new_status, timestamp, admin_name]
    if claim:
        parameters.extend([admin_id, admin_name, timestamp])
    if audition_details is not None:
        parameters.append(audition_details)
    parameters.extend([application_id, *expected_statuses])
    async with connection() as db:
        cursor = await db.execute(
            f"""
            UPDATE applications
            SET status = ?, status_updated_at = ?, action_by_name = ?
                {claim_sql} {audition_sql}
            WHERE id = ? AND status IN ({placeholders})
            """,
            parameters,
        )
        await db.commit()
        if cursor.rowcount != 1:
            return None
    return await get_application(application_id)


async def add_note(
    application_id: int, admin_id: int, admin_name: str, note_text: str
) -> None:
    async with connection() as db:
        await db.execute(
            """
            INSERT INTO notes (application_id, admin_id, admin_name, note_text, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (application_id, admin_id, admin_name, note_text, utc_now()),
        )
        await db.execute(
            "UPDATE applications SET action_by_name = ? WHERE id = ?",
            (admin_name, application_id),
        )
        await db.commit()


async def get_notes(application_id: int) -> list[dict[str, Any]]:
    async with connection() as db:
        async with db.execute(
            """
            SELECT * FROM notes WHERE application_id = ?
            ORDER BY id ASC
            """,
            (application_id,),
        ) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


async def list_applications(
    *, statuses: tuple[str, ...] | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    query = "SELECT * FROM applications"
    parameters: list[Any] = []
    if statuses:
        query += f" WHERE status IN ({','.join('?' for _ in statuses)})"
        parameters.extend(statuses)
    query += " ORDER BY id DESC"
    if limit is not None:
        query += " LIMIT ?"
        parameters.append(limit)
    async with connection() as db:
        async with db.execute(query, parameters) as cursor:
            return [_decode_application(row) for row in await cursor.fetchall()]


async def find_applications(name: str, limit: int = 10) -> list[dict[str, Any]]:
    needle = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    async with connection() as db:
        async with db.execute(
            """
            SELECT * FROM applications
            WHERE full_name LIKE ? ESCAPE '\\'
            ORDER BY id DESC LIMIT ?
            """,
            (f"%{needle}%", limit),
        ) as cursor:
            return [_decode_application(row) for row in await cursor.fetchall()]


async def all_applications_for_export() -> list[dict[str, Any]]:
    return await list_applications()


async def get_statistics() -> dict[str, Any]:
    async with connection() as db:
        async with db.execute("SELECT status, COUNT(*) AS amount FROM applications GROUP BY status") as cursor:
            statuses = {row["status"]: row["amount"] for row in await cursor.fetchall()}
        async with db.execute(
            """
            SELECT primary_position, COUNT(*) AS amount FROM applications
            GROUP BY primary_position ORDER BY amount DESC LIMIT 5
            """
        ) as cursor:
            positions = [dict(row) for row in await cursor.fetchall()]
        async with db.execute("SELECT birth_date FROM applications") as cursor:
            birth_dates = [row["birth_date"] for row in await cursor.fetchall()]
    ages = []
    today = datetime.now(timezone.utc).date()
    for value in birth_dates:
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
