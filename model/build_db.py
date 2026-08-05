"""
STOCK NEXUS — Chart Retrieval Database Builder
================================================
Pulls 120 days of OHLCV for all 40 stocks, renders candlestick chart images,
computes technical indicators, generates analysis text, and stores everything
in a SQLite database for similarity-based chart retrieval.

Usage:
    python model/build_db.py              # build / update DB
    python model/build_db.py --status     # show DB stats
"""

import argparse, io, json, os, sqlite3, sys, time, warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from PIL import Image

# ── ensure model/ directory is on path so ngx_scraper is importable ──────────
_MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
if _MODEL_DIR not in sys.path:
    sys.path.insert(0, _MODEL_DIR)

# ── paths ─────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_DIR, "trained", "chart_retrieval.db")
os.makedirs(os.path.join(BASE_DIR, "trained"), exist_ok=True)

# ── stock universe (mirrors app.py) ──────────────────────────────────────────
NIGERIAN_STOCKS = [
    # Yahoo Finance has no NGX data — yf is None for all NGX stocks.
    # OHLCV is generated via synthetic random walk from seed prices.
    # Full list loaded dynamically from ngx_scraper; this is the fallback.
    {"id":"DANGCEM",    "name":"Dangote Cement",       "sector":"Materials",    "currency":"NGN","yf":None},
    {"id":"MTNN",       "name":"MTN Nigeria",           "sector":"Telecom",      "currency":"NGN","yf":None},
    {"id":"AIRTELAFRI", "name":"Airtel Africa",         "sector":"Telecom",      "currency":"NGN","yf":None},
    {"id":"GTCO",       "name":"GT Co Holding",         "sector":"Finance",      "currency":"NGN","yf":None},
    {"id":"ZENITHBANK", "name":"Zenith Bank",           "sector":"Finance",      "currency":"NGN","yf":None},
    {"id":"ACCESSCORP", "name":"Access Holdings",       "sector":"Finance",      "currency":"NGN","yf":None},
    {"id":"UBA",        "name":"United Bank Africa",    "sector":"Finance",      "currency":"NGN","yf":None},
    {"id":"SEPLAT",     "name":"Seplat Energy",         "sector":"Energy",       "currency":"NGN","yf":None},
    {"id":"STANBIC",    "name":"Stanbic IBTC",          "sector":"Finance",      "currency":"NGN","yf":None},
    {"id":"BUACEMENT",  "name":"BUA Cement",            "sector":"Materials",    "currency":"NGN","yf":None},
    {"id":"BUAFOODS",   "name":"BUA Foods",             "sector":"Consumer",     "currency":"NGN","yf":None},
    {"id":"NESTLE",     "name":"Nestle Nigeria",        "sector":"Consumer",     "currency":"NGN","yf":None},
    {"id":"FLOURMILL",  "name":"Flour Mills",           "sector":"Consumer",     "currency":"NGN","yf":None},
    {"id":"TRANSCORP",  "name":"Transcorp",             "sector":"Conglomerate", "currency":"NGN","yf":None},
    {"id":"FIDELITYBK", "name":"Fidelity Bank",         "sector":"Finance",      "currency":"NGN","yf":None},
    {"id":"FIRSTHOLDCO","name":"First Bank HoldCo",     "sector":"Finance",      "currency":"NGN","yf":None},
    {"id":"CONOIL",     "name":"Conoil",                "sector":"Energy",       "currency":"NGN","yf":None},
    {"id":"OKOMUOIL",   "name":"Okomu Oil",             "sector":"Agriculture",  "currency":"NGN","yf":None},
    {"id":"PRESCO",     "name":"Presco",                "sector":"Agriculture",  "currency":"NGN","yf":None},
    {"id":"TOTAL",      "name":"TotalEnergies Nigeria", "sector":"Energy",       "currency":"NGN","yf":None},
]

# Try loading full universe from scraper
try:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ngx_scraper import build_stock_list as _ngx_list, build_seed_prices as _ngx_seeds
    NIGERIAN_STOCKS = _ngx_list()
    print(f"[NGX] Loaded {len(NIGERIAN_STOCKS)} stocks from scraper universe")
except Exception as _e:
    print(f"[NGX] Using fallback 20-stock list ({_e})")
US_STOCKS = [
    {"id":"AAPL",  "name":"Apple Inc",           "sector":"Technology",     "currency":"USD","yf":"AAPL"},
    {"id":"MSFT",  "name":"Microsoft Corp",       "sector":"Technology",     "currency":"USD","yf":"MSFT"},
    {"id":"NVDA",  "name":"NVIDIA Corp",          "sector":"Technology",     "currency":"USD","yf":"NVDA"},
    {"id":"GOOGL", "name":"Alphabet Inc",         "sector":"Technology",     "currency":"USD","yf":"GOOGL"},
    {"id":"AMZN",  "name":"Amazon.com Inc",       "sector":"Consumer",       "currency":"USD","yf":"AMZN"},
    {"id":"META",  "name":"Meta Platforms",       "sector":"Technology",     "currency":"USD","yf":"META"},
    {"id":"TSLA",  "name":"Tesla Inc",            "sector":"EV/Auto",        "currency":"USD","yf":"TSLA"},
    {"id":"BRK-B", "name":"Berkshire Hathaway B", "sector":"Finance",        "currency":"USD","yf":"BRK-B"},
    {"id":"JPM",   "name":"JPMorgan Chase",       "sector":"Finance",        "currency":"USD","yf":"JPM"},
    {"id":"V",     "name":"Visa Inc",             "sector":"Finance",        "currency":"USD","yf":"V"},
    {"id":"JNJ",   "name":"Johnson & Johnson",    "sector":"Healthcare",     "currency":"USD","yf":"JNJ"},
    {"id":"XOM",   "name":"Exxon Mobil",          "sector":"Energy",         "currency":"USD","yf":"XOM"},
    {"id":"WMT",   "name":"Walmart Inc",          "sector":"Consumer",       "currency":"USD","yf":"WMT"},
    {"id":"SPY",   "name":"S&P 500 ETF",          "sector":"ETF",            "currency":"USD","yf":"SPY"},
    {"id":"QQQ",   "name":"Nasdaq 100 ETF",       "sector":"ETF",            "currency":"USD","yf":"QQQ"},
    {"id":"GLD",   "name":"Gold ETF",             "sector":"ETF",            "currency":"USD","yf":"GLD"},
    {"id":"NFLX",  "name":"Netflix Inc",          "sector":"Media",          "currency":"USD","yf":"NFLX"},
    {"id":"DIS",   "name":"Walt Disney Co",       "sector":"Media",          "currency":"USD","yf":"DIS"},
    {"id":"BAC",   "name":"Bank of America",      "sector":"Finance",        "currency":"USD","yf":"BAC"},
    {"id":"COIN",  "name":"Coinbase Global",      "sector":"Crypto/Finance", "currency":"USD","yf":"COIN"},
]
ALL_STOCKS = NIGERIAN_STOCKS + US_STOCKS

# ══════════════════════════════════════════════════════════════════════════════
# INDICATORS  (self-contained, no app.py import needed)
# ══════════════════════════════════════════════════════════════════════════════

def _ema(s, p):   return s.ewm(span=p, adjust=False).mean()
def _rsi(s, p=14):
    d = s.diff(); g = d.clip(lower=0).rolling(p).mean()
    l = (-d.clip(upper=0)).rolling(p).mean()
    return 100 - 100 / (1 + g / (l + 1e-9))
def _atr(h, l, c, p=14):
    tr = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    return tr.rolling(p).mean()
def _macd(c, f=12, sl=26, sig=9):
    ml = _ema(c,f) - _ema(c,sl); s = _ema(ml,sig); return ml, s, ml-s
def _bollinger(c, p=20, k=2):
    m = c.rolling(p).mean(); s = c.rolling(p).std()
    up, lo = m+k*s, m-k*s
    return up, m, lo, (c-lo)/(up-lo+1e-9)
def _stoch(h, l, c, k=14, d=3):
    K = 100*(c-l.rolling(k).min())/(h.rolling(k).max()-l.rolling(k).min()+1e-9)
    return K, K.rolling(d).mean()
def _adx(h, l, c, p=14):
    up=h.diff(); dn=-l.diff()
    pdm=np.where((up>dn)&(up>0),up,0.0); mdm=np.where((dn>up)&(dn>0),dn,0.0)
    tr_s=_atr(h,l,c,p)
    pdi=100*pd.Series(pdm,index=h.index).rolling(p).mean()/(tr_s+1e-9)
    mdi=100*pd.Series(mdm,index=h.index).rolling(p).mean()/(tr_s+1e-9)
    dx=100*(pdi-mdi).abs()/(pdi+mdi+1e-9)
    return dx.rolling(p).mean(), pdi, mdi

def compute_indicators(df):
    c,h,l,v,o = df["Close"],df["High"],df["Low"],df["Volume"],df["Open"]
    rsi14=_rsi(c,14); rsi7=_rsi(c,7)
    ml,sl_,hist=_macd(c)
    bb_up,bb_mid,bb_lo,pct_b=_bollinger(c)
    atr14=_atr(h,l,c,14)
    ema9=_ema(c,9); ema21=_ema(c,21); ema50=_ema(c,50); ema200=_ema(c,200)
    k_,d_=_stoch(h,l,c)
    adx_,pdi,mdi=_adx(h,l,c)
    v_ma20=v.rolling(20).mean()
    def last(s):
        v2=s.dropna(); return float(v2.iloc[-1]) if len(v2)>0 else 0.0
    price=last(c); atr_v=last(atr14)
    # candle
    body=abs(float(c.iloc[-1])-float(o.iloc[-1]))
    rng=max(float(h.iloc[-1])-float(l.iloc[-1]),1e-9)
    uw=(float(h.iloc[-1])-max(float(c.iloc[-1]),float(o.iloc[-1])))/rng
    lw=(min(float(c.iloc[-1]),float(o.iloc[-1]))-float(l.iloc[-1]))/rng
    br=body/rng
    if br<0.1: candle="DOJI"
    elif lw>0.6 and uw<0.15: candle="HAMMER"
    elif uw>0.6 and lw<0.15: candle="SHOOTING STAR"
    else: candle="BULLISH BAR" if float(c.iloc[-1])>float(o.iloc[-1]) else "BEARISH BAR"
    return {
        "rsi":round(last(rsi14),1),"rsi_7":round(last(rsi7),1),
        "macd":"BULLISH" if last(ml)>last(sl_) else "BEARISH",
        "macd_line":round(last(ml),4),"macd_hist":round(last(hist),4),
        "bb_pct":round(last(pct_b)*100,1),"bb_upper":round(last(bb_up),2),"bb_lower":round(last(bb_lo),2),
        "atr":round(atr_v/price*100 if price>0 else 0,4),"atr_raw":round(atr_v,2),
        "ema9":round(last(ema9),2),"ema21":round(last(ema21),2),
        "ema50":round(last(ema50),2),"ema200":round(last(ema200),2),
        "stoch_k":round(last(k_),1),"stoch_d":round(last(d_),1),
        "adx":round(last(adx_),1),"plus_di":round(last(pdi),1),"minus_di":round(last(mdi),1),
        "vol_ratio":round(last(v)/( last(v_ma20)+1e-9),2),"candle":candle,"price":round(price,2),
    }

def swing_levels(df):
    h=df["High"].values; l=df["Low"].values; sw=5
    highs,lows=[],[]
    for i in range(sw,len(h)-sw):
        if h[i]==max(h[i-sw:i+sw+1]): highs.append(float(h[i]))
        if l[i]==min(l[i-sw:i+sw+1]): lows.append(float(l[i]))
    return sorted(set(highs)), sorted(set(lows),reverse=True)

def rule_based_signal(ind, ch):
    b=br=0
    rsi=ind["rsi"]; macd=ind["macd"]; bb=ind["bb_pct"]
    stoch=ind["stoch_k"]; adx=ind["adx"]
    if rsi<30: b+=3
    elif rsi>70: br+=3
    elif rsi<50: b+=1
    else: br+=1
    if macd=="BULLISH": b+=3
    else: br+=3
    if bb<20: b+=2
    elif bb>80: br+=2
    if stoch<20: b+=2
    elif stoch>80: br+=2
    if ch>1: b+=2
    elif ch<-1: br+=2
    T=b+br; bp=round(b/T*100) if T else 50
    direction="BULLISH" if bp>=60 else "BEARISH" if bp<=40 else "NEUTRAL"
    conf=round(min(88,max(20,abs(bp-50)*2.2)))
    if adx<18 and direction!="NEUTRAL" and conf<55:
        direction="NEUTRAL"; conf=round(conf*0.6)
    return direction, conf, bp

# ══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC OHLCV FOR NGX (Yahoo Finance has no NGX data)
# ══════════════════════════════════════════════════════════════════════════════

# Seed prices mirror app.py NG_SEEDS
# ── NGX seed prices — load from scraper, fallback to hardcoded ───────────────
try:
    from ngx_scraper import build_seed_prices as _ngx_seed_fn
    NG_SEEDS = {k: {"price": v["price"], "vol": v["vol"]} for k, v in _ngx_seed_fn().items()}
except Exception:
    NG_SEEDS = {
        "DANGCEM":     {"price": 810.0,  "vol": 1_240_000},
        "MTNN":        {"price": 760.0,  "vol": 2_100_000},
        "AIRTELAFRI":  {"price": 2497.0, "vol":   320_000},
        "GTCO":        {"price": 120.95, "vol": 8_800_000},
        "ZENITHBANK":  {"price": 103.0,  "vol":12_000_000},
        "ACCESSCORP":  {"price":  26.0,  "vol":25_000_000},
        "UBA":         {"price":  46.15, "vol":18_000_000},
        "SEPLAT":      {"price": 9099.9, "vol":   180_000},
        "STANBIC":     {"price": 133.1,  "vol":   620_000},
        "BUACEMENT":   {"price": 326.7,  "vol":   550_000},
        "BUAFOODS":    {"price": 798.0,  "vol":   490_000},
        "NESTLE":      {"price": 3055.5, "vol":    85_000},
        "FLOURMILL":   {"price":  54.0,  "vol": 1_200_000},
        "TRANSCORP":   {"price":  48.0,  "vol": 5_000_000},
        "FIDELITYBK":  {"price":  19.25, "vol":22_000_000},
        "FIRSTHOLDCO": {"price":  50.0,  "vol":16_000_000},
        "CONOIL":      {"price": 204.4,  "vol":   380_000},
        "OKOMUOIL":    {"price": 1765.0, "vol":    95_000},
        "PRESCO":      {"price": 1980.0, "vol":    67_000},
        "TOTAL":       {"price": 640.0,  "vol":   120_000},
    }

def synthetic_ohlcv(stock_id, n_days=120, seed=None):
    """
    Generate n_days of realistic synthetic OHLCV for an NGX stock.
    Uses a biased random walk with realistic daily volatility (0.5-2%).
    Includes periodic trend reversals to produce varied chart patterns.
    """
    rng = np.random.default_rng(seed if seed is not None else abs(hash(stock_id)) % (2**31))
    s = NG_SEEDS.get(stock_id, {"price": 100.0, "vol": 1_000_000})
    base_price = s["price"]
    base_vol   = s["vol"]

    # daily vol between 0.8% and 2% of price (NGX stocks are less liquid)
    daily_vol_pct = rng.uniform(0.008, 0.020)

    prices = [base_price]
    # generate random walk with slight mean-reversion tendency
    trend_bias = rng.choice([-1, 0, 1], p=[0.3, 0.4, 0.3])  # -1=bear,0=flat,1=bull
    for i in range(1, n_days):
        # flip trend every 20-40 days
        if i % rng.integers(20, 40) == 0:
            trend_bias = rng.choice([-1, 0, 1], p=[0.3, 0.4, 0.3])
        sigma = prices[-1] * daily_vol_pct
        drift = trend_bias * prices[-1] * 0.0008
        change = drift + rng.normal(0, sigma)
        new_price = max(prices[-1] * 0.90, prices[-1] + change)  # floor at -10% single day
        prices.append(round(new_price, 2))

    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n_days)

    rows = []
    for i, (dt, close) in enumerate(zip(dates, prices)):
        open_  = prices[i-1] if i > 0 else close
        spread = close * rng.uniform(0.005, 0.025)
        high   = round(max(open_, close) + spread * rng.uniform(0.2, 0.8), 2)
        low    = round(min(open_, close) - spread * rng.uniform(0.2, 0.8), 2)
        low    = max(low, close * 0.90)
        vol    = int(base_vol * rng.uniform(0.4, 2.2))
        rows.append({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol})

    df = pd.DataFrame(rows, index=dates)
    df.index.name = "Date"
    return df

# ══════════════════════════════════════════════════════════════════════════════
# CHART RENDERER
# ══════════════════════════════════════════════════════════════════════════════

def render_chart(df, stock_id, indicators, size=(224, 224)):
    """Render a candlestick chart + indicator overlays as a PNG bytes blob."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.gridspec import GridSpec

        # Use last 30 candles for the chart window
        plot_df = df.tail(30).copy()
        dates = list(range(len(plot_df)))
        opens  = plot_df["Open"].values
        highs  = plot_df["High"].values
        lows   = plot_df["Low"].values
        closes = plot_df["Close"].values
        vols   = plot_df["Volume"].values

        fig = plt.figure(figsize=(4, 4), dpi=56, facecolor="#0d1117")
        gs  = GridSpec(3, 1, figure=fig, hspace=0.05,
                       height_ratios=[3, 1, 1])
        ax1 = fig.add_subplot(gs[0])  # price
        ax2 = fig.add_subplot(gs[1], sharex=ax1)  # volume
        ax3 = fig.add_subplot(gs[2], sharex=ax1)  # RSI

        # ── candles ──
        for i, (o, h, l, c) in enumerate(zip(opens, highs, lows, closes)):
            color = "#26a69a" if c >= o else "#ef5350"
            ax1.plot([i, i], [l, h], color=color, linewidth=0.6)
            ax1.add_patch(mpatches.Rectangle(
                (i - 0.3, min(o, c)), 0.6, abs(c - o),
                facecolor=color, edgecolor=color, linewidth=0))

        # ── EMAs ──
        c_series = plot_df["Close"]
        for span, col in [(9, "#ffeb3b"), (21, "#ff9800"), (50, "#2196f3")]:
            ema = c_series.ewm(span=span, adjust=False).mean().values
            ax1.plot(dates, ema, color=col, linewidth=0.7, alpha=0.8)

        # ── Bollinger ──
        m20 = c_series.rolling(20).mean(); s20 = c_series.rolling(20).std()
        ax1.fill_between(dates, (m20+2*s20).values, (m20-2*s20).values,
                         alpha=0.07, color="#9c27b0")

        ax1.set_facecolor("#0d1117"); ax1.tick_params(colors="#666", labelsize=4)
        for sp in ax1.spines.values(): sp.set_color("#222")
        plt.setp(ax1.get_xticklabels(), visible=False)

        # ── volume ──
        vcols = ["#26a69a" if closes[i] >= opens[i] else "#ef5350"
                 for i in range(len(dates))]
        ax2.bar(dates, vols, color=vcols, alpha=0.7, width=0.7)
        ax2.set_facecolor("#0d1117"); ax2.tick_params(colors="#666", labelsize=4)
        for sp in ax2.spines.values(): sp.set_color("#222")
        plt.setp(ax2.get_xticklabels(), visible=False)

        # ── RSI ──
        rsi_vals = pd.Series(closes).diff()
        g = rsi_vals.clip(lower=0).rolling(14).mean()
        l_r = (-rsi_vals.clip(upper=0)).rolling(14).mean()
        rsi_line = (100 - 100 / (1 + g / (l_r + 1e-9))).values
        ax3.plot(dates, rsi_line, color="#e91e63", linewidth=0.8)
        ax3.axhline(70, color="#ef5350", linewidth=0.4, linestyle="--", alpha=0.6)
        ax3.axhline(30, color="#26a69a", linewidth=0.4, linestyle="--", alpha=0.6)
        ax3.set_ylim(0, 100)
        ax3.set_facecolor("#0d1117"); ax3.tick_params(colors="#666", labelsize=4)
        for sp in ax3.spines.values(): sp.set_color("#222")

        plt.tight_layout(pad=0.1)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight",
                    facecolor="#0d1117", dpi=56)
        plt.close(fig)
        buf.seek(0)
        # Resize to exactly size
        img = Image.open(buf).convert("RGB").resize(size, Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
    except Exception as e:
        print(f"  [CHART] render error: {e}")
        return None

# ══════════════════════════════════════════════════════════════════════════════
# ANALYSIS TEXT GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

def generate_analysis_text(stock_info, ind, direction, conf, t1, t2, stop, rr, df):
    """Produce a rich, structured analysis string from computed data."""
    curr  = "₦" if stock_info["currency"] == "NGN" else "$"
    price = ind["price"]
    adx   = ind["adx"]
    trend_str  = "STRONG" if adx > 50 else "MODERATE" if adx > 25 else "WEAK"
    mkt_phase  = "TRENDING" if adx > 35 else "RANGING"

    # Trend narrative
    if direction == "BULLISH":
        trend_narrative = (
            f"Price is in a {'confirmed' if conf >= 70 else 'developing'} uptrend. "
            f"EMA9 ({curr}{ind['ema9']:,.2f}) is {'above' if ind['ema9']>ind['ema21'] else 'crossing'} "
            f"EMA21 ({curr}{ind['ema21']:,.2f}), "
            f"with EMA50 at {curr}{ind['ema50']:,.2f} acting as dynamic support."
        )
        setup = (
            f"LONG SETUP: Enter on pullback toward {curr}{ind['ema9']:,.2f}–{curr}{ind['ema21']:,.2f}. "
            f"TP1 {curr}{t1:,.2f} (structure high / +{abs(t1-price)/price*100:.1f}%), "
            f"TP2 {curr}{t2:,.2f} (+{abs(t2-price)/price*100:.1f}%). "
            f"Stop below {curr}{stop:,.2f}. R:R = {rr}:1."
        )
    elif direction == "BEARISH":
        trend_narrative = (
            f"Price is in a {'confirmed' if conf >= 70 else 'developing'} downtrend. "
            f"EMA9 ({curr}{ind['ema9']:,.2f}) is below EMA21 ({curr}{ind['ema21']:,.2f}), "
            f"and price is trading beneath EMA50 ({curr}{ind['ema50']:,.2f})."
        )
        setup = (
            f"SHORT SETUP: Enter on rejection near {curr}{ind['ema9']:,.2f}–{curr}{ind['ema21']:,.2f}. "
            f"TP1 {curr}{t1:,.2f} (structure low / -{abs(price-t1)/price*100:.1f}%), "
            f"TP2 {curr}{t2:,.2f} (-{abs(price-t2)/price*100:.1f}%). "
            f"Stop above {curr}{stop:,.2f}. R:R = {rr}:1."
        )
    else:
        trend_narrative = (
            f"Price is consolidating between EMA9 ({curr}{ind['ema9']:,.2f}) "
            f"and EMA50 ({curr}{ind['ema50']:,.2f}). No clear directional bias."
        )
        setup = (
            f"WAIT for breakout above {curr}{t1:,.2f} (bullish) "
            f"or breakdown below {curr}{stop:,.2f} (bearish) before entering."
        )

    # RSI narrative
    if ind["rsi"] > 70:
        rsi_txt = f"RSI(14) at {ind['rsi']} — overbought territory. Watch for mean reversion."
    elif ind["rsi"] < 30:
        rsi_txt = f"RSI(14) at {ind['rsi']} — oversold territory. Potential bounce zone."
    else:
        rsi_txt = f"RSI(14) at {ind['rsi']} — neutral momentum, room to run {'higher' if direction=='BULLISH' else 'lower'}."

    # Bollinger narrative
    if ind["bb_pct"] > 80:
        bb_txt = f"Price near upper Bollinger Band ({curr}{ind['bb_upper']:,.2f}) — extended, watch for reversal."
    elif ind["bb_pct"] < 20:
        bb_txt = f"Price near lower Bollinger Band ({curr}{ind['bb_lower']:,.2f}) — compressed, potential reversal zone."
    else:
        bb_txt = f"Price inside Bollinger Bands (BB%: {ind['bb_pct']:.0f}%) — within normal range."

    # Volume
    vol_txt = (
        f"Volume is {'above' if ind['vol_ratio'] > 1.2 else 'below' if ind['vol_ratio'] < 0.8 else 'at'} "
        f"average ({ind['vol_ratio']:.2f}x). "
        + ("High volume confirms the move." if ind['vol_ratio'] > 1.2 else
           "Low volume — treat signal with caution." if ind['vol_ratio'] < 0.8 else
           "Average volume, neutral conviction.")
    )

    # SMC note
    swing_h, swing_l = swing_levels(df) if df is not None else ([], [])
    smc_txt = ""
    if swing_h and swing_l:
        nearest_res = min(swing_h, key=lambda x: abs(x - price))
        nearest_sup = min(swing_l, key=lambda x: abs(x - price))
        smc_txt = (
            f"Key swing resistance: {curr}{nearest_res:,.2f}. "
            f"Key swing support: {curr}{nearest_sup:,.2f}. "
            f"These are primary liquidity pools."
        )

    analysis = f"""## TREND DIRECTION
{trend_narrative}
Market phase: {mkt_phase} | Trend strength: {trend_str} (ADX {adx:.0f}).

## KEY LEVELS
Support: {curr}{ind['bb_lower']:,.2f} (BB lower) | EMA50: {curr}{ind['ema50']:,.2f} | EMA200: {curr}{ind['ema200']:,.2f}
Resistance: {curr}{ind['bb_upper']:,.2f} (BB upper) | EMA9: {curr}{ind['ema9']:,.2f}
{smc_txt}

## TECHNICAL INDICATORS
{rsi_txt}
RSI(7): {ind['rsi_7']} | Stochastic K/D: {ind['stoch_k']:.0f}/{ind['stoch_d']:.0f}{'  — overbought' if ind['stoch_k']>80 else '  — oversold' if ind['stoch_k']<20 else ''}.
MACD: {ind['macd']} (line {ind['macd_line']:+.4f}, hist {ind['macd_hist']:+.4f}).
{bb_txt}
ADX: {adx:.0f} (+DI {ind['plus_di']:.0f} / -DI {ind['minus_di']:.0f}) — {trend_str} trend.

## CANDLESTICK PATTERNS
Last candle: {ind['candle']}. ATR(14): {curr}{ind['atr_raw']:,.2f} ({ind['atr']:.2f}% of price).

## VOLUME ANALYSIS
{vol_txt}

## SMC / ICT CONCEPTS
{smc_txt if smc_txt else 'Insufficient swing data for SMC mapping on this window.'}
Watch for order block reactions near EMA zones and Bollinger extremes.

## TRADE SETUP
{setup}

## SIGNAL
**{direction}** — Confidence: {conf}%
Bull score: {round(conf/100*60+20):.0f}/100 | Bear score: {round((100-conf)/100*60+20):.0f}/100

## RISK NOTE
Invalidation: {'close below ' + curr + f'{stop:,.2f}' if direction=='BULLISH' else 'close above ' + curr + f'{stop:,.2f}' if direction=='BEARISH' else 'break of range boundaries'}.
Do not risk more than 1–2% of capital per trade. This is generated analysis, not financial advice.
"""
    return analysis.strip()

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════════════

def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS charts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id    TEXT NOT NULL,
            stock_name  TEXT NOT NULL,
            sector      TEXT,
            currency    TEXT,
            date_end    TEXT NOT NULL,
            direction   TEXT NOT NULL,
            confidence  INTEGER,
            indicators  TEXT NOT NULL,
            analysis    TEXT NOT NULL,
            img_bytes   BLOB NOT NULL,
            img_vec     BLOB NOT NULL,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stock ON charts(stock_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dir   ON charts(direction)")
    conn.commit()

def img_to_vector(png_bytes, size=64):
    """Convert PNG bytes → flat normalised float32 vector for similarity search."""
    img = Image.open(io.BytesIO(png_bytes)).convert("L").resize((size, size), Image.LANCZOS)
    arr = np.array(img, dtype=np.float32) / 255.0
    return arr.flatten()

def already_stored(conn, stock_id, date_end):
    cur = conn.execute(
        "SELECT 1 FROM charts WHERE stock_id=? AND date_end=?", (stock_id, date_end))
    return cur.fetchone() is not None

# ══════════════════════════════════════════════════════════════════════════════
# MAIN BUILD LOOP
# ══════════════════════════════════════════════════════════════════════════════

def build(verbose=True):
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed. Run: pip install yfinance")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    total_new = 0
    total_skip = 0
    total_fail = 0

    for stock in ALL_STOCKS:
        sid   = stock["id"]
        sname = stock["name"]
        ytick = stock["yf"]

        # ── NGX stocks: generate synthetic OHLCV (Yahoo Finance has no NGX data) ──
        if ytick is None:
            if verbose:
                print(f"\n[{sid}] Generating synthetic OHLCV (NGX — no yfinance data)...")
            df = synthetic_ohlcv(sid, n_days=120)
        else:
            # ── US stocks: fetch real OHLCV from yfinance ──
            if verbose:
                print(f"\n[{sid}] Fetching {ytick} ...")
            try:
                df = yf.download(ytick, period="120d", interval="1d",
                                 auto_adjust=True, progress=False, threads=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.columns = [str(c).strip().title() for c in df.columns]
                if df.empty or "Close" not in df.columns:
                    if verbose: print(f"  [SKIP] No data returned")
                    total_fail += 1
                    continue
                df = df[["Open","High","Low","Close","Volume"]].dropna()
                if len(df) < 30:
                    if verbose: print(f"  [SKIP] Only {len(df)} rows")
                    total_fail += 1
                    continue
            except Exception as e:
                if verbose: print(f"  [FAIL] Download error: {e}")
                total_fail += 1
                continue

        # Generate one entry per available 30-candle window
        # Step every 5 days to get variety without too many near-duplicates
        windows_added = 0
        for end_idx in range(30, len(df)+1, 5):
            window = df.iloc[end_idx-30 : end_idx].copy()
            date_end = str(window.index[-1].date())

            if already_stored(conn, sid, date_end):
                total_skip += 1
                continue

            # Indicators on the full available history up to this point
            full_window = df.iloc[:end_idx].copy()
            try:
                ind = compute_indicators(full_window)
            except Exception as e:
                continue

            price  = ind["price"]
            if price <= 0:
                continue

            # Daily change
            closes = full_window["Close"].values
            ch = float((closes[-1] - closes[-2]) / (closes[-2] + 1e-9) * 100) if len(closes) >= 2 else 0.0

            direction, conf, bp = rule_based_signal(ind, ch)

            # TP/SL
            atr_raw = ind["atr_raw"]
            m = atr_raw / price if price > 0 else 0.01
            swing_h, swing_l = swing_levels(full_window)

            def nearest_above(min_atr=1.0):
                thr = price + atr_raw * min_atr
                cands = [x for x in swing_h if x >= thr]
                return cands[0] if cands else None

            def nearest_below(min_atr=0.8):
                thr = price - atr_raw * min_atr
                cands = [x for x in swing_l if x <= thr]
                return cands[0] if cands else None

            if direction == "BULLISH":
                t1   = round(nearest_above(1.0) or price*(1+m*1.5), 2)
                t2   = round(nearest_above(2.0) or price*(1+m*3.0), 2)
                if t2 <= t1: t2 = round(t1 + atr_raw*1.5, 2)
                stop = round((nearest_below(0.8) or price*(1-m*1.0))*0.9985, 2)
                if stop >= price: stop = round(price*(1-m*1.0), 2)
            elif direction == "BEARISH":
                t1   = round(nearest_below(1.0) or price*(1-m*1.5), 2)
                t2   = round(nearest_below(2.0) or price*(1-m*3.0), 2)
                if t2 >= t1: t2 = round(t1 - atr_raw*1.5, 2)
                stop = round((nearest_above(0.8) or price*(1+m*1.0))*1.0015, 2)
                if stop <= price: stop = round(price*(1+m*1.0), 2)
            else:
                t1   = round(price*(1+m*0.8), 2)
                t2   = round(price*(1+m*1.5), 2)
                stop = round(price*(1-m*1.2), 2)

            rr = round(abs(t1-price)/(abs(price-stop)+1e-6), 2)

            # Render chart
            png = render_chart(window, sid, ind)
            if png is None:
                continue

            # Image vector
            vec = img_to_vector(png)

            # Analysis text
            analysis = generate_analysis_text(
                stock, ind, direction, conf, t1, t2, stop, rr, full_window)

            # Store
            conn.execute("""
                INSERT INTO charts
                  (stock_id,stock_name,sector,currency,date_end,
                   direction,confidence,indicators,analysis,img_bytes,img_vec)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                sid, sname, stock["sector"], stock["currency"], date_end,
                direction, conf,
                json.dumps(ind), analysis,
                png, vec.tobytes()
            ))
            conn.commit()
            windows_added += 1
            total_new += 1

        if verbose:
            print(f"  → {windows_added} windows added")
        time.sleep(0.3)  # be polite to yfinance

    conn.close()
    print(f"\n✓ Done. New: {total_new}  Skipped: {total_skip}  Failed: {total_fail}")
    print(f"  DB: {DB_PATH}")

def status():
    if not os.path.exists(DB_PATH):
        print("DB not found. Run: python model/build_db.py")
        return
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM charts").fetchone()[0]
    by_dir = conn.execute(
        "SELECT direction, COUNT(*) FROM charts GROUP BY direction").fetchall()
    by_stock = conn.execute(
        "SELECT stock_id, COUNT(*) FROM charts GROUP BY stock_id ORDER BY COUNT(*) DESC LIMIT 10").fetchall()
    conn.close()
    print(f"\nDB: {DB_PATH}")
    print(f"Total records : {total}")
    print(f"By direction  : {dict(by_dir)}")
    print(f"Top 10 stocks : {dict(by_stock)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.status:
        status()
    else:
        build()
