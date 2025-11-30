# DEX Scanner (Solana + Base)

## Co robi
- Skanuje DEXScreener token profiles i szuka nagłych wzrostów wolumenu / ruchu cenowego.
- Wysyła alerty do Telegrama.
- Działa jako web-service z /health (przydatne przy deployu na Railway).

## Pliki
- app.py — main
- requirements.txt
- Procfile

## Konfiguracja (lokalnie)
1. Stwórz plik `.env` (nie committuj go):
   TELEGRAM_TOKEN=123:ABC...
   CHAT_ID=123456789
   POLL_INTERVAL=60
   MIN_VOLUME_24H=300000
   VOLUME_SPIKE_RATIO=8.0
   PRICE_CHANGE_THRESHOLD=5.0
   CHAINS=solana,base

2. Instalacja:
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python app.py

3. Otwórz http://localhost:8080/health

## Deploy na Railway (szybki przewodnik)
1. Załóż repo na GitHub i push.
2. Zaloguj się na railway.app i stwórz nowy projekt -> Deploy from GitHub.
3. W settings projektu -> Variables dodaj wszystkie zmienne środowiskowe (TELEGRAM_TOKEN, CHAT_ID, ...). Railway obsługuje `PORT` automatycznie.
4. Wybierz branch i deploy — Railway uruchomi `web: python app.py` (Procfile) lub `python app.py`.
5. Sprawdź logi i endpoint /health.

## Rozszerzenia / next steps
- Dodać autoryzowane RPC / node provider (Alchemy/QuickNode) jeżeli chcesz pobierać on-chain swaps bezpośrednio.
- Dodać dedykowane zapytania do TheGraph (np. Uniswap V3 subgraph na Base) dla lepszych danych o poolach i swapach. :contentReference[oaicite:5]{index=5}
- Dodać retry/backoff i lepsze rate-limit handling (DEXScreener ma limity).

Źródła:
- DEXScreener API docs. :contentReference[oaicite:6]{index=6}
- Solana public RPC / uwagi. :contentReference[oaicite:7]{index=7}
- Railway variables i deploy guide. :contentReference[oaicite:8]{index=8}
