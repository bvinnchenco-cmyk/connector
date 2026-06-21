"""
Simple webhook server — listens for GitHub push events and redeploys the bot.
Managed as systemd service: concert-webhook
"""
import os
import subprocess
import hmac
import hashlib
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SECRET = os.environ.get("WEBHOOK_SECRET", "concert-deploy-secret")


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/deploy":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        sig = self.headers.get("X-Hub-Signature-256", "")
        mac = hmac.new(SECRET.encode(), body, hashlib.sha256)
        expected = "sha256=" + mac.hexdigest()

        if not hmac.compare_digest(sig, expected):
            logger.warning("Invalid signature: got %s, expected %s", sig, expected)
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return

        logger.info("Valid deploy webhook received, running deploy.sh")
        subprocess.Popen(["bash", "/opt/concert-agent/apps/ticket-agent/deploy.sh"])

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Deploying...")

    def do_GET(self):
        """Health check"""
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Webhook server OK")

    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)


if __name__ == "__main__":
    logger.info("Webhook server starting on port 8080")
    server = HTTPServer(("0.0.0.0", 8080), WebhookHandler)
    logger.info("Webhook server listening on port 8080")
    server.serve_forever()
