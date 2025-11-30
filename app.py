import os
import time
import threading
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify

# config from env
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")           # nie dodawaj klucza do repo
CHAT_ID = int(os.environ.get("CHAT_ID", "0"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))  # w sekundach
MIN_VOLUME_24H = float(os.environ.get("MIN_VOLUME_24H", "300000"))
VOLUME_SPIKE_RATIO = float(os.environ.get("VOLUME_SPIKE_RATIO", "8.0"))
PRICE_CHANGE_THRESHOLD = float(os.environ.get("PRICE_CHANGE_THRESHOLD", "5.0"))  # procent

# chains to monitor (dexscreener uses chain names like 'solana', 'ethereum' etc.)
CHAINS = os.environ.get("CHAINS", "solana,base").split(",")

# Dexscreener: token-profiles/latest/v1 endpoint (rate-limited)
DEXSCREENER_TOKEN_PROFILES = "https://api.dexscreener.com/token-profiles/latest/v1"

# internal state
seen_tokens = set()
last_alerts = []
total_alerts = 0
start_time = time.time()
last_heartbeat = time.time()

app = Flask(__name__)

def format_uptime(sec):
    return str(timedelta(seconds=int(sec))).split('.')[0]

def send_telegram(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Telegram not configured. Would send:", text)
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10
        )
    except Exception as e:
        print("Telegram send error:", e)

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "uptime": format_uptime(time.time() - start_time),
        "total_alerts": total_alerts,
        "last_heartbeat": datetime.fromtimestamp(last_heartbeat).isoformat()
    })

def heartbeat():
    global last_heartbeat
    last_heartbeat = time.time()
    send_telegram(f"DEX Scanner alive — uptime {format_uptime(time.time()-start_time)}\n{datetime.now().strftime('%d.%m %H:%M')}")

def fetch_token_profiles():
    """Pobiera token profiles z DEXScreener i zwraca listę tokenów"""
    try:
        r = requests.get(DEXSCREENER_TOKEN_PROFILES, timeout=15)
        if r.status_code != 200:
            print("Dexscreener returned", r.status_code)
            return []
        data = r.json()
        # struktura: zależy od aktualnej wersji API — zakładamy listę obiektów z polem 'chain'
        return data.get("results", []) if isinstance(data, dict) else data
    except Exception as e:
        print("fetch_token_profiles error:", e)
        return []

def process_profiles_for_chain(profiles, chain):
    """Filtruje profile dla danego chain i wykrywa potencjalne pompy"""
    global total_alerts, last_alerts, seen_tokens
    now = datetime.utcnow()
    alerts = []
    for p in profiles:
        try:
            # Zakładamy następujące pola (na podstawie dokumentacji DEXScreener):
            # p['chain'], p['symbol'], p['pair'], p['priceChange'], p['volume24h'], p['averageVolume24h']
            token_chain = (p.get("chain") or "").lower()
            if token_chain != chain.lower():
                continue

            symbol = p.get("symbol") or p.get("name") or "UNKNOWN"
            # volume fields may vary; robimy defensywnie
            vol24 = float(p.get("volume24h") or p.get("volume") or 0)
            avg24 = float(p.get("averageVolume24h") or p.get("avgVolume24h") or 0)
            price_change_24h = float(p.get("priceChange") or p.get("priceChange24h") or 0)

            # compute ratio defensively
            ratio = (vol24 / avg24) if avg24 > 0 else (vol24 / 1 if vol24 > 0 else 0)

            # detection logic: duży spike w stosunku do avg i > min vol i price change
            if vol24 >= MIN_VOLUME_24H and ratio >= VOLUME_SPIKE_RATIO and abs(price_change_24h) >= PRICE_CHANGE_THRESHOLD:
                key = f"{chain}:{symbol}"
                if key in seen_tokens:
                    continue
                seen_tokens.add(key)
                msg = f"<b>{symbol}</b> — chain: <i>{chain}</i>\nVol24h: {vol24:.0f} | avg: {avg24:.0f} | x{ratio:.1f}\nPrice change 24h: {price_change_24h:.1f}%\nDEXScreener: https://dexscreener.com/search?q={symbol}"
                send_telegram(msg)
                total_alerts += 1
                last_alerts.append(f"{datetime.utcnow().strftime('%H:%M')} | {symbol} | {chain} | x{ratio:.1f}")
                if len(last_alerts) > 20:
                    last_alerts.pop(0)
                alerts.append((symbol, chain, ratio, vol24, price_change_24h))
        except Exception as e:
            # ignorujemy błędy pojedynczych rekordów
            print("profile processing error:", e)
            continue
    return alerts

def scanner_loop():
    global last_heartbeat
    heartbeat()  # na start
    while True:
        try:
            profiles = fetch_token_profiles()
            if not profiles:
                print("No profiles fetched")
            for chain in CHAINS:
                alerts = process_profiles_for_chain(profiles, chain.strip())
                if alerts:
                    print(f"Alerts for {chain}: {len(alerts)}")
            # heartbeat co 30 minut
            if time.time() - last_heartbeat > 1800:
                heartbeat()
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            # błąd główny — wyślij info i poczekaj chwilę
            send_telegram(f"DEX Scanner błąd: {e}")
            print("Scanner exception:", e)
            time.sleep(30)

if __name__ == "__main__":
    # start scanner thread
    t = threading.Thread(target=scanner_loop, daemon=True)
    t.start()
    # run flask app (Railway expects a web server)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
