# CLAUDE.md — Stock Nexus Project

## What This Is
**Stock Nexus** — a Flask equity intelligence terminal for EU, Asian, and US stocks.
This repo (`Xomie1/Nexus-Stock`) IS the live deployment repo.

- **Live site:** https://nexus-stock-ty2t.onrender.com/
- **Deployment:** Render free tier — pushing to `main` here triggers auto-redeploy (~3 min)
- **Backup/dev repo:** `Xomie1/Nexus-Stock-AI` (ignore — old sessions pushed there by mistake)

## Push Workflow (This Session Has Direct Access)
```bash
git add -A
git commit -m "your message"
git push origin main
# Render redeploys automatically
```

## File Structure (Flat — All at Repo Root)
```
Nexus-Stock/
├── app.py                  # Flask backend — all API routes, stock data, indicators
├── static/css/style.css    # Dark terminal UI styles
├── static/js/app.js        # Frontend JS — all pages, SSE, charting
├── templates/index.html    # Single-page HTML shell
├── requirements.txt        # Python deps
├── runtime.txt             # python-3.11.9 (pins Render Python version)
├── Procfile                # web: python app.py
├── render.yaml             # Render config
└── model/                  # ML models (optional — site works without them)
    ├── train_model.py
    ├── build_db.py
    └── retrieval.py
```

## Tech Stack
- **Backend:** Flask + gevent SSE streaming, yfinance (real OHLCV data), Google News RSS
- **Frontend:** Vanilla JS, no framework, dark terminal aesthetic (Rajdhani/JetBrains Mono/Bebas Neue)
- **Markets:** 29 EU stocks, 20 Asian stocks, 76 US stocks/ETFs = 125 total
- **Currencies:** GBP(p), EUR(€), JPY(¥), HKD(HK$), INR(₹), KRW(₩), CHF(Fr), DKK(kr), USD($)
- **No database** — yfinance has years of real history, no Supabase needed

## Pages (7-page SPA)
| Nav | Page | Key Feature |
|-----|------|-------------|
| DASH | Dashboard | KPIs, morning brief (top longs/shorts), movers, heatmap |
| EU/AS | EU/Asia Markets | 49 stocks table with live prices |
| NYSE | US Markets | 76 stocks/ETFs table |
| SIGNAL | Predictor | Trade brief card (LONG/SHORT + entry/SL/TP/R:R + why bullets) |
| SCAN | Scanner | Full scan + signal history log |
| VISION | Chart AI | Upload chart → similarity match |
| TRADE | Journal | P&L tracker, localStorage, CSV export |

## API Routes
| Route | Method | What It Does |
|-------|--------|-------------|
| `/api/seed` | GET | Bootstrap all stocks + seed prices |
| `/api/stream` | GET | SSE real-time price ticks (every 15-30s) |
| `/api/analyze` | POST | Full analysis → trade brief + indicators + news |
| `/api/scan` | POST | Scan all stocks, return high-confidence setups |
| `/api/brief` | GET | Daily top 4 longs + 4 shorts with entry/SL/TP |
| `/api/signal_history` | GET | In-memory log of tradeable signals this session |
| `/api/analyze_chart` | POST | Chart image upload → AI similarity analysis |

## What the Trade Brief Card Looks Like
When a user analyzes a stock on the SIGNAL page:
```
[ LONG ]                              CONFIDENCE: 71%
✓ REAL CANDLE DATA
████████████░░

ENTRY        STOP LOSS      TARGET 1         TARGET 2
€780.50      €762.00        €810.00          €845.00
market price  −2.4% risk    +3.8% · R:R 1.6  +8.3% · R:R 3.4

WHY THIS SIGNAL:
▸ RSI oversold at 31 — recovery expected
▸ MACD bullish cross
▸ Volume 1.8× avg — institutional buying
▸ News: 2 bullish headlines (score +1.8)

[ + ADD LONG TO JOURNAL ]
```

## Auto Features (No User Action Needed)
- **Auto-scan:** Runs 2s after page load, then every 5 min silently
- **Nav badge:** Shows live bull/bear count (e.g. "SCAN 4▲ 2▼")
- **Morning brief:** Auto-loads on dashboard, refreshes every 10 min
- **Signal history:** Logs every tradeable signal to scanner page

## User Goals
- Get clear LONG/SHORT signals with entry, stop, TP confidence %
- Trade EU + Asian + US stocks starting with ~€100 via Trading 212 (fractional shares)
- Scale up once signals prove reliable
- Eventually: paper trading auto-log, SL/TP alerts, backtest tab

## Known Limitations
- ML (XGBoost/LSTM) models not trained — signals use rule-based engine (works fine)
- Chart Vision AI needs `python model/build_db.py` run once to populate DB
- News = Google RSS + keyword scoring (basic but functional)
- Render free tier sleeps after 15 min — set up UptimeRobot to ping every 5 min

## UptimeRobot Keep-Alive (Important)
Go to uptimerobot.com → Add Monitor → HTTP → `https://nexus-stock-ty2t.onrender.com` → every 5 min
Without this the app sleeps and auto-scan never fires.

## Current Version: v3
Latest changes committed and pushed:
- Trade brief card (LONG/SHORT/WAIT) at top of predictor
- `/api/brief` — daily morning briefing on dashboard
- `/api/signal_history` — tradeable signal log
- `_build_why_bullets()` — 5-bullet reasoning per signal
- Python 3.11.9 pinned via runtime.txt (fixes Render build)
- Page navigation fix (CSS specificity bug resolved)
- Auto-scan with silent mode + nav badge
