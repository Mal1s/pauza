import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from pauza_bot.main import router, load_settings

logging.basicConfig(level=logging.INFO)

async def on_startup(bot: Bot):
    base_url = os.getenv("RENDER_EXTERNAL_URL", "https://pauza.onrender.com")
    webhook_url = f"{base_url}/webhook"
    await bot.set_webhook(webhook_url)
    logging.info(f"Webhook set to {webhook_url}")

def main():
    token, admin_chat_id = load_settings()
    
    # Создаем диспетчер здесь, чтобы он был доступен
    dp = Dispatcher()
    dp.include_router(router)
    
    bot = Bot(token=token)
    
    app = web.Application()
    
    # Настраиваем вебхук
    setup_application(app, dp, bot=bot)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    
    app.on_startup.append(on_startup)
    
    port = int(os.getenv("PORT", 8080))
    logging.info(f"Starting webhook server on port {port}")
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
