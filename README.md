# STOCK NEXUS — Nigerian & US Stock Intelligence Terminal
## Companion app to Forex Nexus

---

### Features
- **Nigerian Exchange (NGX)** — 20 NGX-listed stocks with live prices in ₦
- **US Markets** — 20 US stocks & ETFs (NYSE/NASDAQ) with live prices in $
- **Real-time price streaming** via yfinance batch download (10s refresh)
- **Full technical analysis** — RSI, MACD, Bollinger Bands, ADX, Stochastic, EMA, ATR
- **Structure-aware TP/SL** using real swing highs/lows
- **Signal Scanner** — scan all 40 stocks for high-confidence setups
- **Chart Vision (Local Model)** — upload any chart → similarity search against historical database → full analysis returned, no external API needed
- **Trade Journal** — track NGX & US positions with P&L, win rate, CSV export

---

### Setup

```bash
pip install -r requirements.txt

python app.py
# → http://localhost:5002
```

---

### Chart Vision — Local Model

No external API key needed. Instead, build the local database once:

```bash
# From the stock-nexus/ directory:
python model/build_db.py
```

This pulls 120 days of OHLCV history for all 40 stocks (~5 minutes), renders
candlestick chart images, computes all technical indicators, generates structured
analysis text, and stores everything in `model/trained/chart_retrieval.db`.

When you upload a chart in the app:
1. Your image is converted to a visual feature vector
2. Cosine similarity is computed against every chart in the DB
3. The most similar historical chart's analysis is returned
4. The result shows which stock/date it matched and the similarity score

To check DB status:
```bash
python model/build_db.py --status
```

---

### Architecture
```
yfinance (real OHLCV, batch, 10s refresh)
    │
    ├─→ compute_indicators() → RSI/MACD/ATR/BB/Stoch/ADX/EMA
    │                       → rule_based_signal() → direction + confidence
    │                       → swing_levels()      → TP1/TP2/SL from structure
    │
    ├─→ model/build_db.py   → render charts + generate analysis → SQLite DB
    ├─→ model/retrieval.py  → cosine similarity search on image vectors
    │
    ├─→ app.py /api/analyze        → full analysis JSON
    ├─→ app.py /api/scan           → quick signal scan all stocks
    ├─→ app.py /api/analyze_chart  → local retrieval model chart analysis
    ├─→ app.py /api/model_status   → DB ready check + stats
    └─→ templates/index.html + static/ → Dark terminal UI
```

---

### Port
Runs on **port 5002** (Forex Nexus runs on 5001, no conflict).

