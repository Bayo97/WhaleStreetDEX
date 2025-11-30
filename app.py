import os
import time
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, abort
import requests

from scanner import run_scan_once, get_stats, get_last_alerts
from filters import is_probable_honeypot

# ==============================
# ENV CONFIG
# ==============================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID", "0"))
TRIGGER_SECRET = os.environ.get("TRIGGER_SECRET", "secret123")

PORT = int(os.environ.get("PORT", 8080))

WEBHOOK_PATH = os.environ.get(
    "WEBHOOK_PATH",
    f"/webhook/{TELEGRAM_TOKEN[-18:] if TELEGRAM_TOKEN else 'token'}"
)

HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL", 3600))

# ==============================
# LOGGING
# ==============================
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/dex.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("dex-scanner")

# ==============================
# FLASK APP
# ==============================
app = Flask(__name__)


# ==============================
# TELEGRAM SENDER
# ==============================
def send_telegram(text, chat_id=CHAT_ID):
    if not TELEGRAM_TOKEN:
        logger.warning("No TELEGRAM_TOKEN provided.")
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=10
        )
    except Exception as e:
        logger.error(f"Telegram send error: {e}")


# ==============================
# TELEGRAM COMMAND HANDLER
# ==============================
def handle_command(text, chat_id):
    t = text.lower().strip()

    if t in ["/start", "/help"]:
        msg = (
            "DEX Scanner (Solana + Base)\n\n"
            "Dostępne komendy:\n"
            "/start — opis\n"
            "/help — pomoc\n"
            "/stats — statystyki bota\n"
            "/top — ostatnie alerty\n"
        )
        send_telegram(msg, chat_id)
        return

    if t == "/stats":
        s = get_stats()
        msg = (
            f"Uptime: {s['uptime']}\n"
            f"Total alerts: {s['total_alerts']}\n"
            f"Today: {s['today_alerts']}\n"
            f"Last hour: {s['hour_alerts']}\n"
        )
        send_telegram(msg, chat_id)
        return

    if t == "/top":
        arr = get_last_alerts()
        if not arr:
            send_telegram("Brak alertów.", chat_id)
            return

        send_telegram("Ostatnie alerty:\n\n" + "\n".join(arr), chat_id)
        return


# ==============================
# WEBHOOK ENDPOINT
# ==============================
@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    data = request.json

    if not data or "message" not in data:
        return jsonify({"ok": True})

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")

    if text.startswith("/"):
        handle_command(text, chat_id)

    return jsonify({"ok": True})


# ==============================
# MANUAL SCAN TRIGGER
# ==============================
@app.route("/trigger_scan", methods=["POST"])
def trigger_scan():
    secret = request.headers.get("X-TRIGGER-SECRET") or request.args.get("secret")

    if secret != TRIGGER_SECRET:
        abort(403)

    found = run_scan_once()
    return jsonify({"ok": True, "found": found})


# ==============================
# HEALTH CHECK
# ==============================
@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": time.time()})


# ==============================
# RUN SERVER
# ==============================
if __name__ == "__main__":
    logger.info(f"Starting DEX scanner on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
