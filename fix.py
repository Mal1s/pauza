import os

ROOT_MAIN_CODE = '''import os
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from pauza_bot.main import router, load_settings, db
import pauza_bot.main as p_main

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("pauza_bot.webhook")


async def on_startup(app: web.Application):
    bot: Bot = app["bot"]
    try:
        await db.init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database init error: {e}")

    base_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not base_url:
        logger.error("RENDER_EXTERNAL_URL is not set — webhook will not be registered")
        return

    webhook_url = f"{base_url}/webhook"
    await bot.set_webhook(webhook_url)
    logger.info("Webhook set to %s", webhook_url)


async def on_shutdown(app: web.Application):
    bot: Bot = app["bot"]
    try:
        await bot.delete_webhook()
    except Exception:
        logger.exception("Failed to delete webhook on shutdown")
    await bot.session.close()


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def main():
    token, admin_chat_id = load_settings()
    p_main.ADMIN_CHAT_ID = admin_chat_id

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    app = web.Application()
    app["bot"] = bot
    app["admin_chat_id"] = admin_chat_id

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    port = int(os.getenv("PORT", 8080))
    logger.info("Starting webhook server on port %s", port)
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
'''

PAUZA_MAIN_PATCH = '''
# --- АВТО-ФИКС ОТ ИИ ---
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "-1004290581160").strip())

# Отключаем polling, так как на Render используется webhook
# if __name__ == "__main__":
#     main()
'''

def fix_project():
    print("🔧 Начинаю исправление...")

    # 1. Перезаписываем корневой main.py
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(ROOT_MAIN_CODE)
    print("✅ Корневой main.py перезаписан (отступы в порядке).")

    # 2. Патчим pauza_bot/main.py
    pauza_file = os.path.join("pauza_bot", "main.py")
    if os.path.exists(pauza_file):
        with open(pauza_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Удаляем старую инициализацию ADMIN_CHAT_ID = 0
        content = content.replace("ADMIN_CHAT_ID = 0", "")

        # Удаляем запуск polling
        content = content.replace('if __name__ == "__main__":\\n    main()', '')

        # Добавляем правильную инициализацию в конец файла
        content += "\\n" + PAUZA_MAIN_PATCH

        with open(pauza_file, "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ pauza_bot/main.py успешно пропатчен.")
    else:
        print("❌ ОШИБКА: Файл pauza_bot/main.py не найден! Убедись, что ты в корне проекта.")

    # 3. Проверка на ошибки
    print("🔍 Проверяю код на ошибки...")
    res = os.system("python -m py_compile main.py")
    if res == 0:
        print("✅ Корневой main.py: СИНТАКСИС ОК")

    res2 = os.system("python -m py_compile pauza_bot/main.py")
    if res2 == 0:
        print("✅ pauza_bot/main.py: СИНТАКСИС ОК")

if __name__ == "__main__":
    fix_project()