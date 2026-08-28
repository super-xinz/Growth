import os
import signal
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def main() -> int:
    worker = subprocess.Popen(
        [
            "celery",
            "-A",
            "app.worker.celery_app",
            "worker",
            "-B",
            "--loglevel=INFO",
            "--schedule=/tmp/celerybeat-schedule",
        ]
    )

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            healthy = self.path == "/health" and worker.poll() is None
            body = b'{"status":"ok"}' if healthy else b'{"status":"unavailable"}'
            self.send_response(200 if healthy else 503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def stop(*_args):
        if worker.poll() is None:
            worker.terminate()
        server.shutdown()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    return_code = worker.wait()
    server.shutdown()
    thread.join(timeout=5)
    return return_code


if __name__ == "__main__":
    sys.exit(main())
