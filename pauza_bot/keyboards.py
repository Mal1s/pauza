"""Inline keyboards for player surveys and the admin group."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from . import texts


def button(label: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback_data)


def home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button(texts.START_FORM_BUTTON, "home:apply")],
            [
                button(texts.ABOUT_TEAM_BUTTON, "home:about"),
                button(texts.MY_APPLICATION_BUTTON, "home:mine"),
            ],
        ]
    )


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                button(texts.ADMIN_MENU_NEW_BUTTON, "admin:menu:new"),
                button(texts.ADMIN_MENU_FIND_BUTTON, "admin:menu:find"),
            ],
            [
                button(texts.ADMIN_MENU_STATS_BUTTON, "admin:menu:stats"),
                button(texts.ADMIN_MENU_EXPORT_BUTTON, "admin:menu:export"),
            ],
            [button(texts.ADMIN_MENU_HELP_BUTTON, "admin:menu:help")],
        ]
    )


def new_applications_keyboard(
    applications: list[dict], next_before_id: int | None, show_first_page: bool
) -> InlineKeyboardMarkup | None:
    rows = [
        [button(f"#{item['id']} · {item['full_name'][:45]}", f"admin:open_new:{item['id']}")]
        for item in applications
    ]
    navigation = []
    if show_first_page:
        navigation.append(button(texts.ADMIN_NEW_FIRST_PAGE, "admin:new_page:0"))
    if next_before_id is not None:
        navigation.append(button(texts.ADMIN_NEW_NEXT_PAGE, f"admin:new_page:{next_before_id}"))
    if navigation:
        rows.append(navigation)
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def cancel_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                button(texts.YES_CANCEL_BUTTON, "survey:cancel:yes"),
                button(texts.NO_CANCEL_BUTTON, "survey:cancel:no"),
            ]
        ]
    )


def survey_keyboard(step: str, data: dict) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if step == "contact" and data.get("contact_username"):
        username = data["contact_username"]
        rows.append([button(texts.CONTACT_CONFIRM_YES, "survey:contact:yes")])
        rows.append([button(texts.CONTACT_CONFIRM_NO, "survey:contact:no")])
    elif step == "school":
        rows.append(
            [
                button(texts.YES_BUTTON, "survey:choose:school:yes"),
                button(texts.NO_BUTTON, "survey:choose:school:no"),
            ]
        )
    elif step == "school_years":
        for label, value in texts.SCHOOL_YEARS:
            rows.append([button(label, f"survey:choose:school_years:{value}")])
    elif step in {"primary_position", "secondary_position"}:
        options = list(texts.POSITIONS)
        if step == "secondary_position":
            options = [
                pair for pair in options if pair[1] != data.get("primary_position")
            ]
            options.append((texts.NO_SECONDARY_BUTTON, "none"))
        for label, value in options:
            rows.append([button(label, f"survey:choose:{step}:{value}")])
    elif step == "working_foot":
        rows.extend(
            [[button(label, f"survey:choose:working_foot:{value}")] for label, value in texts.FEET]
        )
    elif step == "level":
        rows.extend(
            [[button(label, f"survey:choose:level:{value}")] for label, value in texts.LEVELS]
        )
    elif step == "injuries":
        rows.append(
            [
                button(texts.NO_BUTTON, "survey:choose:injuries:no"),
                button(texts.HAS_BUTTON, "survey:choose:injuries:yes"),
            ]
        )
    navigation = []
    if step != "full_name":
        navigation.append(button(texts.BACK_BUTTON, "survey:back"))
    if step in {"achievements", "video_link", "about", "additional_info"}:
        navigation.append(button(texts.SKIP_BUTTON, "survey:skip"))
    navigation.append(button(texts.CANCEL_BUTTON, "survey:cancel"))
    rows.append(navigation)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button(texts.SUBMIT_BUTTON, "survey:submit")],
            [
                button(texts.EDIT_BUTTON, "survey:edit:list"),
                button(texts.CANCEL_BUTTON, "survey:cancel"),
            ],
        ]
    )


def edit_fields_keyboard() -> InlineKeyboardMarkup:
    rows = []
    fields = texts.FIELD_DISPLAY_ORDER
    for index in range(0, len(fields), 2):
        row = [
            button(texts.FIELD_NAMES[key], f"survey:edit:{key}")
            for key in fields[index : index + 2]
        ]
        rows.append(row)
    rows.append(
        [
            button(texts.EDIT_BACK_BUTTON, "survey:edit:back"),
            button(texts.CANCEL_BUTTON, "survey:cancel"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def status_keyboard(status: str, application_id: int, contact_url: str | None) -> InlineKeyboardMarkup | None:
    rows: list[list[InlineKeyboardButton]] = []
    if status == "new":
        rows.append(
            [
                button(texts.ADMIN_ACCEPT_BUTTON, f"admin:accept:{application_id}"),
                button(texts.ADMIN_REJECT_BUTTON, f"admin:reject:{application_id}"),
            ]
        )
        rows.append(
            [
                button(texts.ADMIN_RESERVE_BUTTON, f"admin:reserve:{application_id}"),
                button(texts.ADMIN_NOTE_BUTTON, f"admin:note:{application_id}"),
            ]
        )
    elif status == "in_progress":
        rows.append(
            [
                button(texts.ADMIN_APPOINT_BUTTON, f"admin:appointment:{application_id}"),
                button(texts.ADMIN_REJECT_BUTTON, f"admin:reject:{application_id}"),
            ]
        )
        rows.append(
            [
                button(texts.ADMIN_RESERVE_BUTTON, f"admin:reserve:{application_id}"),
                button(texts.ADMIN_NOTE_BUTTON, f"admin:note:{application_id}"),
            ]
        )
    elif status == "reserve":
        rows.append(
            [
                button(texts.ADMIN_ACCEPT_BUTTON, f"admin:accept:{application_id}"),
                button(texts.ADMIN_REJECT_BUTTON, f"admin:reject:{application_id}"),
            ]
        )
        rows.append([button(texts.ADMIN_NOTE_BUTTON, f"admin:note:{application_id}")])
    if contact_url:
        rows.append(
            [InlineKeyboardButton(text=texts.ADMIN_MESSAGE_PLAYER_BUTTON, url=contact_url)]
        )
    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reject_confirmation_keyboard(application_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                button(texts.ADMIN_CONFIRM_YES, f"admin:reject:yes:{application_id}"),
                button(texts.ADMIN_CONFIRM_NO, f"admin:reject:no:{application_id}"),
            ]
        ]
    )
