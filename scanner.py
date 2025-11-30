import requests
import time
from datetime import datetime, timedelta
from filters import is_probable_honeypot

# ==============================
# GLOBALS
# ==============================
start_time = time.time()
total_alerts = 0
today_alerts = 0
hour_alerts = 0
last_alerts = []
seen_alerts = set()

# ==============================
# HELPERS
# ==============================
def format_uptime(sec):
    return str(timedelta(seconds=int(sec))).split('.')[0]

def get_stats():
    return {
        "uptime": format_uptime(time.time() - start_time),
        "total_alerts": total_alerts,
        "today_alerts": today_alerts,
        "hour_alerts": hour_alerts
    }

def get_last_alerts():
    return last_alerts[-10:]


# ==============================
# SCAN FUNCTION
# ==============================
def run_scan_once():
    """
    Pobiera listę tokenów z DEX Solana/Base
    Sprawdza wolumeny i zmiany ceny
    Filtrowanie honeypotów
    Zwraca listę nowych alertów
    """
    global total_alerts, today_alerts, hour_alerts

    # przykładowe źródło DEX Screener API (Solana/Base)
    urls = [
        "https://api.dexscreener.com/latest/dex/tokens/solana",
        "https://api.dexscreener.com/latest/dex/tokens/base"
    ]

    new_alerts = []

    for url in urls:
        try:
            resp = requests.get(url, timeout=10).json()
            pairs = resp.get("pairs", [])
        except Exception:
            continue

        for p in pairs:
            try:
                base = p.get("baseToken", {}).get("symbol")
                price_now = float(p.get("priceUsd") or 0)
                vol24 = float(p.get("volume24h") or p.get("volume") or 0)

                if not base or vol24 == 0:
                    continue

                # prosty filtr pumpy
                price_change = float(p.get("priceChangePercent") or 0)
                if vol24 > 100_000 and price_change > 5 and not is_probable_honeypot(p):
                    if base in seen_alerts:
                        continue
                    seen_alerts.add(base)

                    msg = f"{base} | Vol24: {vol24:.0f} USD | ΔPrice: {price_change:.1f}%\nhttps://dexscreener.com/search?q={base}"
                    new_alerts.append(msg)

                    total_alerts += 1
                    today_alerts += 1
                    hour_alerts += 1
                    last_alerts.append(f"{datetime.now().strftime('%H:%M')} | {base} | Vol24: {vol24:.0f} | ΔPrice: {price_change:.1f}%")

            except Exception:
                continue

    return new_alerts
