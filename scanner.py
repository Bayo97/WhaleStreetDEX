# scanner.py
symbol = p.get("symbol") or p.get("name") or "UNKNOWN"
try:
vol24 = float(p.get("volume24h") or p.get("volume") or 0)
except:
vol24 = 0
try:
avg24 = float(p.get("averageVolume24h") or p.get("avgVolume24h") or 0)
except:
avg24 = 0
try:
price_change_24h = float(p.get("priceChange") or p.get("priceChange24h") or 0)
except:
price_change_24h = 0


ratio = (vol24 / avg24) if avg24 > 0 else (vol24 / 1 if vol24 > 0 else 0)


# must be on monitored chain
if chain not in [c.lower() for c in CHAINS]:
return None


# basic thresholds
if vol24 < MIN_VOLUME_24H:
return None
if ratio < VOLUME_SPIKE_RATIO:
return None
if abs(price_change_24h) < PRICE_CHANGE_THRESHOLD:
return None


# honeypot / scam heuristics (especially for Solana) — if flagged, skip
address = p.get("address") or p.get("tokenAddress") or None
if chain == 'solana' and address:
try:
if is_probable_honeypot(address):
logger.info("Filtered probable honeypot: %s (%s)", symbol, address)
return None
except Exception as e:
logger.exception("Honeypot check error: %s", e)


return {
"symbol": symbol,
"chain": chain,
"ratio": ratio,
"vol24": vol24,
"price_change_24h": price_change_24h,
"address": address
}


# run one scan and return list of alerts


def run_scan_once():
global _total_alerts, _today_alerts, _hour_alerts
profiles = fetch_profiles()
alerts = []
now = _now_ts()


# simple rate limiter for alerts per minute
# count alerts in last 60s
recent_alerts = [t for t in _last_alerts if isinstance(t, str) and t]
# we keep time in entries? to allow simple rate limiting we will use _seen times
last_min_count = len([1 for ts in _seen.values() if now - ts <= 60])
for p in profiles:
try:
info = _detect_profile(p)
