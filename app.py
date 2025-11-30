# app.py
f"Uptime: {stats['uptime']}\n"
f"Total alerts: {stats['total_alerts']}\n"
f"Today alerts: {stats['today_alerts']}\n"
f"Hour alerts: {stats['hour_alerts']}\n"
)
send_telegram(text, chat_id)
elif cmd == "/top":
last = get_last_alerts()
if not last:
send_telegram("Brak alertów jeszcze.", chat_id)
else:
send_telegram("Ostatnie alerty:\n\n" + "\n".join(last), chat_id)
else:
send_telegram("Nieznana komenda. Użyj /help.", chat_id)


# -------- webhook endpoint for Telegram --------


@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
"""Telegram will POST updates here."""
try:
data = request.get_json(force=True)
logger.info("Received update: %s", data.get('update_id'))
# handle messages only
if "message" in data:
msg = data["message"]
chat_id = msg["chat"]["id"]
text = msg.get("text", "")
if text and text.startswith("/"):
handle_command(text.split()[0], chat_id)
else:
send_telegram("Bot obsługuje tylko komendy. Użyj /help.", chat_id)
return jsonify({"ok": True})
except Exception as e:
logger.exception("Error in webhook: %s", e)
return jsonify({"ok": False, "error": str(e)}), 500


# -------- manual trigger endpoint (protected by TRIGGER_SECRET) --------


@app.route("/trigger_scan", methods=["POST"])
def trigger_scan():
secret = request.headers.get("X-TRIGGER-SECRET") or request.args.get("secret")
if not TRIGGER_SECRET:
logger.warning("TRIGGER_SECRET not set — rejecting manual trigger")
abort(403)
if not secret or secret != TRIGGER_SECRET:
abort(403)
# run a scan synchronously and return result
logger.info("Manual scan triggered")
alerts = run_scan_once()
return jsonify({"status": "ok", "alerts": alerts})


# -------- health and misc endpoints --------


@app.route("/health")
def health():
stats = get_stats()
return jsonify({"status": "ok", "stats": stats})


# -------- heartbeat thread (periodic message to admin chat) --------


def heartbeat_loop():
while True:
try:
send_telegram(f"DEX Scanner alive — uptime {get_stats()['uptime']}")
except Exception as e:
logger.exception("Heartbeat error: %s", e)
time.sleep(HEARTBEAT_INTERVAL)


if __name__ == "__main__":
# start heartbeat thread
if TELEGRAM_TOKEN and CHAT_ID and os.environ.get("ENABLE_HEARTBEAT", "1") == "1":
t_hb = threading.Thread(target=heartbeat_loop, daemon=True)
t_hb.start()
# start Flask
logger.info("Starting app on port %s — webhook path: %s", PORT, WEBHOOK_PATH)
app.run(host="0.0.0.0", port=PORT)
