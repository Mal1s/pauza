import asyncio
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pauza_bot import db
from pauza_bot.keyboards import status_keyboard
from pauza_bot.main import (
    _valid_contact,
    _validate_text,
    age_from_birth_date,
    format_age,
    render_application_card,
    render_review,
)


def application_data() -> dict:
    return {
        "full_name": "Иванов Иван Иванович",
        "birth_date": "12.05.2005",
        "contact": "@ivan_football",
        "school": "yes",
        "school_name": "Динамо, Москва",
        "school_years": "3_5",
        "height_cm": 182,
        "weight_kg": 76.5,
        "primary_position": "forward",
        "secondary_position": "midfielder",
        "working_foot": "right",
        "level": "reserve",
        "achievements": "Кубок города",
        "video_link": "https://example.com/video",
        "days": ["mon", "wed"],
        "times": ["evening"],
        "injuries": "no",
        "injury_details": None,
        "referral_source": "friends",
        "about": "Быстрый и командный",
        "additional_info": "Играю в любительской лиге",
    }


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path = db.DB_PATH
        db.DB_PATH = Path(self.temp_dir.name) / "pauza.db"
        await db.init_db()

    async def asyncTearDown(self) -> None:
        db.DB_PATH = self.old_path
        self.temp_dir.cleanup()

    async def test_active_application_blocks_second_submission(self) -> None:
        first = await db.create_application_if_allowed(123, "ivan", application_data())
        self.assertTrue(first["ok"])
        second = await db.create_application_if_allowed(123, "ivan", application_data())
        self.assertFalse(second["ok"])
        self.assertEqual(second["reason"], "active")
        saved = await db.get_application(first["application_id"])
        self.assertEqual(saved["days"], ["mon", "wed"])
        self.assertEqual(saved["times"], ["evening"])
        self.assertEqual(saved["additional_info"], "Играю в любительской лиге")

    async def test_status_transition_is_atomic_and_claim_is_saved(self) -> None:
        created = await db.create_application_if_allowed(123, "ivan", application_data())
        application_id = created["application_id"]
        updated = await db.update_status(
            application_id,
            ("new",),
            "in_progress",
            77,
            "@coach",
            claim=True,
        )
        self.assertEqual(updated["status"], "in_progress")
        self.assertEqual(updated["taken_by_id"], 77)
        self.assertIsNotNone(updated["taken_at"])
        self.assertIsNone(
            await db.update_status(
                application_id,
                ("new",),
                "rejected",
                88,
                "@other_coach",
            )
        )

    async def test_fourteen_day_cooldown_after_rejection(self) -> None:
        created = await db.create_application_if_allowed(123, "ivan", application_data())
        application_id = created["application_id"]
        await db.update_status(application_id, ("new",), "rejected", 77, "@coach")
        gate = await db.application_gate(123)
        self.assertFalse(gate["allowed"])
        self.assertEqual(gate["reason"], "cooldown")
        async with db.connection() as connection:
            old_date = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
            await connection.execute(
                "UPDATE applications SET status_updated_at = ? WHERE id = ?",
                (old_date, application_id),
            )
            await connection.commit()
        gate = await db.application_gate(123)
        self.assertTrue(gate["allowed"])

    async def test_admin_notes_are_persisted(self) -> None:
        created = await db.create_application_if_allowed(123, "ivan", application_data())
        await db.add_note(created["application_id"], 77, "@coach", "Позвонить вечером")
        notes = await db.get_notes(created["application_id"])
        self.assertEqual(notes[0]["note_text"], "Позвонить вечером")


class ValidationTests(unittest.TestCase):
    def test_contact_formats_are_normalized(self) -> None:
        self.assertEqual(_valid_contact("@ivan_football"), "@ivan_football")
        self.assertEqual(_valid_contact("t.me/ivan_football"), "https://t.me/ivan_football")
        self.assertEqual(_valid_contact("vk.com/ivan.football"), "https://vk.com/ivan.football")
        self.assertIsNone(_valid_contact("https://example.com"))

    def test_birth_date_and_height_validation(self) -> None:
        self.assertIsNotNone(age_from_birth_date("12.05.2005"))
        self.assertFalse(_validate_text("height_cm", "221")[0])
        self.assertTrue(_validate_text("height_cm", "182")[0])
        self.assertFalse(_validate_text("birth_date", "31.02.2005")[0])
        self.assertEqual(format_age(21), "21 год")
        self.assertEqual(format_age(22), "22 года")
        self.assertEqual(format_age(25), "25 лет")

    def test_application_messages_escape_input_and_fit_telegram_limit(self) -> None:
        data = application_data()
        review = render_review({**data, "full_name": "Иванов <тест>"})
        self.assertIn("&lt;тест&gt;", review)
        self.assertIn("Играю в любительской лиге", review)
        self.assertLess(len(review), 4096)

        application = {
            **data,
            "id": 42,
            "user_id": 123,
            "tg_username": "ivan",
            "status": "new",
            "created_at": "2026-01-01T10:00:00+00:00",
            "status_updated_at": "2026-01-01T10:00:00+00:00",
            "taken_by_id": None,
            "taken_by_name": None,
            "taken_at": None,
            "action_by_name": None,
            "admin_message_id": None,
            "audition_details": None,
        }
        notes = [
            {"admin_name": "@coach", "note_text": "x" * 350}
            for _ in range(12)
        ]
        card = render_application_card(application, notes, admin=True)
        self.assertLess(len(card), 4096)
        self.assertIn("Новая заявка #42", card)
        self.assertIn("Играю в любительской лиге", card)

    def test_admin_application_card_has_accept_reject_and_contact_actions(self) -> None:
        keyboard = status_keyboard(
            "new",
            42,
            "https://t.me/ivan_football",
        )
        buttons = [button for row in keyboard.inline_keyboard for button in row]
        self.assertIn("✅ Принять", [button.text for button in buttons])
        self.assertIn("❌ Отказать", [button.text for button in buttons])
        contact_button = next(button for button in buttons if button.url)
        self.assertEqual(contact_button.url, "https://t.me/ivan_football")
        self.assertIn("admin:accept:42", [button.callback_data for button in buttons])


if __name__ == "__main__":
    unittest.main()
