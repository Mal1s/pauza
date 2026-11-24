import os
import asyncio
from http.server import SimpleHTTPRequestHandler, HTTPServer
from threading import Thread
from pauza_bot.main import main as bot_main

class HealthCheckHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

if __name__ == "__main__":
    Thread(target=run_server, daemon=True).start()
    asyncio.run(bot_main())
