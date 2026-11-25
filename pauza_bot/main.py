import os
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from pauza_bot.main import router, load_settings, db

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("pauza_bot.webhook")


async def on_startup(app: web.Application):
    bot: Bot = app["bot"]
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

    # Прокидываем ADMIN_CHAT_ID в глобальную переменную модуля pauza_bot.main
    import pauza_bot.main as pauza_main
    pauza_main.ADMIN_CHAT_ID = admin_chat_id

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    app = web.Application()
    app["bot"] = bot
    app["admin_chat_id"] = admin_chat_id

    # health-check для внешнего пингера, чтобы Render не засыпал
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    port = int(os.getenv("PORT", 8080))
    logger.info("Starting webhook server on port %s", port)
    web.run_app(app, host="0.0.0.0", port=port)



ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "-1004290581160").strip())
# Файл используется как модуль, polling отключен
