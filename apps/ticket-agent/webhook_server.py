"""
Simple webhook server — listens for GitHub push events and redeploys the bot.
Run once: python3 webhook_server.py &
"""
import os
import subprocess
import hmac
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler

SECRET = os.environ.get("WEBHOOK_SECRET", "concert-deploy-secret")


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/deploy":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        # Verify GitHub signature
        sig = self.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            self.send_response(403)
            self.end_headers()
            return

        subprocess.Popen(["bash", "/opt/concert-agent/apps/ticket-agent/deploy.sh"])

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Deploying...")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9000), WebhookHandler)
    print("Webhook server listening on port 9000")
    server.serve_forever()
