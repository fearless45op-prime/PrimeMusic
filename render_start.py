"""Start VenomX bot alongside a tiny Render health-check HTTP server."""
import json
import os
import runpy
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health", "/healthz"):
            body = json.dumps({"status": "ok", "service": "VenomMusic"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            body = b'{"detail":"Not found"}'
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Keep health probes from flooding Render logs.
        return


def start_health_server():
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, name="health-server", daemon=True)
    thread.start()
    print(f"Health server listening on 0.0.0.0:{port}", flush=True)


if __name__ == "__main__":
    # Bind the port before importing/starting the bot so Render detects it early.
    start_health_server()
    runpy.run_module("VenomX", run_name="__main__", alter_sys=True)
