"""
GitHub webhook listener.

When a push lands on the 'main' branch GitHub sends a POST to this server.
The server verifies the HMAC-SHA256 signature, then runs 'git pull origin main'
so the production copy on your Linux server stays in sync automatically.

Setup (GitHub side)
-------------------
1. Go to your repo → Settings → Webhooks → Add webhook
2. Payload URL : http://<your-server-ip>:<port>/webhook
3. Content type: application/json
4. Secret      : the webhook_secret value from bot_config.ini
5. Events      : "Just the push event"

The port and secret come from config.py (bot_config.ini + setup.py).
"""

import hashlib
import hmac
import logging
import subprocess
import sys
from pathlib import Path

from flask import Flask, abort, jsonify, request

# Add project root to path so config.py is importable
sys.path.insert(0, str(Path(__file__).parent))
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("webhook")

app = Flask(__name__)

REPO_DIR = Path(__file__).parent.resolve()
TARGET_BRANCH = "main"


def _verify_signature(payload: bytes, header_sig: str | None) -> bool:
    """Return True when the GitHub HMAC-SHA256 signature matches our secret."""
    if not header_sig:
        return False
    expected = "sha256=" + hmac.new(
        config.WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header_sig)


def _git_pull() -> tuple[str, int]:
    """Run git pull and return (output, returncode)."""
    result = subprocess.run(
        ["git", "-C", str(REPO_DIR), "pull", "origin", TARGET_BRANCH],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return (result.stdout + result.stderr).strip(), result.returncode


@app.route("/webhook", methods=["POST"])
def webhook() -> tuple:
    # ── Signature check ───────────────────────────────────────────
    payload = request.get_data()
    sig = request.headers.get("X-Hub-Signature-256")

    if not _verify_signature(payload, sig):
        log.warning("Rejected webhook — bad or missing signature.")
        abort(403)

    data = request.get_json(silent=True) or {}

    # ── Only act on pushes to main ────────────────────────────────
    ref = data.get("ref", "")
    if ref != f"refs/heads/{TARGET_BRANCH}":
        log.info("Ignored push to ref: %s", ref)
        return jsonify({"status": "ignored", "ref": ref}), 200

    pusher = data.get("pusher", {}).get("name", "unknown")
    log.info("Push to main by %s — pulling…", pusher)

    output, code = _git_pull()

    if code == 0:
        log.info("git pull succeeded:\n%s", output)
        return jsonify({"status": "pulled", "output": output}), 200
    else:
        log.error("git pull failed (exit %d):\n%s", code, output)
        return jsonify({"status": "error", "output": output}), 500


@app.route("/health", methods=["GET"])
def health() -> tuple:
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    log.info("Webhook server starting on port %d", config.WEBHOOK_PORT)
    app.run(host="0.0.0.0", port=config.WEBHOOK_PORT)
