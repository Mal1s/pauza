import os
import asyncio
from aiohttp import web
import threading
from pauza_bot.main import main as start_bot

async def health_check(request):
    return web.Response(text="OK")

def run_bot_in_background():
    start_bot()

async def main():
    app = web.Application()
    app.router.add_get('/', health_check)
    
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Веб-сервер запущен на порту {port}")

    bot_thread = threading.Thread(target=run_bot_in_background, daemon=True)
    bot_thread.start()
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
