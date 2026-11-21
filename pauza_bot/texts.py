"""All player-facing and admin-facing text used by the PAUZA bot."""

BRAND = "⚽ <b>ПАУЗА</b> · набор игроков"
SEPARATOR = "━━━━━━━━━━━━━━"

WELCOME = (
    "⚽ <b>ПАУЗА — набор в команду</b>\n"
    "━━━━━━━━━━━━━━\n"
    "Хочешь попасть на просмотр? Заполни короткую анкету, это займёт 3–4 минуты.\n"
    "Тренеры посмотрят её и сами с тобой свяжутся 🤝"
)
ABOUT_TEAM = (
    "⚽ <b>О команде «ПАУЗА»</b>\n"
    "━━━━━━━━━━━━━━\n"
    "Мы футбольная команда, которая ищет новых игроков. "
    "Расскажи о себе в анкете — тренеры свяжутся с тобой 🤝"
)
ACTIVE_APPLICATION = (
    "Твоя анкета уже у тренеров 🟡\n"
    "Мы ответим, как только появятся новости."
)
COOLDOWN_APPLICATION = (
    "Спасибо за интерес к «ПАУЗЕ»! После отказа новую анкету можно отправить "
    "через 14 дней. Попробуй снова немного позже 🙌"
)
APPLICATION_SENT = (
    "🎉 Анкета отправлена тренерам!\n"
    "Они посмотрят её и свяжутся с тобой. Статус можно проверить в «📋 Моя заявка»."
)
APPLICATION_SENT_ADMIN_ERROR = (
    "🎉 Анкета сохранена! Сейчас не получилось доставить её тренерам, "
    "но она не потерялась. Они увидят её в списке новых заявок."
)
NO_APPLICATION = "Пока у тебя нет заявок. Нажми «📝 Заполнить анкету», чтобы начать."
ABOUT_TEAM_BUTTON = "ℹ️ О команде"
START_FORM_BUTTON = "📝 Заполнить анкету"
MY_APPLICATION_BUTTON = "📋 Моя заявка"
YES_BUTTON = "Да"
NO_BUTTON = "Нет"
HAS_BUTTON = "Есть"
NO_SECONDARY_BUTTON = "Нет запасной"
AVAILABILITY_DONE_BUTTON = "Готово ➡️"
SELECTED_MARK = "✅ "
EDIT_BACK_BUTTON = "⬅️ К анкете"
BACK_BUTTON = "⬅️ Назад"
CANCEL_BUTTON = "✖️ Отмена"
SKIP_BUTTON = "⏭ Пропустить"
SUBMIT_BUTTON = "✅ Отправить тренерам"
EDIT_BUTTON = "✏️ Изменить"
CANCELLED = "Анкета отменена. Если захочешь — заполни её в любое время ⚽"
SURVEY_CANCEL_CONFIRM = "Точно отменить заполнение анкеты?"
YES_CANCEL_BUTTON = "Да, отменить"
NO_CANCEL_BUTTON = "Продолжить анкету"
EDIT_TITLE = "Что хочешь изменить?"
REVIEW_TITLE = "⚽ <b>Проверь анкету</b>"
REVIEW_HELP = "Всё верно? Можно отправить анкету или изменить отдельное поле."
STEP_PROGRESS = "<b>Шаг {step} из {total}</b> · {bar}"
AVAILABILITY_SELECTED = "<b>Выбрано:</b> {days}\n<b>Время:</b> {times}"
REVIEW_TEMPLATE = (
    "{title}\n{separator}\n"
    "👤 <b>{full_name}</b>\n"
    "🎂 {birth_line}\n"
    "💬 {contact}\n"
    "{separator}\n"
    "📏 {height} см · ⚖️ {weight} кг\n"
    "🦶 {foot} нога\n"
    "🎯 {position} (запасная: {secondary})\n"
    "📈 Уровень: {level}\n"
    "🏫 Спортшкола: {school}\n"
    "🏆 Достижения: {achievements}\n"
    "🎥 Видео: {video}\n"
    "{separator}\n"
    "📅 {days} · {times}\n"
    "🩹 Травмы: {injury}\n"
    "📣 Узнал: {source}\n"
    "💭 О себе: {about}\n\n"
    "🗒 Дополнительно: {additional_info}\n\n"
    "{help}"
)
APPLICATION_TITLE = "⚽ <b>ПАУЗА · заявка #{application_id}</b>"
APPLICATION_NAME = "👤 <b>{name}</b>"
APPLICATION_BIRTH = "🎂 {birth_line}"
AGE_IN_BIRTH_LINE = " ({age})"
APPLICATION_CONTACT = "💬 {contact}"
APPLICATION_MEASUREMENTS = "📏 {height} см · ⚖️ {weight} кг"
APPLICATION_FOOT = "🦶 {foot} нога"
APPLICATION_POSITION = "🎯 {position} (запасная: {secondary})"
APPLICATION_LEVEL = "📈 Уровень: {level}"
APPLICATION_SCHOOL = "🏫 Спортшкола: {school}"
APPLICATION_ACHIEVEMENTS = "🏆 Достижения: {achievements}"
APPLICATION_VIDEO = "🎥 Видео: {video}"
APPLICATION_AVAILABILITY = "📅 {days} · {times}"
APPLICATION_INJURY = "🩹 Травмы: {injury}"
APPLICATION_SOURCE = "📣 Узнал: {source}"
APPLICATION_ABOUT = "💭 О себе: {about}"
APPLICATION_ADDITIONAL_INFO = "🗒 Дополнительно: {additional_info}"
SCHOOL_NOT_ATTENDED = "нет"
SCHOOL_ATTENDED = "да, «{school}», {years}"
INJURY_NONE = "нет"
INJURY_PRESENT = "есть — {details}"
SECONDARY_NONE = "нет запасной"
AGE_FLASH = "🎂 Тебе {age}."
AGE_WORD_LET = "лет"
AGE_WORD_YEAR = "год"
AGE_WORD_YEARS = "года"
EARLIER_NOTES = "<i>Ещё {count} ранних заметок сохранено</i>"
COACH_DEFAULT_NAME = "Тренер"
UNKNOWN_STATUS_EMOJI = "⚪"
SECONDARY_SAME_ERROR = "Запасная позиция должна отличаться от основной."
ACTION_CANCELLED = "Действие отменено."
ADMIN_ONLY_ACTION = "Это действие доступно только в админ-чате."
ADMIN_REJECTION_SAVED = "Отказ сохранён."
ADMIN_ACCEPTED_ASK_DETAILS = "Заявка принята. Отправь дату, время и место просмотра."
ADMIN_MOVED_TO_RESERVE = "Заявка добавлена в резерв."
ADMIN_TEXT_ONLY = "Пожалуйста, отправь ответ текстом."
ADMIN_SEARCH_ROW = (
    "#{id} · <b>{name}</b>\n{emoji} {status} · создана {created_at}{contact}"
)
ADMIN_OPEN_CONTACT = '\n<a href="{url}">Открыть контакт</a>'
ADMIN_STATS_TOTAL = "Всего заявок: <b>{total}</b>"
ADMIN_STATS_AVERAGE_AGE = "Средний возраст: <b>{age}</b>"
ADMIN_EMPTY_STATS = "• Пока нет данных"
ADMIN_POSITION_STAT = "• {position}: {amount}"
ADMIN_SOURCE_STAT = "• {source}: {amount}"
ADMIN_STATS_STATUS_TITLE = "<b>По статусам</b>"
ADMIN_STATS_POSITION_TITLE = "<b>Топ позиций</b>"
ADMIN_STATS_SOURCE_TITLE = "<b>Источники</b>"
ADMIN_NEW_LIST_HEADER = "{title} · {count}\n"
ADMIN_NEW_LIST = "Карточки с кнопками уже отправлены в этот чат."
ADMIN_UNKNOWN_STATUS = "⚪"
ADMIN_FIND_HEADER = "🔎 <b>Результаты поиска:</b> {count}"
ADMIN_SEARCH_ROW = (
    "#{id} · <b>{name}</b>\n{emoji} {status} · создана {created_at}{contact}"
)
ADMIN_OPEN_CONTACT = '\n<a href="{url}">Открыть контакт</a>'
ADMIN_EXPORT_COUNT = "📄 Заявок в выгрузке: {count}"
CSV_NO_SECONDARY = "Нет запасной"
VALIDATION_PREFIX = "⚠️ "
UNEXPECTED_TEXT = "Нажми кнопку ниже или отправь ответ на текущий вопрос."
GENERIC_ERROR = "Не получилось обновить экран. Попробуй ещё раз."
CONTACT_AUTO_PROMPT = (
    "Я нашёл Telegram: <b>{username}</b>\n"
    "Это твой аккаунт для связи?"
)
CONTACT_CONFIRM_YES = "✅ Да, это мой"
CONTACT_CONFIRM_NO = "Нет, укажу другой"
CONTACT_MANUAL_PROMPT = "Укажи контакт: <code>@username</code>, <code>t.me/username</code> или <code>vk.com/username</code>."
UNKNOWN_VALUE = "—"

QUESTIONS = {
    "full_name": "Как тебя зовут? Напиши фамилию, имя и отчество (минимум два слова).",
    "birth_date": "Дата рождения в формате <code>ДД.ММ.ГГГГ</code>.",
    "contact": "Как с тобой связаться? Можно подтвердить Telegram выше или указать Telegram/VK.",
    "school": "Занимался в футбольной спортшколе?",
    "school_name": "Напиши название спортшколы и/или город.",
    "school_years": "Сколько лет ты занимался в спортшколе?",
    "height_cm": "Какой у тебя рост в сантиметрах? Например: <code>182</code>.",
    "weight_kg": "Какой у тебя вес в килограммах? Например: <code>76</code>.",
    "primary_position": "На какой позиции играешь чаще всего?",
    "secondary_position": "Есть запасная позиция?",
    "working_foot": "Какая у тебя рабочая нога?",
    "level": "Как бы ты описал свой игровой уровень?",
    "achievements": "Расскажи о турнирах, кубках и других достижениях. Это необязательно.",
    "video_link": "Есть ссылка на видео своей игры? Отправь ссылку или пропусти этот шаг.",
    "availability": "Выбери удобные дни и время для просмотра. Нужен хотя бы один день и один период.",
    "injuries": "Есть травмы или ограничения, о которых тренеру важно знать?",
    "injury_details": "Коротко расскажи о травме или ограничении. Это предупреждение для тренера, не медицинская анкета.",
    "referral_source": "Откуда ты узнал о команде?",
    "about": "Опиши себя одной строкой — до 150 символов. Это необязательно.",
    "additional_info": (
        "Есть ещё что-то, что тренеру важно знать? Расскажи об опыте, стиле игры "
        "или мотивации — до 500 символов. Это необязательно."
    ),
}

ERRORS = {
    "full_name": "Напиши минимум два слова. Используй буквы, пробелы и дефис.",
    "birth_date": "Нужна реальная дата в формате ДД.ММ.ГГГГ. Возраст — от 10 до 50 лет.",
    "contact": "Укажи Telegram или VK: @username, t.me/username или vk.com/username.",
    "school_name": "Напиши название школы или город.",
    "height_cm": "Введи целое число от 120 до 220 см.",
    "weight_kg": "Введи вес от 30 до 150 кг, например 76 или 76,5.",
    "achievements": "Сообщение слишком длинное. Умести ответ в 500 символов.",
    "video_link": "Нужна действующая ссылка, начинающаяся с http:// или https://.",
    "availability": "Выбери минимум один день и один период времени.",
    "injury_details": "Напиши коротко, до 300 символов.",
    "referral_source": "Выбери один из вариантов на кнопках.",
    "about": "Умести ответ в 150 символов или пропусти этот шаг.",
    "additional_info": "Умести ответ в 500 символов или пропусти этот шаг.",
}

SCHOOL_YEARS = [
    ("Менее года", "less_1"),
    ("1–2 года", "1_2"),
    ("3–5 лет", "3_5"),
    ("6+ лет", "6_plus"),
]
POSITIONS = [
    ("🧤 Вратарь", "goalkeeper"),
    ("🛡 Защитник", "defender"),
    ("⚙️ Полузащитник", "midfielder"),
    ("🎯 Нападающий", "forward"),
]
FEET = [("Правая", "right"), ("Левая", "left"), ("Обе", "both")]
LEVELS = [
    ("Любитель", "amateur"),
    ("Школа", "school"),
    ("Дубль", "reserve"),
    ("Профессионал", "professional"),
]
SOURCES = [
    ("Instagram", "instagram"),
    ("Telegram", "telegram"),
    ("Друзья", "friends"),
    ("Соцсети / ВК", "social"),
    ("Другое", "other"),
]
DAYS = [
    ("Пн", "mon"),
    ("Вт", "tue"),
    ("Ср", "wed"),
    ("Чт", "thu"),
    ("Пт", "fri"),
    ("Сб", "sat"),
    ("Вс", "sun"),
]
TIMES = [
    ("🌅 Утро", "morning"),
    ("☀️ День", "day"),
    ("🌆 Вечер", "evening"),
]
STATUSES = {
    "new": ("🟡", "Новая"),
    "in_progress": ("🔵", "В работе"),
    "invited": ("🟢", "Приглашён на просмотр"),
    "rejected": ("🔴", "Отказ"),
    "reserve": ("🟣", "Резерв"),
}
STATUS_EMOJI = {key: value[0] for key, value in STATUSES.items()}
STATUS_LABEL = {key: value[1] for key, value in STATUSES.items()}
STATUS_LINES = {
    "new": "Тренеры ещё не обработали анкету.",
    "in_progress": "Тренер уже смотрит твою анкету.",
    "invited": "Тебя пригласили на просмотр! Проверь детали ниже.",
    "rejected": "Спасибо за интерес к «ПАУЗЕ». Попробуй снова через 14 дней.",
    "reserve": "Твоя анкета в резерве. Если появятся новости, тренеры свяжутся с тобой.",
}
REJECTION_TO_PLAYER = (
    "Спасибо за интерес к «ПАУЗЕ»! Сейчас мы не можем позвать тебя на просмотр, "
    "но будем рады видеть тебя снова 🙌"
)
INVITATION_TO_PLAYER = "🎉 Тебя ждут на просмотре!\n\n{details}"
NEW_APPLICATION_ADMIN = "🟡 <b>Новая заявка #{application_id}</b>"
STATUS_ADMIN = "Статус: {emoji} {status}"
CLAIM_ADMIN = "Взял: {admin} · {when}"
ACTION_ADMIN = "Изменил: {admin} · {when}"
AUDITION_ADMIN = "🟢 <b>Просмотр:</b> {details}"
NOTE_ADMIN = "📝 <b>Заметка от {admin}:</b> {note}"
ADMIN_ACCEPT_BUTTON = "✅ Принять"
ADMIN_REJECT_BUTTON = "❌ Отказать"
ADMIN_RESERVE_BUTTON = "⏳ В резерв"
ADMIN_NOTE_BUTTON = "📝 Заметка"
ADMIN_APPOINT_BUTTON = "🟢 Назначить просмотр"
ADMIN_MESSAGE_PLAYER_BUTTON = "💬 Написать игроку"
ADMIN_CONFIRM_REJECT = "Точно отказать игроку?"
ADMIN_CONFIRM_YES = "Да, отказать"
ADMIN_CONFIRM_NO = "Нет"
ADMIN_ASK_APPOINTMENT = (
    "Отправь одним сообщением дату, время и место просмотра для заявки #{application_id}."
)
ADMIN_ASK_NOTE = "Напиши заметку для заявки #{application_id} одним сообщением."
ADMIN_INVALID_APPOINTMENT = "Укажи дату, время и место одним сообщением (до 500 символов)."
ADMIN_INVALID_NOTE = "Заметка должна содержать от 1 до 350 символов."
ADMIN_NOTE_SAVED = "Заметка сохранена."
ADMIN_APPOINTMENT_SENT = "Просмотр назначен. Игроку отправлено уведомление."
ADMIN_ALREADY_PROCESSED = "Эта заявка уже обработана или изменена другим тренером."
ADMIN_NOT_FOUND = "Заявка не найдена."
ADMIN_STATS_TITLE = "📊 <b>Сводка по заявкам</b>"
ADMIN_NEW_EMPTY = "🟡 Новых заявок пока нет."
ADMIN_FIND_USAGE = "Использование: <code>/find имя</code>"
ADMIN_FIND_EMPTY = "По этому имени заявок не найдено."
ADMIN_EXPORT_EMPTY = "Пока нечего выгружать."
ADMIN_EXPORT_FILENAME = "pauza_applications.csv"
ADMIN_LIST_TITLE = "🟡 <b>Новые заявки</b>"
ADMIN_UNKNOWN_COMMAND = "Не знаю такую команду. Напиши /stats, /new, /find или /export."
MY_APPLICATION_TITLE = "📋 <b>Твоя последняя заявка</b>"
MY_APPLICATION_STATUS = "Статус: {emoji} <b>{status}</b>\n{message}"
MY_APPLICATION_APPOINTMENT = "\n\n📍 <b>Детали просмотра:</b> {details}"
DAY_NAMES = {code: label for label, code in DAYS}
TIME_NAMES = {"morning": "утро", "day": "день", "evening": "вечер"}
POSITION_NAMES = {
    "goalkeeper": "Вратарь",
    "defender": "Защитник",
    "midfielder": "Полузащитник",
    "forward": "Нападающий",
}
FOOT_NAMES = {"right": "Правая", "left": "Левая", "both": "Обе"}
LEVEL_NAMES = {
    "amateur": "Любитель",
    "school": "Школа",
    "reserve": "Дубль",
    "professional": "Профессионал",
}
SOURCE_NAMES = {
    "instagram": "Instagram",
    "telegram": "Telegram",
    "friends": "Друзья",
    "social": "Соцсети / ВК",
    "other": "Другое",
}
SCHOOL_YEAR_NAMES = dict(SCHOOL_YEARS)
FIELD_NAMES = {
    "full_name": "ФИО",
    "birth_date": "Дата рождения",
    "contact": "Контакт",
    "school": "Спортшкола",
    "school_name": "Название школы",
    "school_years": "Стаж в спортшколе",
    "height_cm": "Рост",
    "weight_kg": "Вес",
    "primary_position": "Основная позиция",
    "secondary_position": "Запасная позиция",
    "working_foot": "Рабочая нога",
    "level": "Уровень",
    "achievements": "Достижения",
    "video_link": "Видео игры",
    "availability": "Дни и время",
    "injuries": "Травмы / ограничения",
    "injury_details": "Комментарий о травме",
    "referral_source": "Источник",
    "about": "О себе",
    "additional_info": "Дополнительная информация",
}
FIELD_DISPLAY_ORDER = list(FIELD_NAMES)
CSV_HEADERS = {
    "id": "ID заявки",
    "user_id": "Telegram user ID",
    "tg_username": "Telegram username",
    "full_name": "ФИО",
    "birth_date": "Дата рождения",
    "contact": "Контакт",
    "school": "Спортшкола",
    "school_name": "Название школы / город",
    "school_years": "Стаж в спортшколе",
    "height_cm": "Рост, см",
    "weight_kg": "Вес, кг",
    "primary_position": "Основная позиция",
    "secondary_position": "Запасная позиция",
    "working_foot": "Рабочая нога",
    "level": "Уровень",
    "achievements": "Достижения",
    "video_link": "Видео",
    "days": "Дни",
    "times": "Время",
    "injuries": "Травмы / ограничения",
    "injury_details": "Комментарий о травме",
    "referral_source": "Источник",
    "about": "О себе",
    "additional_info": "Дополнительная информация",
    "status": "Статус",
    "taken_by_name": "Взял в работу",
    "taken_at": "Дата взятия в работу",
    "action_by_name": "Последнее действие админа",
    "created_at": "Дата создания",
    "status_updated_at": "Дата обновления статуса",
    "audition_details": "Детали просмотра",
}
