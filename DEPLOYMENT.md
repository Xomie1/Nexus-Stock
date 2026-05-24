# STOCK NEXUS — Deployment Guide

## Live Site
Deployed on Render: https://nexus-stock-ty2t.onrender.com/

---

## Render Configuration

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
python app.py
```

**Python Version:** 3.11 (set in Render dashboard or via `runtime.txt`)

---

## Project Structure

```
Nexus-Stock/
├── app.py                  ← Main Flask server (EU/Asian + US stocks)
├── predictor.py            ← ML prediction engine (XGBoost + LSTM)
├── retrain_scheduler.py    ← Weekly auto-retraining (Sunday 02:00 UTC)
├── database.py             ← Supabase integration (optional)
├── requirements.txt        ← Python dependencies
├── render.yaml             ← Render deployment config
├── Procfile                ← Start command backup
├── .env.example            ← Environment variable template
│
├── static/
│   ├── css/style.css       ← Terminal UI styling
│   └── js/app.js           ← Frontend JavaScript
│
├── templates/
│   └── index.html          ← Main HTML page
│
└── model/
    ├── train_model.py      ← Offline model training script
    ├── retrieval.py        ← Chart image retrieval model
    └── build_db.py         ← Chart database builder
```

---

## Stock Universe

| Market | Stocks | Data Source | Currency |
|--------|--------|-------------|----------|
| 🌍 European | 29 stocks (LSE, CAC40, DAX, SIX, AEX, OMXC, MIB) | yfinance | GBP, EUR, CHF, DKK |
| 🌏 Asian | 20 stocks (TSE, HKEX, NSE, KRX + US ADRs) | yfinance | JPY, HKD, INR, KRW, USD |
| 🇺🇸 US | 76 stocks + ETFs (NYSE/NASDAQ) | yfinance | USD |

---

## Environment Variables (Optional)

Copy `.env.example` to `.env` and fill in values for Supabase persistence:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

Without these, the app runs fine — data just resets on each restart.

---

## Local Development

```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:5002
```
