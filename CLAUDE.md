# CLAUDE.md — Stock Nexus Project

## This Repo IS the Deployment
`Xomie1/Nexus-Stock` → Render auto-deploys on every push to `main`
Live: https://nexus-stock-ty2t.onrender.com/

## Push Workflow (You Have Direct Access Here)
```bash
git add -A && git commit -m "your message" && git push origin main
```

## File Structure (Flat at Root)
app.py · static/css/style.css · static/js/app.js · templates/index.html
requirements.txt · runtime.txt · Procfile · render.yaml · model/

## Stack
Flask + gevent SSE · yfinance OHLCV · Google News RSS
29 EU + 20 Asian + 76 US stocks = 125 total
No database — all in-memory + localStorage

## Current Version: v4
- Auto paper trading: strong signals (≥65% conf) auto-logged every scan
- Paper trade win/loss detected on each price tick (TP1 or SL hit)
- Accuracy tracker in TRADE journal tab (live win rate %)
- Visual profit meter: SL ←→ ENTRY ←→ TP1 ←→ TP2 bar
- Risk gauge hint explains balance × risk% mechanics
- Trade brief card redesigned (bigger, cleaner)
- Morning brief on dashboard (top longs/shorts)
- Auto-scan every 5 min + on page load

## API Routes
/api/seed · /api/stream (SSE) · /api/analyze · /api/scan
/api/brief · /api/signal_history · /api/analyze_chart

## User Goals
Trade EU/Asian/US stocks from €100 via Trading 212
Signals: LONG/SHORT with entry, SL, TP1, TP2, R:R, confidence
Paper trading auto-tracks accuracy before real money

## Next Up (User's Priority List)
1. SL/TP price alerts (toast notification when price approaches)
2. Backtest tab (historical signal performance)
3. News API upgrade (beyond Google RSS)
4. More visual dashboard (charts, sparklines)
