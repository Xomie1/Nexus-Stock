"""
predictor.py — Stock Nexus ML Inference Engine (XGBoost only)
=============================================================
LSTM removed: TensorFlow cannot reliably run within Render's 512MB RAM budget.
XGBoost alone outperforms LSTM on tabular daily OHLCV data and trains in <30s.
"""

import os, json, warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib

# ── Paths ─────────────────────────────────────────────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.isdir(os.path.join(_DIR, "trained")):
    _DIR = os.path.join(_DIR, "model")
_TRAIN = os.path.join(_DIR, "trained")

_XGB_CLF = os.path.join(_TRAIN, "xgb_direction.pkl")
_XGB_REG = os.path.join(_TRAIN, "xgb_change.pkl")
_SCALER  = os.path.join(_TRAIN, "lstm_scaler.pkl")   # keep filename for back-compat
_FEATS   = os.path.join(_TRAIN, "feature_names.json")
_META    = os.path.join(_TRAIN, "model_meta.json")

# ── Lazy-loaded globals ───────────────────────────────────────────────────────
_xgb_clf  = None
_xgb_reg  = None
_scaler   = None
_feat_cols = None
_loaded   = False


def _load():
    global _xgb_clf, _xgb_reg, _scaler, _feat_cols, _loaded
    if _loaded:
        return

    if os.path.exists(_FEATS):
        with open(_FEATS) as f:
            _feat_cols = json.load(f)

    if os.path.exists(_SCALER):
        try:
            _scaler = joblib.load(_SCALER)
        except Exception as e:
            print(f"[PREDICTOR] Scaler load failed: {e}")

    if os.path.exists(_XGB_CLF):
        try:
            _xgb_clf = joblib.load(_XGB_CLF)
            print(f"[PREDICTOR] XGBoost classifier loaded")
        except Exception as e:
            print(f"[PREDICTOR] XGBoost classifier load failed: {e}")
    else:
        print(f"[PREDICTOR] XGBoost classifier not found — run model/train_model.py")

    if os.path.exists(_XGB_REG):
        try:
            _xgb_reg = joblib.load(_XGB_REG)
            print(f"[PREDICTOR] XGBoost regressor loaded")
        except Exception as e:
            print(f"[PREDICTOR] XGBoost regressor load failed: {e}")

    _loaded = True
    if _xgb_clf:
        print("[PREDICTOR] ✅ XGBoost ready")
    else:
        print("[PREDICTOR] ⚠️  No trained models — ML predictions unavailable")


def models_ready() -> bool:
    _load()
    return bool(_xgb_clf)


# ── Feature engineering ───────────────────────────────────────────────────────
def _make_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]

    df["ret_1"]  = c.pct_change(1)
    df["ret_3"]  = c.pct_change(3)
    df["ret_5"]  = c.pct_change(5)
    df["ret_10"] = c.pct_change(10)

    def rsi(s, n=14):
        d = s.diff()
        g = d.clip(lower=0).rolling(n).mean()
        ls = (-d.clip(upper=0)).rolling(n).mean()
        return 100 - 100 / (1 + g / (ls + 1e-9))
    df["rsi14"] = rsi(c, 14)
    df["rsi7"]  = rsi(c, 7)

    ema12 = c.ewm(span=12).mean()
    ema26 = c.ewm(span=26).mean()
    ml    = ema12 - ema26
    sl    = ml.ewm(span=9).mean()
    df["macd_line"]  = ml
    df["macd_hist"]  = ml - sl
    df["macd_cross"] = (ml > sl).astype(int)

    sma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    bb_up = sma20 + 2 * std20
    bb_lo = sma20 - 2 * std20
    df["bb_pct"]   = (c - bb_lo) / (bb_up - bb_lo + 1e-9)
    df["bb_width"] = (bb_up - bb_lo) / (sma20 + 1e-9)

    tr  = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    df["atr_pct"] = atr / (c + 1e-9)

    for n in [9, 21, 50, 200]:
        df[f"ema{n}_dist"] = (c - c.ewm(span=n).mean()) / (c + 1e-9)

    lo14 = l.rolling(14).min()
    hi14 = h.rolling(14).max()
    k    = 100 * (c - lo14) / (hi14 - lo14 + 1e-9)
    df["stoch_k"] = k
    df["stoch_d"] = k.rolling(3).mean()

    up_move   = h.diff()
    down_move = -l.diff()
    pdm = up_move.clip(lower=0).where(up_move > down_move, 0)
    ndm = down_move.clip(lower=0).where(down_move > up_move, 0)
    pdi = 100 * pdm.rolling(14).mean() / (atr + 1e-9)
    ndi = 100 * ndm.rolling(14).mean() / (atr + 1e-9)
    dx  = 100 * (pdi - ndi).abs() / (pdi + ndi + 1e-9)
    df["adx"]      = dx.rolling(14).mean()
    df["plus_di"]  = pdi
    df["minus_di"] = ndi

    vol_ma20 = v.rolling(20).mean()
    df["vol_ratio"]  = v / (vol_ma20 + 1e-9)
    df["vol_change"] = v.pct_change(1)

    df["high52_dist"] = (h.rolling(252).max() - c) / (c + 1e-9)
    df["low52_dist"]  = (c - l.rolling(252).min()) / (c + 1e-9)
    df["dow"] = pd.to_datetime(df.index).dayofweek

    df["mom_20"]  = c.pct_change(20)
    df["mom_60"]  = c.pct_change(60)
    df["mom_120"] = c.pct_change(120)

    df["dist_sma20"]  = (c - sma20) / (sma20 + 1e-9)
    df["dist_sma50"]  = (c - c.rolling(50).mean()) / (c.rolling(50).mean() + 1e-9)
    df["dist_sma200"] = (c - c.rolling(200).mean()) / (c.rolling(200).mean() + 1e-9)

    ret1 = c.pct_change(1)
    df["vol_10"] = ret1.rolling(10).std()
    df["vol_30"] = ret1.rolling(30).std()
    df["vol_ratio_regime"] = df["vol_10"] / (df["vol_30"] + 1e-9)

    df["vol_mom_5"]  = v.pct_change(5)
    df["vol_mom_20"] = v.pct_change(20)

    df["gap"]   = (c - c.shift(1)) / (c.shift(1) + 1e-9) - ret1
    df["accel"] = ret1 - ret1.shift(1)

    return df


FEATURE_COLS = [
    "ret_1","ret_3","ret_5","ret_10",
    "mom_20","mom_60","mom_120",
    "dist_sma20","dist_sma50","dist_sma200",
    "rsi14","rsi7",
    "macd_line","macd_hist","macd_cross",
    "bb_pct","bb_width",
    "stoch_k","stoch_d",
    "adx","plus_di","minus_di",
    "ema9_dist","ema21_dist","ema50_dist","ema200_dist",
    "atr_pct","vol_10","vol_30","vol_ratio_regime",
    "vol_ratio","vol_change","vol_mom_5","vol_mom_20",
    "high52_dist","low52_dist","gap","accel",
    "dow",
]


# ── Core prediction ───────────────────────────────────────────────────────────
def predict(df: pd.DataFrame, current_price: float) -> dict:
    """XGBoost-only prediction. Returns direction, probability, signal, confidence, 5-day targets."""
    _load()

    if not models_ready() or df is None or len(df) < 30:
        return _unavailable(current_price)

    try:
        feat_df = _make_features(df)
        cols    = _feat_cols if _feat_cols else FEATURE_COLS
        feat_df[cols] = feat_df[cols].ffill().bfill().fillna(0)
        feat_df = feat_df.dropna(subset=cols)
        if len(feat_df) < 2:
            return _unavailable(current_price)

        x_latest = feat_df[cols].values[-1:].astype(np.float32)

        if not _xgb_clf or not _scaler:
            return _unavailable(current_price)

        xs          = _scaler.transform(x_latest)
        prob_up     = float(_xgb_clf.predict_proba(xs)[0][1])
        change_pct  = float(_xgb_reg.predict(xs)[0]) * 100 if _xgb_reg else 0.0

        if prob_up >= 0.68:   signal = "STRONG BUY"
        elif prob_up >= 0.56: signal = "BUY"
        elif prob_up <= 0.32: signal = "STRONG SELL"
        elif prob_up <= 0.44: signal = "SELL"
        else:                 signal = "HOLD"

        confidence = int(min(95, max(20, abs(prob_up - 0.5) * 200)))

        atr_vals  = feat_df["atr_pct"].dropna().values
        atr_pct   = float(atr_vals[-1]) if len(atr_vals) > 0 else 0.015
        mid_5d    = current_price * (1 + change_pct / 100 * 5)
        spread    = current_price * atr_pct * 2.5

        return {
            "ml_direction":   "UP" if prob_up >= 0.5 else "DOWN",
            "ml_prob_up":     round(prob_up, 4),
            "ml_change_pct":  round(change_pct, 3),
            "ml_signal":      signal,
            "ml_confidence":  confidence,
            "ml_target_low":  round(mid_5d - spread, 2),
            "ml_target_mid":  round(mid_5d, 2),
            "ml_target_high": round(mid_5d + spread, 2),
            "ml_source":      "xgboost",
        }

    except Exception as e:
        print(f"[PREDICTOR] predict() error: {e}")
        return _unavailable(current_price)


def _unavailable(price: float) -> dict:
    return {
        "ml_direction":   None,
        "ml_prob_up":     None,
        "ml_change_pct":  None,
        "ml_signal":      "UNAVAILABLE",
        "ml_confidence":  0,
        "ml_target_low":  None,
        "ml_target_mid":  None,
        "ml_target_high": None,
        "ml_source":      "unavailable",
    }


def predictor_status() -> dict:
    _load()
    meta = {}
    if os.path.exists(_META):
        with open(_META) as f:
            meta = json.load(f)
    return {
        "xgboost_ready":     bool(_xgb_clf),
        "lstm_ready":        False,   # LSTM removed
        "ensemble_ready":    False,   # XGBoost-only now
        "xgb_direction_acc": meta.get("xgb_direction_acc"),
        "n_samples":         meta.get("n_samples"),
        "last_retrain":      meta.get("last_retrain"),
        "real_ngx_days":     meta.get("real_ngx_days", 0),
        "real_ngx_tickers":  meta.get("real_ngx_tickers", 0),
        "retrain_trigger":   meta.get("retrain_trigger"),
    }


def reload_models() -> bool:
    """Hot-reload models from disk after retraining. Zero-downtime."""
    global _xgb_clf, _xgb_reg, _scaler, _feat_cols, _loaded
    print("[PREDICTOR] Reloading models from disk...")
    _xgb_clf   = None
    _xgb_reg   = None
    _scaler    = None
    _feat_cols = None
    _loaded    = False
    _load()
    ready = models_ready()
    print(f"[PREDICTOR] Reload {'✅ complete' if ready else '⚠️  no models found'}")
    return ready
