"""Telegram bot for football team PAUZA (webhook on Render / polling on Replit)."""

import asyncio
import csv
import html
import io
import logging
import os
import re
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    ErrorEvent,
    Message,
    ReplyKeyboardRemove,
)

from . import db, keyboards, texts

logger = logging.getLogger("pauza_bot")
router = Router()
MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def _read_admin_chat_id() -> int:
    """ID чата модераторов из переменной окружения (кавычки и пробелы убираем)."""
    raw = os.getenv("ADMIN_CHAT_ID", "").strip().strip("\"'").strip()
    try:
        return int(raw)
    except ValueError:
        return 0


ADMIN_CHAT_ID = _read_admin_chat_id()

TOTAL_STEPS = 15
STEP_ORDER = [
    "full_name",
    "birth_date",
    "contact",
    "school",
    "school_name",
    "school_years",
    "height_cm",
    "weight_kg",
    "primary_position",
    "secondary_position",
    "working_foot",
    "level",
    "achievements",
    "video_link",
    "injuries",
    "injury_details",
    "about",
    "additional_info",
]
PROGRESS_GROUP = {
    "full_name": 1,
    "birth_date": 2,
    "contact": 3,
    "school": 4,
    "school_name": 4,
    "school_years": 4,
    "height_cm": 5,
    "weight_kg": 6,
    "primary_position": 7,
    "secondary_position": 8,
    "working_foot": 9,
    "level": 10,
    "achievements": 11,
    "video_link": 12,
    "injuries": 13,
    "injury_details": 13,
    "about": 14,
    "additional_info": 15,
}
OPTIONAL_STEPS = {"achievements", "video_link", "about", "additional_info"}
POSITION_CODES = {value for _, value in texts.POSITIONS}
NAME_PATTERN = re.compile(
    r"^[^\W\d_]+(?:[-’'][^\W\d_]+)*(?:\s+[^\W\d_]+(?:[-’'][^\W\d_]+)*)+$",
    re.UNICODE,
)
TG_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{5,32}$")
VK_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


class SurveyForm(StatesGroup):
    filling = State()


class AdminInput(StatesGroup):
    appointment = State()
    note = State()
    find = State()


# ----------------------------------------------------------------------------
# Настройки, создание бота, проверка админ-чата
# ----------------------------------------------------------------------------


def load_settings() -> tuple[str, int]:
    token = os.getenv("BOT_TOKEN", "").strip().strip("\"'").strip()
    missing = []
    if not token:
        missing.append("BOT_TOKEN")
    if not ADMIN_CHAT_ID:
        missing.append("ADMIN_CHAT_ID (число, например -1001234567890)")
    if missing:
        raise RuntimeError(
            "Не заданы переменные окружения: "
            + ", ".join(missing)
            + ". Добавь их в Render (Environment) или Replit (Secrets)."
        )
    return token, ADMIN_CHAT_ID


def create_bot(token: str) -> Bot:
    """Бот с HTML-разметкой по умолчанию (все тексты размечены HTML)."""
    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def check_admin_chat(bot: Bot) -> bool:
    """Проверяет доступ к чату модераторов и пишет понятную причину в лог."""
    try:
        chat = await bot.get_chat(ADMIN_CHAT_ID)
        me = await bot.get_me()
        member = await bot.get_chat_member(ADMIN_CHAT_ID, me.id)
        logger.info(
            "Admin chat OK: id=%s title=%r type=%s, bot status=%s",
            ADMIN_CHAT_ID,
            chat.title,
            chat.type,
            member.status,
        )
        if member.status in {"left", "kicked"}:
            logger.error("Бот НЕ состоит в админ-чате (status=%s)", member.status)
            return False
        await bot.send_message(ADMIN_CHAT_ID, "✅ Бот запущен и видит этот чат.")
        return True
    except TelegramAPIError as exc:
        logger.error(
            "ADMIN CHAT CHECK FAILED (ADMIN_CHAT_ID=%s): %s", ADMIN_CHAT_ID, exc
        )
        return False


# ----------------------------------------------------------------------------
# Форматирование
# ----------------------------------------------------------------------------


def _esc(value: Any, default: str | None = None) -> str:
    if value is None or value == "":
        value = default if default is not None else texts.UNKNOWN_VALUE
    return html.escape(str(value), quote=True)


def progress_bar(step: int, total: int = TOTAL_STEPS) -> str:
    filled = round(10 * step / total)
    return "▰" * filled + "▱" * (10 - filled)


def age_from_birth_date(value: str) -> int | None:
    try:
        birth = datetime.strptime(value, "%d.%m.%Y").date()
    except (TypeError, ValueError):
        return None
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def format_age(age: int) -> str:
    last_two = age % 100
    last_digit = age % 10
    if 11 <= last_two <= 14:
        unit = texts.AGE_WORD_LET
    elif last_digit == 1:
        unit = texts.AGE_WORD_YEAR
    elif 2 <= last_digit <= 4:
        unit = texts.AGE_WORD_YEARS
    else:
        unit = texts.AGE_WORD_LET
    return f"{age} {unit}"


def format_datetime(value: str | None) -> str:
    if not value:
        return texts.UNKNOWN_VALUE
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        return value


def format_weight(value: Any) -> str:
    if value is None:
        return texts.UNKNOWN_VALUE
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def format_days(days: list[str]) -> str:
    return ", ".join(texts.DAY_NAMES[day] for day in texts.DAY_NAMES if day in days) or texts.UNKNOWN_VALUE


def format_times(times: list[str]) -> str:
    return ", ".join(texts.TIME_NAMES[time] for time in texts.TIME_NAMES if time in times) or texts.UNKNOWN_VALUE


def format_school_years(code: str | None) -> str:
    return texts.SCHOOL_YEAR_NAMES.get(code, code or texts.UNKNOWN_VALUE)


def format_position(code: str | None) -> str:
    return texts.POSITION_NAMES.get(code, code or texts.UNKNOWN_VALUE)


def format_foot(code: str | None) -> str:
    return texts.FOOT_NAMES.get(code, code or texts.UNKNOWN_VALUE)


def format_level(code: str | None) -> str:
    return texts.LEVEL_NAMES.get(code, code or texts.UNKNOWN_VALUE)


def format_source(code: str | None) -> str:
    return texts.SOURCE_NAMES.get(code, code or texts.UNKNOWN_VALUE)


def progress_header(step: str) -> str:
    index = PROGRESS_GROUP.get(step, 1)
    return (
        f"{texts.BRAND}\n{texts.SEPARATOR}\n"
        + texts.STEP_PROGRESS.format(
            step=index,
            total=TOTAL_STEPS,
            bar=progress_bar(index),
        )
    )


def render_question(step: str, data: dict[str, Any], error: str | None = None) -> str:
    question = texts.QUESTIONS.get(step, texts.UNEXPECTED_TEXT)
    if step == "contact":
        question = (
            texts.CONTACT_AUTO_PROMPT.format(username=_esc(data["contact_username"]))
            if data.get("contact_username")
            else texts.CONTACT_MANUAL_PROMPT
        )
    body = f"{progress_header(step)}\n\n{question}"
    if data.get("flash"):
        body += f"\n\n{_esc(data['flash'])}"
    if error:
        body += f"\n\n{texts.VALIDATION_PREFIX}{_esc(error)}"
    return body


def render_review(data: dict[str, Any]) -> str:
    birth_date = data.get("birth_date")
    age = age_from_birth_date(birth_date) if birth_date else None
    birth_line = _esc(birth_date)
    if age is not None:
        birth_line += texts.AGE_IN_BIRTH_LINE.format(age=_esc(format_age(age)))
    school = texts.SCHOOL_NOT_ATTENDED
    if data.get("school") == "yes":
        school = texts.SCHOOL_ATTENDED.format(
            school=_esc(data.get("school_name")),
            years=_esc(format_school_years(data.get("school_years"))),
        )
    secondary = data.get("secondary_position")
    secondary_text = (
        texts.SECONDARY_NONE if secondary == "none" else format_position(secondary)
    )
    injury_text = texts.INJURY_NONE
    if data.get("injuries") == "yes":
        injury_text = texts.INJURY_PRESENT.format(
            details=_esc(data.get("injury_details"))
        )
    return texts.REVIEW_TEMPLATE.format(
        title=texts.REVIEW_TITLE,
        separator=texts.SEPARATOR,
        full_name=_esc(data.get("full_name")),
        birth_line=birth_line,
        contact=_esc(data.get("contact")),
        height=_esc(data.get("height_cm")),
        weight=_esc(format_weight(data.get("weight_kg"))),
        foot=_esc(format_foot(data.get("working_foot"))),
        position=_esc(format_position(data.get("primary_position"))),
        secondary=_esc(secondary_text),
        level=_esc(format_level(data.get("level"))),
        school=school,
        achievements=_esc(data.get("achievements")),
        video=_esc(data.get("video_link")),
        injury=injury_text,
        about=_esc(data.get("about")),
        additional_info=_esc(data.get("additional_info")),
        help=texts.REVIEW_HELP,
    )


def admin_contact_url(application: dict[str, Any]) -> str | None:
    contact = (application.get("contact") or "").strip()
    if contact.startswith("@"):
        username = contact[1:]
        if TG_NAME_PATTERN.fullmatch(username):
            return f"https://t.me/{username}"
    if contact.startswith("https://t.me/"):
        return contact
    if application.get("tg_username"):
        return f"https://t.me/{application['tg_username']}"
    user_id = application.get("user_id")
    return f"tg://user?id={user_id}" if user_id else None


def render_application_card(
    application: dict[str, Any],
    notes: list[dict[str, Any]],
    *,
    admin: bool,
) -> str:
    age = age_from_birth_date(application.get("birth_date", ""))
    birth_line = _esc(application.get("birth_date"))
    if age is not None:
        birth_line += texts.AGE_IN_BIRTH_LINE.format(age=_esc(format_age(age)))
    school = texts.SCHOOL_NOT_ATTENDED
    if application.get("school") == "yes":
        school = texts.SCHOOL_ATTENDED.format(
            school=_esc(application.get("school_name")),
            years=_esc(format_school_years(application.get("school_years"))),
        )
    secondary = application.get("secondary_position")
    secondary_text = (
        texts.SECONDARY_NONE if secondary == "none" else format_position(secondary)
    )
    injury = texts.INJURY_NONE
    if application.get("injuries") == "yes":
        injury = texts.INJURY_PRESENT.format(
            details=_esc(application.get("injury_details"))
        )
    status = application.get("status", "new")
    status_emoji = texts.STATUS_EMOJI.get(status, texts.UNKNOWN_STATUS_EMOJI)
    status_label = texts.STATUS_LABEL.get(status, status)
    title = (
        texts.NEW_APPLICATION_ADMIN.format(application_id=application["id"])
        if admin and status == "new"
        else texts.APPLICATION_TITLE.format(application_id=application["id"])
    )
    lines = [
        title,
        texts.SEPARATOR,
        texts.APPLICATION_NAME.format(name=_esc(application.get("full_name"))),
        texts.APPLICATION_BIRTH.format(birth_line=birth_line),
        texts.APPLICATION_CONTACT.format(contact=_esc(application.get("contact"))),
        texts.SEPARATOR,
        texts.APPLICATION_MEASUREMENTS.format(
            height=_esc(application.get("height_cm")),
            weight=_esc(format_weight(application.get("weight_kg"))),
        ),
        texts.APPLICATION_FOOT.format(
            foot=_esc(format_foot(application.get("working_foot")))
        ),
        texts.APPLICATION_POSITION.format(
            position=_esc(format_position(application.get("primary_position"))),
            secondary=_esc(secondary_text),
        ),
        texts.APPLICATION_LEVEL.format(level=_esc(format_level(application.get("level")))),
        texts.APPLICATION_SCHOOL.format(school=school),
        texts.APPLICATION_ACHIEVEMENTS.format(
            achievements=_esc(application.get("achievements"))
        ),
        texts.APPLICATION_VIDEO.format(video=_esc(application.get("video_link"))),
        texts.SEPARATOR,
        texts.APPLICATION_INJURY.format(injury=injury),
        texts.APPLICATION_ABOUT.format(about=_esc(application.get("about"))),
        texts.APPLICATION_ADDITIONAL_INFO.format(
            additional_info=_esc(application.get("additional_info"))
        ),
    ]
    if admin:
        lines.extend(
            [
                texts.SEPARATOR,
                texts.STATUS_ADMIN.format(
                    emoji=status_emoji,
                    status=_esc(status_label),
                ),
            ]
        )
        if application.get("taken_by_name"):
            lines.append(
                texts.CLAIM_ADMIN.format(
                    admin=_esc(application["taken_by_name"]),
                    when=_esc(format_datetime(application.get("taken_at"))),
                )
            )
        elif application.get("action_by_name"):
            lines.append(
                texts.ACTION_ADMIN.format(
                    admin=_esc(application["action_by_name"]),
                    when=_esc(format_datetime(application.get("status_updated_at"))),
                )
            )
        if application.get("audition_details"):
            lines.append(
                texts.AUDITION_ADMIN.format(details=_esc(application["audition_details"]))
            )
        if notes:
            lines.append(texts.SEPARATOR)
            earlier = len(notes) - 4
            if earlier > 0:
                lines.append(texts.EARLIER_NOTES.format(count=earlier))
            for note in notes[-4:]:
                note_text = str(note["note_text"])
                if len(note_text) > 250:
                    note_text = note_text[:247] + "…"
                lines.append(
                    texts.NOTE_ADMIN.format(
                        admin=_esc(note["admin_name"]),
                        note=_esc(note_text),
                    )
                )
    else:
        lines.extend(
            [
                texts.SEPARATOR,
                texts.MY_APPLICATION_STATUS.format(
                    emoji=status_emoji,
                    status=_esc(status_label),
                    message=_esc(texts.STATUS_LINES.get(status, "")),
                ),
            ]
        )
        if application.get("audition_details"):
            lines.append(
                texts.MY_APPLICATION_APPOINTMENT.format(
                    details=_esc(application["audition_details"])
                )
            )
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# Экран анкеты
# ----------------------------------------------------------------------------


async def _edit_screen(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    *,
    error: str | None = None,
) -> None:
    data = await state.get_data()
    message_id = data.get("screen_message_id")
    if not message_id:
        return
    view = data.get("view", "form")
    if view == "review":
        text = render_review(data)
        markup = keyboards.review_keyboard()
    elif view == "edit_list":
        text = f"{texts.BRAND}\n{texts.SEPARATOR}\n<b>{texts.EDIT_TITLE}</b>"
        markup = keyboards.edit_fields_keyboard()
    elif view == "cancel":
        text = f"{progress_header(data.get('step', 'full_name'))}\n\n{texts.SURVEY_CANCEL_CONFIRM}"
        markup = keyboards.cancel_confirm_keyboard()
    else:
        step = data.get("step", "full_name")
        text = render_question(step, data, error)
        markup = keyboards.survey_keyboard(step, data)
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=markup,
        )
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            logger.warning("Could not update survey message: %s", exc)


def _next_step(step: str, data: dict[str, Any]) -> str | None:
    try:
        index = STEP_ORDER.index(step) + 1
    except ValueError:
        return None
    while index < len(STEP_ORDER):
        candidate = STEP_ORDER[index]
        if candidate in {"school_name", "school_years"} and data.get("school") != "yes":
            index += 1
            continue
        if candidate == "injury_details" and data.get("injuries") != "yes":
            index += 1
            continue
        return candidate
    return None


def _previous_step(step: str, data: dict[str, Any]) -> str | None:
    try:
        index = STEP_ORDER.index(step) - 1
    except ValueError:
        return None
    while index >= 0:
        candidate = STEP_ORDER[index]
        if candidate in {"school_name", "school_years"} and data.get("school") != "yes":
            index -= 1
            continue
        if candidate == "injury_details" and data.get("injuries") != "yes":
            index -= 1
            continue
        return candidate
    return None


async def _show_review(bot: Bot, chat_id: int, state: FSMContext) -> None:
    await state.update_data(view="review", flash=None, cancel_pending=False)
    await _edit_screen(bot, chat_id, state)


async def _continue_after_answer(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    step: str,
    *,
    flash: str | None = None,
) -> None:
    data = await state.get_data()
    editing = data.get("editing", False)
    edit_parent = data.get("edit_parent")
    if editing:
        if edit_parent == "school":
            if step == "school" and data.get("school") == "yes":
                next_step = "school_name"
            elif step == "school_name":
                next_step = "school_years"
            else:
                await state.update_data(editing=False, edit_parent=None)
                await _show_review(bot, chat_id, state)
                return
            await state.update_data(step=next_step, view="form", flash=None)
            await _edit_screen(bot, chat_id, state)
            return
        if edit_parent == "injuries":
            if step == "injuries" and data.get("injuries") == "yes":
                await state.update_data(step="injury_details", view="form", flash=None)
                await _edit_screen(bot, chat_id, state)
                return
            await state.update_data(editing=False, edit_parent=None)
            await _show_review(bot, chat_id, state)
            return
        await state.update_data(editing=False, edit_parent=None)
        await _show_review(bot, chat_id, state)
        return

    next_step = _next_step(step, data)
    if next_step is None:
        await _show_review(bot, chat_id, state)
    else:
        await state.update_data(
            step=next_step,
            view="form",
            flash=flash,
            cancel_pending=False,
        )
        await _edit_screen(bot, chat_id, state)


def _valid_contact(raw: str) -> str | None:
    value = raw.strip()
    if value.startswith("@"):
        username = value[1:]
        return f"@{username}" if TG_NAME_PATTERN.fullmatch(username) else None
    normalized = value if "://" in value else f"https://{value}"
    try:
        parsed = urlsplit(normalized)
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    path = parsed.path.strip("/").split("/", 1)[0]
    if host in {"t.me", "www.t.me"} and TG_NAME_PATTERN.fullmatch(path):
        return f"https://t.me/{path}"
    if host in {"vk.com", "www.vk.com"} and VK_NAME_PATTERN.fullmatch(path):
        return f"https://vk.com/{path}"
    return None


def _validate_text(step: str, raw: str) -> tuple[bool, Any, str | None, str | None]:
    value = raw.strip()
    if step == "full_name":
        if len(value) <= 100 and NAME_PATTERN.fullmatch(value):
            return True, re.sub(r"\s+", " ", value), None, None
        return False, None, texts.ERRORS["full_name"], None
    if step == "birth_date":
        try:
            parsed = datetime.strptime(value, "%d.%m.%Y").date()
            if parsed.strftime("%d.%m.%Y") != value:
                raise ValueError("date format")
            age = age_from_birth_date(value)
            if parsed > date.today() or age is None or not 10 <= age <= 50:
                raise ValueError("age")
            return True, value, None, texts.AGE_FLASH.format(age=_esc(format_age(age)))
        except ValueError:
            return False, None, texts.ERRORS["birth_date"], None
    if step == "contact":
        contact = _valid_contact(value)
        if contact:
            return True, contact, None, None
        return False, None, texts.ERRORS["contact"], None
    if step == "school_name":
        if value and len(value) <= 160:
            return True, value, None, None
        return False, None, texts.ERRORS["school_name"], None
    if step == "height_cm":
        if value.isdigit() and 120 <= int(value) <= 220:
            return True, int(value), None, None
        return False, None, texts.ERRORS["height_cm"], None
    if step == "weight_kg":
        if re.fullmatch(r"\d{1,3}(?:[.,]\d)?", value):
            weight = float(value.replace(",", "."))
            if 30 <= weight <= 150:
                return True, weight, None, None
        return False, None, texts.ERRORS["weight_kg"], None
    if step == "achievements":
        if len(value) <= 500:
            return True, value or None, None, None
        return False, None, texts.ERRORS["achievements"], None
    if step == "video_link":
        if not value:
            return True, None, None, None
        try:
            parsed = urlsplit(value)
            if len(value) <= 300 and parsed.scheme in {"http", "https"} and parsed.netloc:
                return True, value, None, None
        except ValueError:
            pass
        return False, None, texts.ERRORS["video_link"], None
    if step == "injury_details":
        if value and len(value) <= 300:
            return True, value, None, None
        return False, None, texts.ERRORS["injury_details"], None
    if step == "about":
        if len(value) <= 150:
            return True, value or None, None, None
        return False, None, texts.ERRORS["about"], None
    if step == "additional_info":
        if len(value) <= 500:
            return True, value or None, None, None
        return False, None, texts.ERRORS["additional_info"], None
    return False, None, texts.UNEXPECTED_TEXT, None


async def _save_answer(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    step: str,
    value: Any,
    *,
    flash: str | None = None,
) -> None:
    patch: dict[str, Any] = {step: value, "flash": None, "view": "form"}
    if step == "school" and value == "no":
        patch.update(school_name=None, school_years=None)
    if step == "injuries" and value == "no":
        patch["injury_details"] = None
    if step == "contact":
        patch["contact_username"] = None
    await state.update_data(**patch)
    await _continue_after_answer(bot, chat_id, state, step, flash=flash)


async def _delete_message(message: Message) -> None:
    try:
        await message.delete()
    except TelegramAPIError as exc:
        logger.debug("Could not delete processed message: %s", exc)
    except Exception:
        logger.exception("Unexpected error while deleting a processed message")


async def _send_status_to_player(bot: Bot, user_id: int, text: str) -> None:
    try:
        await bot.send_message(user_id, text)
    except TelegramAPIError as exc:
        logger.warning("Could not send private status message to user %s: %s", user_id, exc)


# ----------------------------------------------------------------------------
# Карточка заявки в чате модераторов
# ----------------------------------------------------------------------------


async def _admin_card_text(application_id: int) -> tuple[dict[str, Any], str]:
    application = await db.get_application(application_id)
    if not application:
        raise LookupError(f"Application {application_id} is missing")
    notes = await db.get_notes(application_id)
    return application, render_application_card(application, notes, admin=True)


def _admin_markup(application: dict[str, Any], contact_url: str | None):
    return keyboards.status_keyboard(
        application["status"], application["id"], contact_url
    )


async def _send_card(
    bot: Bot, application: dict[str, Any], card_text: str
) -> Message:
    """Отправляет карточку. Если Telegram не принял кнопку-ссылку, шлёт без неё."""
    url = admin_contact_url(application)
    try:
        return await bot.send_message(
            ADMIN_CHAT_ID, card_text, reply_markup=_admin_markup(application, url)
        )
    except TelegramBadRequest as exc:
        logger.warning(
            "Card #%s rejected with contact button (%s), retrying without it",
            application["id"],
            exc,
        )
        return await bot.send_message(
            ADMIN_CHAT_ID, card_text, reply_markup=_admin_markup(application, None)
        )


async def _edit_card(
    bot: Bot, message_id: int, application: dict[str, Any], card_text: str
) -> None:
    url = admin_contact_url(application)
    try:
        await bot.edit_message_text(
            chat_id=ADMIN_CHAT_ID,
            message_id=message_id,
            text=card_text,
            reply_markup=_admin_markup(application, url),
        )
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        if "message to edit not found" in str(exc).lower():
            raise
        logger.warning(
            "Edit card #%s failed with button (%s), retrying without it",
            application["id"],
            exc,
        )
        await bot.edit_message_text(
            chat_id=ADMIN_CHAT_ID,
            message_id=message_id,
            text=card_text,
            reply_markup=_admin_markup(application, None),
        )


async def _refresh_admin_card(bot: Bot, application_id: int) -> None:
    try:
        application, card_text = await _admin_card_text(application_id)
    except LookupError:
        logger.warning("Application %s is missing while refreshing its card", application_id)
        return
    message_id = application.get("admin_message_id")
    if message_id:
        try:
            await _edit_card(bot, message_id, application, card_text)
            return
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return
            logger.warning("Could not edit admin card #%s: %s", application_id, exc)
        except TelegramAPIError as exc:
            logger.warning("Could not edit admin card #%s: %s", application_id, exc)
            return
    try:
        sent = await _send_card(bot, application, card_text)
        await db.set_admin_message_id(application_id, sent.message_id)
    except TelegramAPIError:
        logger.exception("Could not send admin card #%s", application_id)


async def _application_card_to_admin(bot: Bot, application_id: int) -> bool:
    try:
        application, card_text = await _admin_card_text(application_id)
    except LookupError:
        logger.error("Application %s not found in DB right after creating", application_id)
        return False
    except Exception:
        logger.exception("DB error while loading application #%s", application_id)
        return False
    try:
        message = await _send_card(bot, application, card_text)
        await db.set_admin_message_id(application_id, message.message_id)
        return True
    except TelegramAPIError:
        logger.exception(
            "Could not deliver application #%s to admin chat (ADMIN_CHAT_ID=%s)",
            application_id,
            ADMIN_CHAT_ID,
        )
        return False
    except Exception:
        logger.exception("Unexpected error delivering application #%s", application_id)
        return False


# ----------------------------------------------------------------------------
# Главное меню и анкета
# ----------------------------------------------------------------------------


async def _handle_home_apply(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not callback.message or callback.message.chat.type != ChatType.PRIVATE:
        await callback.answer()
        return
    gate = await db.application_gate(callback.from_user.id)
    if not gate["allowed"]:
        message = texts.ACTIVE_APPLICATION if gate["reason"] == "active" else texts.COOLDOWN_APPLICATION
        await callback.message.edit_text(message, reply_markup=keyboards.home_keyboard())
        await callback.answer()
        return
    await state.clear()
    await state.set_state(SurveyForm.filling)
    await state.update_data(
        screen_message_id=callback.message.message_id,
        step="full_name",
        view="form",
        editing=False,
        contact_username=callback.from_user.username,
        flash=None,
    )
    await _edit_screen(bot, callback.message.chat.id, state)
    await callback.answer()


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    await state.clear()
    await message.answer(texts.WELCOME, reply_markup=keyboards.home_keyboard())


@router.callback_query(F.data.startswith("home:"))
async def home_callback(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not callback.message or callback.message.chat.type != ChatType.PRIVATE:
        await callback.answer()
        return
    action = (callback.data or "").split(":", 1)[1]
    if action == "apply":
        await _handle_home_apply(callback, state, bot)
        return
    await state.clear()
    if action == "about":
        await callback.message.edit_text(
            texts.ABOUT_TEAM,
            reply_markup=keyboards.home_keyboard(),
        )
        await callback.answer()
        return
    if action == "mine":
        application = await db.get_latest_application(callback.from_user.id)
        if not application:
            response = texts.NO_APPLICATION
        else:
            response = render_application_card(application, [], admin=False)
        await callback.message.edit_text(
            response,
            reply_markup=keyboards.home_keyboard(),
        )
        await callback.answer()
        return
    await callback.answer()


@router.callback_query(F.data == "survey:cancel")
async def survey_cancel_prompt(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if await state.get_state() != SurveyForm.filling.state:
        await callback.answer(texts.UNEXPECTED_TEXT, show_alert=True)
        return
    data = await state.get_data()
    await state.update_data(
        view="cancel",
        cancel_pending=True,
        cancel_previous_view=data.get("view", "form"),
    )
    if callback.message:
        await _edit_screen(bot, callback.message.chat.id, state)
    await callback.answer()


@router.callback_query(F.data.startswith("survey:cancel:"))
async def survey_cancel_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    action = (callback.data or "").rsplit(":", 1)[-1]
    if action == "yes":
        await state.clear()
        if callback.message:
            await callback.message.edit_text(
                texts.CANCELLED,
                reply_markup=keyboards.home_keyboard(),
            )
        await callback.answer()
        return
    if action == "no":
        data = await state.get_data()
        view = data.get("cancel_previous_view", "form")
        await state.update_data(view=view, cancel_pending=False)
        if callback.message:
            await _edit_screen(bot, callback.message.chat.id, state)
        await callback.answer()
        return
    await callback.answer()


@router.callback_query(F.data == "survey:edit:list")
async def survey_edit_list(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if await state.get_state() != SurveyForm.filling.state:
        await callback.answer(texts.UNEXPECTED_TEXT, show_alert=True)
        return
    await state.update_data(view="edit_list", editing=False)
    if callback.message:
        await _edit_screen(bot, callback.message.chat.id, state)
    await callback.answer()


@router.callback_query(F.data.startswith("survey:edit:"))
async def survey_edit_field(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    field = (callback.data or "").split(":", 2)[-1]
    if field == "back":
        await state.update_data(view="review", editing=False)
        if callback.message:
            await _edit_screen(bot, callback.message.chat.id, state)
        await callback.answer()
        return
    if field not in texts.FIELD_NAMES:
        await callback.answer(texts.UNEXPECTED_TEXT, show_alert=True)
        return
    await state.update_data(
        step=field,
        view="form",
        editing=True,
        edit_parent=field,
        flash=None,
        contact_username=None,
    )
    if callback.message:
        await _edit_screen(bot, callback.message.chat.id, state)
    await callback.answer()


@router.callback_query(F.data == "survey:back")
async def survey_back(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    if data.get("editing"):
        await state.update_data(editing=False, edit_parent=None, view="review")
        if callback.message:
            await _edit_screen(bot, callback.message.chat.id, state)
        await callback.answer()
        return
    previous = _previous_step(data.get("step", ""), data)
    if previous:
        await state.update_data(step=previous, view="form", flash=None)
    if callback.message:
        await _edit_screen(bot, callback.message.chat.id, state)
    await callback.answer()


@router.callback_query(F.data == "survey:contact:yes")
async def survey_contact_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    username = data.get("contact_username")
    if not username or not callback.message:
        await callback.answer(texts.UNEXPECTED_TEXT, show_alert=True)
        return
    await _save_answer(bot, callback.message.chat.id, state, "contact", f"@{username}")
    await callback.answer()


@router.callback_query(F.data == "survey:contact:no")
async def survey_contact_other(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await state.update_data(contact_username=None, flash=None)
    if callback.message:
        await _edit_screen(bot, callback.message.chat.id, state)
    await callback.answer()


@router.callback_query(F.data.startswith("survey:choose:"))
async def survey_choose(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    parts = (callback.data or "").split(":", 3)
    if len(parts) != 4 or not callback.message:
        await callback.answer(texts.UNEXPECTED_TEXT, show_alert=True)
        return
    _, _, step, value = parts
    data = await state.get_data()
    if step != data.get("step"):
        await callback.answer(texts.UNEXPECTED_TEXT, show_alert=True)
        return
    allowed: dict[str, set[str]] = {
        "school": {"yes", "no"},
        "school_years": {value for _, value in texts.SCHOOL_YEARS},
        "primary_position": POSITION_CODES,
        "secondary_position": POSITION_CODES | {"none"},
        "working_foot": {value for _, value in texts.FEET},
        "level": {value for _, value in texts.LEVELS},
        "injuries": {"yes", "no"},
    }
    if value not in allowed.get(step, set()):
        await callback.answer(texts.UNEXPECTED_TEXT, show_alert=True)
        return
    if step == "secondary_position" and value == data.get("primary_position"):
        await callback.answer(texts.SECONDARY_SAME_ERROR, show_alert=True)
        return
    await _save_answer(bot, callback.message.chat.id, state, step, value)
    await callback.answer()


@router.callback_query(F.data == "survey:skip")
async def survey_skip(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    step = data.get("step")
    if step not in OPTIONAL_STEPS or not callback.message:
        await callback.answer(texts.UNEXPECTED_TEXT, show_alert=True)
        return
    await _save_answer(bot, callback.message.chat.id, state, step, None)
    await callback.answer()


@router.callback_query(F.data == "survey:submit")
async def survey_submit(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    if data.get("view") != "review" or await state.get_state() != SurveyForm.filling.state:
        await callback.answer(texts.UNEXPECTED_TEXT, show_alert=True)
        return
    if data.get("submitting"):
        await callback.answer(texts.ADMIN_ALREADY_PROCESSED, show_alert=True)
        return
    await state.update_data(submitting=True)
    try:
        result = await db.create_application_if_allowed(
            callback.from_user.id,
            callback.from_user.username,
            data,
        )
    except Exception:
        logger.exception("DB error while creating application")
        await state.update_data(submitting=False)
        await callback.answer(
            "Не удалось сохранить заявку. Попробуй ещё раз через минуту.",
            show_alert=True,
        )
        return
    if not result["ok"]:
        await state.clear()
        text = texts.ACTIVE_APPLICATION if result["reason"] == "active" else texts.COOLDOWN_APPLICATION
        if callback.message:
            await callback.message.edit_text(text, reply_markup=keyboards.home_keyboard())
        await callback.answer()
        return
    application_id = result["application_id"]
    delivered = await _application_card_to_admin(bot, application_id)
    await state.clear()
    if callback.message:
        await callback.message.edit_text(
            texts.APPLICATION_SENT if delivered else texts.APPLICATION_SENT_ADMIN_ERROR,
            reply_markup=keyboards.home_keyboard(),
        )
    await callback.answer()


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext, bot: Bot) -> None:
    current_state = await state.get_state()
    await _delete_message(message)
    if current_state == SurveyForm.filling.state:
        data = await state.get_data()
        screen_message_id = data.get("screen_message_id")
        await state.clear()
        if screen_message_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=screen_message_id,
                    text=texts.CANCELLED,
                    reply_markup=keyboards.home_keyboard(),
                )
            except TelegramBadRequest:
                pass
    elif current_state in {
        AdminInput.appointment.state,
        AdminInput.note.state,
        AdminInput.find.state,
    }:
        data = await state.get_data()
        prompt_id = data.get("prompt_message_id")
        await state.clear()
        if prompt_id:
            try:
                await bot.delete_message(message.chat.id, prompt_id)
            except TelegramBadRequest:
                pass
        await message.answer(texts.ACTION_CANCELLED)


@router.message(SurveyForm.filling, F.text)
async def survey_text_input(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    data = await state.get_data()
    if data.get("view") == "cancel":
        await _delete_message(message)
        await _edit_screen(bot, message.chat.id, state, error=texts.UNEXPECTED_TEXT)
        return
    step = data.get("step", "full_name")
    if step not in {
        "full_name",
        "birth_date",
        "contact",
        "school_name",
        "height_cm",
        "weight_kg",
        "achievements",
        "video_link",
        "injury_details",
        "about",
        "additional_info",
    }:
        await _delete_message(message)
        await _edit_screen(bot, message.chat.id, state, error=texts.UNEXPECTED_TEXT)
        return
    valid, value, error, flash = _validate_text(step, message.text or "")
    await _delete_message(message)
    if not valid:
        await _edit_screen(bot, message.chat.id, state, error=error)
        return
    await _save_answer(bot, message.chat.id, state, step, value, flash=flash)


@router.message(SurveyForm.filling)
async def survey_non_text_input(message: Message, state: FSMContext, bot: Bot) -> None:
    await _delete_message(message)
    if message.chat.type == ChatType.PRIVATE:
        await _edit_screen(bot, message.chat.id, state, error=texts.UNEXPECTED_TEXT)


# ----------------------------------------------------------------------------
# Админ-чат
# ----------------------------------------------------------------------------


def _admin_name(message_or_user: Any) -> str:
    user = getattr(message_or_user, "from_user", None)
    if user is None:
        return texts.COACH_DEFAULT_NAME
    return f"@{user.username}" if user.username else user.full_name


def _is_admin_chat(chat_id: int) -> bool:
    return chat_id == ADMIN_CHAT_ID


@router.callback_query(F.data.startswith("admin:"))
async def admin_action(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    message = callback.message
    if not isinstance(message, Message) or message.chat.id != ADMIN_CHAT_ID:
        await callback.answer(texts.ADMIN_ONLY_ACTION, show_alert=True)
        return
    parts = (callback.data or "").split(":")
    if len(parts) < 3:
        await callback.answer(texts.ADMIN_ALREADY_PROCESSED, show_alert=True)
        return
    action = parts[1]
    actor_id = callback.from_user.id
    actor_name = _admin_name(callback)
    if action == "menu":
        if len(parts) != 3:
            await callback.answer(texts.ADMIN_MENU_UNKNOWN_ACTION, show_alert=True)
            return
        menu_action = parts[2]
        if menu_action == "find":
            await state.clear()
            await state.set_state(AdminInput.find)
            prompt = await message.answer(texts.ADMIN_FIND_PROMPT)
            await state.update_data(
                admin_chat_id=message.chat.id,
                prompt_message_id=prompt.message_id,
            )
            await callback.answer()
            return
        await state.clear()
        await callback.answer()
        if menu_action == "new":
            await _show_new_applications(message)
        elif menu_action == "stats":
            await admin_stats_command(message)
        elif menu_action == "export":
            await admin_export_command(message)
        elif menu_action == "help":
            await admin_help_command(message)
        else:
            await message.answer(texts.ADMIN_MENU_UNKNOWN_ACTION)
        return
    if action in {"new_page", "open_new"}:
        if len(parts) != 3 or not parts[2].isascii() or not parts[2].isdecimal():
            await callback.answer(texts.ADMIN_NOT_FOUND, show_alert=True)
            return
        application_id = int(parts[2])
        if action == "new_page":
            await callback.answer()
            await _show_new_applications(message, before_id=application_id or None, edit=True)
            return
        application = await db.get_application(application_id)
        if not application or application["status"] != "new":
            await callback.answer(texts.ADMIN_ALREADY_PROCESSED, show_alert=True)
            return
        await callback.answer()
        previous_message_id = application.get("admin_message_id")
        if not await _application_card_to_admin(bot, application_id):
            await message.answer(texts.ADMIN_NEW_OPEN_FAILED)
            return
        if previous_message_id:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=ADMIN_CHAT_ID, message_id=previous_message_id
                )
            except TelegramAPIError as exc:
                logger.debug("Could not clear previous card #%s: %s", application_id, exc)
        return
    if action == "reject" and len(parts) == 3:
        try:
            application_id = int(parts[2])
        except ValueError:
            await callback.answer(texts.ADMIN_NOT_FOUND, show_alert=True)
            return
        application = await db.get_application(application_id)
        if not application or application["status"] not in {"new", "in_progress", "reserve"}:
            await callback.answer(texts.ADMIN_ALREADY_PROCESSED, show_alert=True)
            return
        await message.edit_reply_markup(
            reply_markup=keyboards.reject_confirmation_keyboard(application_id)
        )
        await callback.answer()
        return
    if action == "reject" and len(parts) == 4:
        try:
            application_id = int(parts[3])
        except ValueError:
            await callback.answer(texts.ADMIN_NOT_FOUND, show_alert=True)
            return
        confirmation = parts[2]
        if confirmation == "no":
            await _refresh_admin_card(bot, application_id)
            await callback.answer()
            return
        if confirmation != "yes":
            await callback.answer(texts.ADMIN_ALREADY_PROCESSED, show_alert=True)
            return
        application = await db.update_status(
            application_id,
            ("new", "in_progress", "reserve"),
            "rejected",
            actor_id,
            actor_name,
        )
        if not application:
            await callback.answer(texts.ADMIN_ALREADY_PROCESSED, show_alert=True)
            return
        await _send_status_to_player(bot, application["user_id"], texts.REJECTION_TO_PLAYER)
        await _refresh_admin_card(bot, application_id)
        await callback.answer(texts.ADMIN_REJECTION_SAVED)
        return
    try:
        application_id = int(parts[-1])
    except ValueError:
        await callback.answer(texts.ADMIN_NOT_FOUND, show_alert=True)
        return
    application = await db.get_application(application_id)
    if not application:
        await callback.answer(texts.ADMIN_NOT_FOUND, show_alert=True)
        return
    if action == "accept":
        updated = await db.update_status(
            application_id,
            ("new", "reserve"),
            "in_progress",
            actor_id,
            actor_name,
            claim=True,
        )
        if not updated:
            await callback.answer(texts.ADMIN_ALREADY_PROCESSED, show_alert=True)
            return
        await _refresh_admin_card(bot, application_id)
        await state.set_state(AdminInput.appointment)
        await state.update_data(
            application_id=application_id,
            prompt_message_id=None,
            admin_chat_id=message.chat.id,
        )
        prompt = await message.answer(
            texts.ADMIN_ASK_APPOINTMENT.format(application_id=application_id)
        )
        await state.update_data(prompt_message_id=prompt.message_id)
        await callback.answer(texts.ADMIN_ACCEPTED_ASK_DETAILS)
        return
    if action == "reserve":
        updated = await db.update_status(
            application_id,
            ("new", "in_progress"),
            "reserve",
            actor_id,
            actor_name,
        )
        if not updated:
            await callback.answer(texts.ADMIN_ALREADY_PROCESSED, show_alert=True)
            return
        await _refresh_admin_card(bot, application_id)
        await callback.answer(texts.ADMIN_MOVED_TO_RESERVE)
        return
    if action == "appointment":
        if application["status"] != "in_progress":
            await callback.answer(texts.ADMIN_ALREADY_PROCESSED, show_alert=True)
            return
        await state.set_state(AdminInput.appointment)
        await state.update_data(
            application_id=application_id,
            prompt_message_id=None,
            admin_chat_id=message.chat.id,
        )
        prompt = await message.answer(
            texts.ADMIN_ASK_APPOINTMENT.format(application_id=application_id)
        )
        await state.update_data(prompt_message_id=prompt.message_id)
        await callback.answer()
        return
    if action == "note":
        if application["status"] not in {"new", "in_progress", "reserve"}:
            await callback.answer(texts.ADMIN_ALREADY_PROCESSED, show_alert=True)
            return
        await state.set_state(AdminInput.note)
        await state.update_data(
            application_id=application_id,
            prompt_message_id=None,
            admin_chat_id=message.chat.id,
        )
        prompt = await message.answer(texts.ADMIN_ASK_NOTE.format(application_id=application_id))
        await state.update_data(prompt_message_id=prompt.message_id)
        await callback.answer()
        return
    await callback.answer(texts.ADMIN_ALREADY_PROCESSED, show_alert=True)


def _is_cancel_command(value: str) -> bool:
    return value.strip().partition("@")[0].lower() == "/cancel"


async def _cancel_admin_input(
    message: Message,
    state: FSMContext,
    bot: Bot,
    data: dict[str, Any],
) -> bool:
    if not _is_cancel_command(message.text or ""):
        return False
    await _delete_message(message)
    await state.clear()
    prompt_id = data.get("prompt_message_id")
    if prompt_id:
        try:
            await bot.delete_message(message.chat.id, prompt_id)
        except TelegramBadRequest:
            pass
    await message.answer(texts.ACTION_CANCELLED, reply_markup=ReplyKeyboardRemove())
    return True


@router.message(AdminInput.appointment, F.text)
async def admin_appointment_input(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    if not _is_admin_chat(message.chat.id) or message.chat.id != data.get("admin_chat_id"):
        return
    if await _cancel_admin_input(message, state, bot, data):
        return
    details = (message.text or "").strip()
    if not 10 <= len(details) <= 500:
        prompt_id = data.get("prompt_message_id")
        if prompt_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=prompt_id,
                    text=f"{texts.ADMIN_INVALID_APPOINTMENT}\n\n"
                    f"{texts.ADMIN_ASK_APPOINTMENT.format(application_id=data.get('application_id'))}",
                )
            except TelegramBadRequest:
                pass
        return
    await _delete_message(message)
    application_id = int(data["application_id"])
    updated = await db.update_status(
        application_id,
        ("in_progress",),
        "invited",
        message.from_user.id,
        _admin_name(message),
        audition_details=details,
    )
    prompt_id = data.get("prompt_message_id")
    await state.clear()
    if prompt_id:
        try:
            await bot.delete_message(message.chat.id, prompt_id)
        except TelegramBadRequest:
            pass
    if not updated:
        await message.answer(texts.ADMIN_ALREADY_PROCESSED)
        return
    await _send_status_to_player(
        bot,
        updated["user_id"],
        texts.INVITATION_TO_PLAYER.format(details=_esc(details)),
    )
    await _refresh_admin_card(bot, application_id)
    await message.answer(texts.ADMIN_APPOINTMENT_SENT, reply_markup=ReplyKeyboardRemove())


@router.message(AdminInput.note, F.text)
async def admin_note_input(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    if not _is_admin_chat(message.chat.id) or message.chat.id != data.get("admin_chat_id"):
        return
    if await _cancel_admin_input(message, state, bot, data):
        return
    note_text = (message.text or "").strip()
    if not 1 <= len(note_text) <= 350:
        prompt_id = data.get("prompt_message_id")
        if prompt_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=prompt_id,
                    text=f"{texts.ADMIN_INVALID_NOTE}\n\n"
                    f"{texts.ADMIN_ASK_NOTE.format(application_id=data.get('application_id'))}",
                )
            except TelegramBadRequest:
                pass
        return
    await _delete_message(message)
    application_id = int(data["application_id"])
    await db.add_note(application_id, message.from_user.id, _admin_name(message), note_text)
    prompt_id = data.get("prompt_message_id")
    await state.clear()
    if prompt_id:
        try:
            await bot.delete_message(message.chat.id, prompt_id)
        except TelegramBadRequest:
            pass
    await _refresh_admin_card(bot, application_id)
    await message.answer(texts.ADMIN_NOTE_SAVED)


@router.message(AdminInput.find, F.text)
async def admin_find_input(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    if not _is_admin_chat(message.chat.id) or message.chat.id != data.get("admin_chat_id"):
        return
    query = (message.text or "").strip()
    await _delete_message(message)
    prompt_id = data.get("prompt_message_id")
    if _is_cancel_command(query):
        await state.clear()
        if prompt_id:
            try:
                await bot.delete_message(message.chat.id, prompt_id)
            except TelegramBadRequest:
                pass
        await message.answer(texts.ADMIN_FIND_CANCELLED)
        return
    if not 2 <= len(query) <= 100:
        if prompt_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=prompt_id,
                    text=f"{texts.ADMIN_FIND_INVALID}\n\n{texts.ADMIN_FIND_PROMPT}",
                )
            except TelegramBadRequest:
                pass
        return
    await state.clear()
    if prompt_id:
        try:
            await bot.delete_message(message.chat.id, prompt_id)
        except TelegramBadRequest:
            pass
    await _send_find_results(bot, message.chat.id, query)


@router.message(AdminInput.appointment)
@router.message(AdminInput.note)
@router.message(AdminInput.find)
async def admin_non_text_input(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    prompt_id = data.get("prompt_message_id")
    if prompt_id and _is_admin_chat(message.chat.id):
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_id,
                text=texts.ADMIN_TEXT_ONLY,
            )
        except TelegramBadRequest:
            pass


@router.message(Command("menu"))
async def admin_menu_command(message: Message) -> None:
    if not _is_admin_chat(message.chat.id):
        return
    await message.answer(
        texts.ADMIN_MENU_TEXT.format(title=texts.ADMIN_MENU_TITLE),
        reply_markup=keyboards.admin_menu_keyboard(),
    )


@router.message(Command("help"))
async def admin_help_command(message: Message) -> None:
    if not _is_admin_chat(message.chat.id):
        return
    await message.answer(
        texts.ADMIN_HELP_TEXT,
        reply_markup=keyboards.admin_menu_keyboard(),
    )


@router.message(Command("chatid"))
async def chat_id_command(message: Message) -> None:
    """Показывает ID текущего чата. Напиши /chatid в группе модераторов."""
    await message.answer(
        f"ID этого чата: <code>{message.chat.id}</code>\n"
        f"ID из ADMIN_CHAT_ID: <code>{ADMIN_CHAT_ID}</code>\n"
        f"Совпадает: {'да ✅' if message.chat.id == ADMIN_CHAT_ID else 'нет ❌'}"
    )


@router.message(Command("stats"))
async def admin_stats_command(message: Message) -> None:
    if not _is_admin_chat(message.chat.id):
        return
    stats = await db.get_statistics()
    status_rows = [
        f"{texts.STATUS_EMOJI.get(key, '⚪')} {texts.STATUS_LABEL.get(key, key)}: "
        f"{stats['statuses'].get(key, 0)}"
        for key in texts.STATUSES
    ]
    position_rows = [
        texts.ADMIN_POSITION_STAT.format(
            position=texts.POSITION_NAMES.get(
                row["primary_position"], row["primary_position"]
            ),
            amount=row["amount"],
        )
        for row in stats["positions"]
    ] or [texts.ADMIN_EMPTY_STATS]
    average_age = stats["average_age"] if stats["average_age"] is not None else texts.UNKNOWN_VALUE
    await message.answer(
        f"{texts.ADMIN_STATS_TITLE}\n"
        + texts.ADMIN_STATS_TOTAL.format(total=stats["total"])
        + "\n"
        + texts.ADMIN_STATS_AVERAGE_AGE.format(age=_esc(average_age))
        + "\n\n"
        + texts.ADMIN_STATS_STATUS_TITLE
        + "\n"
        + "\n".join(status_rows)
        + "\n\n"
        + texts.ADMIN_STATS_POSITION_TITLE
        + "\n"
        + "\n".join(position_rows)
    )


NEW_APPLICATIONS_PAGE_SIZE = 10


async def _show_new_applications(
    message: Message, *, before_id: int | None = None, edit: bool = False
) -> None:
    try:
        applications = await db.list_applications(
            statuses=("new",), limit=NEW_APPLICATIONS_PAGE_SIZE + 1, before_id=before_id
        )
    except Exception:
        logger.exception("Could not load new applications")
        await message.answer(texts.ADMIN_NEW_LOAD_FAILED)
        return

    page = applications[:NEW_APPLICATIONS_PAGE_SIZE]
    next_before_id = page[-1]["id"] if len(applications) > len(page) else None
    markup = keyboards.new_applications_keyboard(page, next_before_id, before_id is not None)
    body = (
        texts.ADMIN_NEW_LIST.format(title=texts.ADMIN_LIST_TITLE)
        if page
        else texts.ADMIN_NEW_EMPTY
    )
    if edit:
        try:
            await message.edit_text(body, reply_markup=markup)
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                raise
    else:
        await message.answer(body, reply_markup=markup)


@router.message(Command("new"))
async def admin_new_command(message: Message) -> None:
    if _is_admin_chat(message.chat.id):
        await _show_new_applications(message)


async def _send_find_results(bot: Bot, chat_id: int, query: str) -> None:
    applications = await db.find_applications(query)
    if not applications:
        await bot.send_message(chat_id, texts.ADMIN_FIND_EMPTY)
        return
    await bot.send_message(
        chat_id,
        texts.ADMIN_FIND_HEADER.format(count=len(applications)),
    )
    for application in reversed(applications):
        status_emoji = texts.STATUS_EMOJI.get(
            application["status"], texts.ADMIN_UNKNOWN_STATUS
        )
        status_label = texts.STATUS_LABEL.get(
            application["status"], application["status"]
        )
        contact_url = admin_contact_url(application)
        contact = (
            texts.ADMIN_OPEN_CONTACT.format(url=_esc(contact_url))
            if contact_url
            else ""
        )
        await bot.send_message(
            chat_id,
            texts.ADMIN_SEARCH_ROW.format(
                id=application["id"],
                name=_esc(application["full_name"]),
                emoji=status_emoji,
                status=_esc(status_label),
                created_at=_esc(format_datetime(application.get("created_at"))),
                contact=contact,
            ),
        )


@router.message(Command("find"))
async def admin_find_command(message: Message, bot: Bot) -> None:
    if not _is_admin_chat(message.chat.id):
        return
    query = (message.text or "").partition(" ")[2].strip()
    if not query:
        await message.answer(texts.ADMIN_FIND_USAGE)
        return
    await _send_find_results(bot, message.chat.id, query)


@router.message(Command("export"))
async def admin_export_command(message: Message) -> None:
    if not _is_admin_chat(message.chat.id):
        return
    applications = await db.all_applications_for_export()
    if not applications:
        await message.answer(texts.ADMIN_EXPORT_EMPTY)
        return
    output = io.StringIO(newline="")
    fields = list(texts.CSV_HEADERS)
    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        extrasaction="ignore",
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writerow(texts.CSV_HEADERS)
    for application in reversed(applications):
        row = {key: application.get(key) for key in fields}
        row["days"] = format_days(application.get("days", [])) if application.get("days") else ""
        row["times"] = format_times(application.get("times", [])) if application.get("times") else ""
        row["school_years"] = format_school_years(application.get("school_years"))
        row["primary_position"] = format_position(application.get("primary_position"))
        row["secondary_position"] = (
            texts.CSV_NO_SECONDARY
            if application.get("secondary_position") == "none"
            else format_position(application.get("secondary_position"))
        )
        row["working_foot"] = format_foot(application.get("working_foot"))
        row["level"] = format_level(application.get("level"))
        row["referral_source"] = (
            format_source(application.get("referral_source"))
            if application.get("referral_source")
            else ""
        )
        writer.writerow(row)
    file = BufferedInputFile(
        output.getvalue().encode("utf-8-sig"),
        filename=texts.ADMIN_EXPORT_FILENAME,
    )
    await message.answer_document(
        file,
        caption=texts.ADMIN_EXPORT_COUNT.format(count=len(applications)),
    )


@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}), F.text)
async def admin_unknown_command(message: Message) -> None:
    if not _is_admin_chat(message.chat.id):
        return
    if message.text and message.text.startswith("/"):
        await message.answer(texts.ADMIN_UNKNOWN_COMMAND)


# ----------------------------------------------------------------------------
# Глобальный обработчик ошибок: любая необработанная ошибка попадёт в логи
# ----------------------------------------------------------------------------


@router.errors()
async def on_error(event: ErrorEvent) -> bool:
    logger.exception("Unhandled error in handler: %s", event.exception)
    return True


# ----------------------------------------------------------------------------
# Локальный запуск (Replit): long polling
# Не запускай одновременно с Render: polling удаляет webhook.
# ----------------------------------------------------------------------------


async def run_polling() -> None:
    token, _ = load_settings()
    bot = create_bot(token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await check_admin_chat(bot)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_polling())
