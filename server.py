"""Webhook-сервер для Render (web service). Запуск: python server.py"""

import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from pauza_bot.main import check_admin_chat, create_bot, load_settings, router

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("server")


async def health(_: web.Request) -> web.Response:
    """Для UptimeRobot / cron-job.org: пингуй этот адрес каждые 5-10 минут,
    чтобы бесплатный Render не засыпал."""
    return web.Response(text="OK")


async def on_startup(app: web.Application) -> None:
    bot: Bot = app["bot"]
    dp: Dispatcher = app["dp"]
    base_url = os.getenv("RENDER_EXTERNAL_URL", "https://pauza.onrender.com").rstrip("/")
    webhook_url = f"{base_url}/webhook"
    await bot.set_webhook(
        webhook_url,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=False,
    )
    log.info("Webhook set to %s", webhook_url)
    # Диагностика: если админ-чат недоступен, причина будет в логах
    await check_admin_chat(bot)


async def on_cleanup(app: web.Application) -> None:
    await app["bot"].session.close()


def main() -> None:
    token, _ = load_settings()

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    bot = create_bot(token)  # parse_mode=HTML внутри

    app = web.Application()
    app["bot"] = bot
    app["dp"] = dp
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    port = int(os.getenv("PORT", 8080))
    log.info("Starting webhook server on port %s", port)
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()