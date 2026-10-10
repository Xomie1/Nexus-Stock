"""
train_model.py — Stock Nexus ML Prediction Engine
==================================================
Trains an XGBoost + LSTM ensemble on historical OHLCV data for both
NGX and US stocks. Saves trained models to model/trained/.

Outputs:
  model/trained/xgb_direction.pkl      — XGBoost: next-day direction (UP/DOWN)
  model/trained/xgb_change.pkl         — XGBoost: next-day % price change
  model/trained/lstm_model.keras       — LSTM: sequence model
  model/trained/lstm_scaler.pkl        — Feature scaler for LSTM
  model/trained/feature_names.json     — Feature column order
  model/trained/model_meta.json        — Training stats & accuracy

Run from stock-nexus-fixed/:
    pip install xgboost tensorflow scikit-learn joblib
    python3 model/train_model.py
"""

import os, sys, json, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import joblib

try:
    import yfinance as yf
    _yf_ok = True
except ImportError:
    print("ERROR: yfinance not installed. Run: pip install yfinance")
    sys.exit(1)

try:
    import xgboost as xgb
    _xgb_ok = True
except ImportError:
    print("WARNING: xgboost not installed. Run: pip install xgboost")
    _xgb_ok = False

try:
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    from tensorflow import keras
    from tensorflow.keras import layers
    import tensorflow as tf
    tf.get_logger().setLevel("ERROR")
    _tf_ok = True
except ImportError:
    print("WARNING: tensorflow not installed. Run: pip install tensorflow")
    _tf_ok = False

from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error

# ── Config ────────────────────────────────────────────────────────────────────
OUT_DIR    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trained")
PERIOD     = "5y"         # 5 years — ~1,250 rows per ticker (was 2y/249 rows, too little data)
INTERVAL   = "1d"
SEQ_LEN    = 30           # LSTM lookback window (days)
LSTM_UNITS = 128           # increased from 64 — more capacity for larger dataset
EPOCHS     = 60            # more epochs with early stopping (patience=8)
BATCH_SIZE = 32

os.makedirs(OUT_DIR, exist_ok=True)

# ── Tickers ───────────────────────────────────────────────────────────────────
US_TICKERS = [
    # Mega-cap tech
    "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","ORCL","AMD","INTC",
    "CRM","ADBE","NFLX","PYPL","UBER","SHOP","SNOW","PLTR",
    # Finance
    "JPM","BAC","GS","MS","WFC","C","BRK-B","V","MA","AXP","COIN","SCHW",
    # Healthcare
    "JNJ","UNH","PFE","ABBV","MRK","LLY","TMO","ABT",
    # Energy
    "XOM","CVX","COP","SLB","OXY",
    # Consumer
    "WMT","AMZN","COST","TGT","NKE","MCD","SBUX","DIS",
    # ETFs (good for learning market-wide patterns)
    "SPY","QQQ","IWM","GLD","TLT","VIX",
    # Industrials / other
    "BA","CAT","GE","HON","RTX","LMT",
]

# NGX stocks on Yahoo Finance — correct suffix is .LG (Lagos), not .NG
# Note: Yahoo Finance NGX coverage is patchy; failures are skipped gracefully
NGX_YF_TICKERS = [
    "DANGCEM.LG","GTCO.LG","ZENITHBANK.LG","MTNN.LG","ACCESSCORP.LG",
    "FIRSTHOLDCO.LG","UBA.LG","STANBIC.LG","BUACEMENT.LG","BUAFOODS.LG",
    "NESTLE.LG","SEPLAT.LG","TRANSCORP.LG","GEREGU.LG","OKOMUOIL.LG",
    "FLOURMILL.LG","NB.LG","GUINNESS.LG","DANGSUGAR.LG","OANDO.LG",
    "FCMB.LG","FIDELITYBK.LG","WEMABANK.LG","ETI.LG","PRESCO.LG",
    "AIRTELAFRI.LG","ARADEL.LG","TRANSPOWER.LG","TOTAL.LG","CONOIL.LG",
    "WAPCO.LG","JBERGER.LG","NASCON.LG","VITAFOAM.LG","CUSTODIAN.LG",
    "UCAP.LG","PZ.LG","UNILEVER.LG","NEM.LG","AIICO.LG",
]

# ── Feature engineering ───────────────────────────────────────────────────────
def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all technical features from OHLCV dataframe."""
    df = df.copy()
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]

    # Returns
    df["ret_1"]  = c.pct_change(1)
    df["ret_3"]  = c.pct_change(3)
    df["ret_5"]  = c.pct_change(5)
    df["ret_10"] = c.pct_change(10)

    # RSI
    def rsi(s, n=14):
        d = s.diff()
        g = d.clip(lower=0).rolling(n).mean()
        ls = (-d.clip(upper=0)).rolling(n).mean()
        return 100 - 100 / (1 + g / (ls + 1e-9))
    df["rsi14"] = rsi(c, 14)
    df["rsi7"]  = rsi(c, 7)

    # MACD
    ema12 = c.ewm(span=12).mean()
    ema26 = c.ewm(span=26).mean()
    ml    = ema12 - ema26
    sl    = ml.ewm(span=9).mean()
    df["macd_line"] = ml
    df["macd_hist"] = ml - sl
    df["macd_cross"] = (ml > sl).astype(int)

    # Bollinger
    sma20   = c.rolling(20).mean()
    std20   = c.rolling(20).std()
    bb_up   = sma20 + 2 * std20
    bb_lo   = sma20 - 2 * std20
    df["bb_pct"] = (c - bb_lo) / (bb_up - bb_lo + 1e-9)
    df["bb_width"] = (bb_up - bb_lo) / (sma20 + 1e-9)

    # ATR
    tr1  = h - l
    tr2  = (h - c.shift()).abs()
    tr3  = (l - c.shift()).abs()
    tr   = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr  = tr.rolling(14).mean()
    df["atr_pct"] = atr / (c + 1e-9)

    # EMAs
    for n in [9, 21, 50, 200]:
        df[f"ema{n}_dist"] = (c - c.ewm(span=n).mean()) / (c + 1e-9)

    # Stochastic
    lo14   = l.rolling(14).min()
    hi14   = h.rolling(14).max()
    k      = 100 * (c - lo14) / (hi14 - lo14 + 1e-9)
    df["stoch_k"] = k
    df["stoch_d"] = k.rolling(3).mean()

    # ADX
    up_move   = h.diff()
    down_move = -l.diff()
    pdm = up_move.clip(lower=0).where(up_move > down_move, 0)
    ndm = down_move.clip(lower=0).where(down_move > up_move, 0)
    atr14 = atr
    pdi   = 100 * pdm.rolling(14).mean() / (atr14 + 1e-9)
    ndi   = 100 * ndm.rolling(14).mean() / (atr14 + 1e-9)
    dx    = 100 * (pdi - ndi).abs() / (pdi + ndi + 1e-9)
    df["adx"]     = dx.rolling(14).mean()
    df["plus_di"] = pdi
    df["minus_di"]= ndi

    # Volume
    vol_ma20 = v.rolling(20).mean()
    df["vol_ratio"] = v / (vol_ma20 + 1e-9)
    df["vol_change"]= v.pct_change(1)

    # Price position
    df["high52_dist"] = (h.rolling(252).max() - c) / (c + 1e-9)
    df["low52_dist"]  = (c - l.rolling(252).min()) / (c + 1e-9)

    # Day of week
    df["dow"] = pd.to_datetime(df.index).dayofweek

    # Multi-period momentum (strongest predictor class in literature)
    df["mom_20"]  = c.pct_change(20)
    df["mom_60"]  = c.pct_change(60)
    df["mom_120"] = c.pct_change(120)

    # Mean-reversion: distance from rolling mean
    df["dist_sma20"]  = (c - sma20) / (sma20 + 1e-9)
    df["dist_sma50"]  = (c - c.rolling(50).mean()) / (c.rolling(50).mean() + 1e-9)
    df["dist_sma200"] = (c - c.rolling(200).mean()) / (c.rolling(200).mean() + 1e-9)

    # Volatility regime
    df["vol_10"]  = df["ret_1"].rolling(10).std()
    df["vol_30"]  = df["ret_1"].rolling(30).std()
    df["vol_ratio_regime"] = df["vol_10"] / (df["vol_30"] + 1e-9)  # rising vs falling vol

    # Volume momentum
    df["vol_mom_5"]  = v.pct_change(5)
    df["vol_mom_20"] = v.pct_change(20)

    # Gap (overnight move)
    df["gap"] = (c - c.shift(1)) / (c.shift(1) + 1e-9) - df["ret_1"]

    # Price acceleration
    df["accel"] = df["ret_1"] - df["ret_1"].shift(1)

    return df

FEATURE_COLS = [
    # Returns
    "ret_1","ret_3","ret_5","ret_10",
    # Momentum (multi-period — strongest signal class)
    "mom_20","mom_60","mom_120",
    # Mean reversion
    "dist_sma20","dist_sma50","dist_sma200",
    # Oscillators
    "rsi14","rsi7",
    "macd_line","macd_hist","macd_cross",
    "bb_pct","bb_width",
    "stoch_k","stoch_d",
    # Trend
    "adx","plus_di","minus_di",
    "ema9_dist","ema21_dist","ema50_dist","ema200_dist",
    # Volatility
    "atr_pct","vol_10","vol_30","vol_ratio_regime",
    # Volume
    "vol_ratio","vol_change","vol_mom_5","vol_mom_20",
    # Price structure
    "high52_dist","low52_dist","gap","accel",
    # Calendar
    "dow",
]

# ── Data collection ───────────────────────────────────────────────────────────
def fetch_ticker(ticker, period=PERIOD, interval=INTERVAL):
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        if df is None or len(df) < 60:
            return None
        df = df[["Open","High","Low","Close","Volume"]].dropna()
        return df
    except Exception as e:
        print(f"  [skip] {ticker}: {e}")
        return None

def build_dataset(tickers, label=""):
    X_list, y_dir_list, y_chg_list = [], [], []
    sequences = []
    seq_labels_dir, seq_labels_chg = [], []
    ok, skip = 0, 0

    for ticker in tickers:
        print(f"  {label}{ticker}...", end=" ", flush=True)
        df = fetch_ticker(ticker)
        if df is None:
            print("skip")
            skip += 1
            continue

        df = make_features(df)

        # Target: next-day return
        df["target_chg"] = df["Close"].pct_change(1).shift(-1)
        df["target_dir"] = (df["target_chg"] > 0).astype(int)

        df = df.dropna(subset=FEATURE_COLS + ["target_chg", "target_dir"])
        if len(df) < SEQ_LEN + 10:
            print("too short")
            skip += 1
            continue

        X = df[FEATURE_COLS].values.astype(np.float32)
        y_dir = df["target_dir"].values.astype(int)
        y_chg = df["target_chg"].values.astype(np.float32)

        X_list.append(X)
        y_dir_list.append(y_dir)
        y_chg_list.append(y_chg)

        # Build LSTM sequences
        for i in range(SEQ_LEN, len(X)):
            sequences.append(X[i-SEQ_LEN:i])
            seq_labels_dir.append(y_dir[i])
            seq_labels_chg.append(y_chg[i])

        print(f"{len(df)} rows")
        ok += 1

    print(f"  → {ok} tickers loaded, {skip} skipped")

    X_flat     = np.vstack(X_list) if X_list else np.empty((0, len(FEATURE_COLS)))
    y_dir_flat = np.concatenate(y_dir_list) if y_dir_list else np.array([])
    y_chg_flat = np.concatenate(y_chg_list) if y_chg_list else np.array([])
    X_seq      = np.array(sequences, dtype=np.float32) if sequences else np.empty((0, SEQ_LEN, len(FEATURE_COLS)))
    y_seq_dir  = np.array(seq_labels_dir, dtype=int)
    y_seq_chg  = np.array(seq_labels_chg, dtype=np.float32)

    return X_flat, y_dir_flat, y_chg_flat, X_seq, y_seq_dir, y_seq_chg


# ── Training ──────────────────────────────────────────────────────────────────
def train_xgboost(X, y_dir, y_chg, scaler):
    print("\n[XGBoost] Training direction classifier...")
    X_s = scaler.transform(X)
    Xtr, Xval, ytr, yval = train_test_split(X_s, y_dir, test_size=0.15, shuffle=False)

    clf = xgb.XGBClassifier(
        n_estimators=600,
        max_depth=4,           # shallower = less overfit on financial data
        learning_rate=0.02,    # slower learning = better generalization
        subsample=0.7,
        colsample_bytree=0.7,
        min_child_weight=5,    # require more samples per leaf
        gamma=0.1,             # min loss reduction to split
        reg_alpha=0.1,         # L1
        reg_lambda=1.5,        # L2
        use_label_encoder=False,
        eval_metric="logloss",
        verbosity=0,
        n_jobs=-1,
    )
    clf.fit(Xtr, ytr, eval_set=[(Xval, yval)], verbose=False)
    acc = accuracy_score(yval, clf.predict(Xval))
    print(f"  Direction accuracy: {acc:.3f}")

    print("[XGBoost] Training % change regressor...")
    Xtr2, Xval2, ytr2, yval2 = train_test_split(X_s, y_chg, test_size=0.15, shuffle=False)
    reg = xgb.XGBRegressor(
        n_estimators=600,
        max_depth=4,
        learning_rate=0.02,
        subsample=0.7,
        colsample_bytree=0.7,
        min_child_weight=5,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.5,
        verbosity=0,
        n_jobs=-1,
    )
    reg.fit(Xtr2, ytr2, eval_set=[(Xval2, yval2)], verbose=False)
    mae = mean_absolute_error(yval2, reg.predict(Xval2))
    print(f"  Change MAE: {mae:.4f} ({mae*100:.2f}%)")

    return clf, reg, float(acc), float(mae)


def train_lstm(X_seq, y_dir, y_chg, scaler):
    print(f"\n[LSTM] Training on {len(X_seq)} sequences (shape={X_seq.shape})...")

    # Scale each feature across the sequence
    n, t, f = X_seq.shape
    X_flat = X_seq.reshape(-1, f)
    X_scaled = scaler.transform(X_flat).reshape(n, t, f)

    split = int(len(X_scaled) * 0.85)
    Xtr, Xval = X_scaled[:split], X_scaled[split:]
    ytr_d, yval_d = y_dir[:split], y_dir[split:]
    ytr_c, yval_c = y_chg[:split], y_chg[split:]

    # Shared LSTM backbone
    inp = keras.Input(shape=(t, f))
    x   = layers.LSTM(LSTM_UNITS, return_sequences=True,
              kernel_regularizer=keras.regularizers.l2(1e-4))(inp)
    x   = layers.Dropout(0.2)(x)
    x   = layers.LSTM(64, kernel_regularizer=keras.regularizers.l2(1e-4))(x)
    x   = layers.Dropout(0.2)(x)
    shared = keras.Model(inp, x)

    # Direction head
    d_out = layers.Dense(1, activation="sigmoid", name="direction")(shared.output)
    # Change head
    c_out = layers.Dense(1, activation="linear", name="change")(shared.output)

    model = keras.Model(shared.input, [d_out, c_out])
    model.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss={"direction": "binary_crossentropy", "change": "mse"},
        loss_weights={"direction": 1.0, "change": 0.5},
        metrics={"direction": "accuracy"},
    )

    cb = [
        keras.callbacks.EarlyStopping(patience=8, restore_best_weights=True, monitor="val_direction_accuracy"),
        keras.callbacks.ReduceLROnPlateau(patience=3, factor=0.5, verbose=0),
    ]

    hist = model.fit(
        Xtr, {"direction": ytr_d.astype(np.float32), "change": ytr_c},
        validation_data=(Xval, {"direction": yval_d.astype(np.float32), "change": yval_c}),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=cb,
        verbose=1,
    )

    val_acc = max(hist.history.get("val_direction_accuracy", [0]))
    print(f"  Best val direction accuracy: {val_acc:.3f}")
    return model, float(val_acc)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  STOCK NEXUS — ML Model Training")
    print("=" * 60)

    # Collect data
    print("\n[DATA] Fetching US stocks...")
    Xf_us, yd_us, yc_us, Xs_us, ysd_us, ysc_us = build_dataset(US_TICKERS, "US/")

    print("\n[DATA] Fetching NGX stocks (Yahoo Finance .NG)...")
    Xf_ng, yd_ng, yc_ng, Xs_ng, ysd_ng, ysc_ng = build_dataset(NGX_YF_TICKERS, "NGX/")

    # Combine
    X_flat = np.vstack([Xf_us, Xf_ng]) if len(Xf_ng) > 0 else Xf_us
    y_dir  = np.concatenate([yd_us, yd_ng]) if len(yd_ng) > 0 else yd_us
    y_chg  = np.concatenate([yc_us, yc_ng]) if len(yc_ng) > 0 else yc_us
    X_seq  = np.vstack([Xs_us, Xs_ng]) if len(Xs_ng) > 0 else Xs_us
    y_sdirr= np.concatenate([ysd_us, ysd_ng]) if len(ysd_ng) > 0 else ysd_us
    y_schg = np.concatenate([ysc_us, ysc_ng]) if len(ysc_ng) > 0 else ysc_us

    print(f"\n[DATA] Total: {len(X_flat)} flat rows, {len(X_seq)} sequences")

    if len(X_flat) < 200:
        print("ERROR: Not enough data to train. Check your internet connection.")
        sys.exit(1)

    # Fit scaler
    scaler = RobustScaler()
    scaler.fit(X_flat)

    meta = {
        "feature_cols": FEATURE_COLS,
        "seq_len": SEQ_LEN,
        "n_samples": int(len(X_flat)),
        "n_sequences": int(len(X_seq)),
        "tickers_us": US_TICKERS,
        "tickers_ngx": NGX_YF_TICKERS,
    }

    # XGBoost
    xgb_acc, xgb_mae = 0.0, 0.0
    if _xgb_ok and len(X_flat) > 0:
        clf, reg, xgb_acc, xgb_mae = train_xgboost(X_flat, y_dir, y_chg, scaler)
        joblib.dump(clf, os.path.join(OUT_DIR, "xgb_direction.pkl"))
        joblib.dump(reg, os.path.join(OUT_DIR, "xgb_change.pkl"))
        print(f"[XGBoost] Saved to {OUT_DIR}/xgb_direction.pkl & xgb_change.pkl")
        meta["xgb_direction_acc"] = xgb_acc
        meta["xgb_change_mae"]    = xgb_mae

    # LSTM
    lstm_acc = 0.0
    if _tf_ok and len(X_seq) >= SEQ_LEN * 4:
        lstm_model, lstm_acc = train_lstm(X_seq, y_sdirr, y_schg, scaler)
        lstm_model.save(os.path.join(OUT_DIR, "lstm_model.keras"))
        print(f"[LSTM] Saved to {OUT_DIR}/lstm_model.keras")
        meta["lstm_direction_acc"] = lstm_acc
    else:
        print("[LSTM] Skipped (tensorflow not available or insufficient sequences)")

    # Save shared scaler and feature list
    joblib.dump(scaler, os.path.join(OUT_DIR, "lstm_scaler.pkl"))
    with open(os.path.join(OUT_DIR, "feature_names.json"), "w") as f:
        json.dump(FEATURE_COLS, f)
    with open(os.path.join(OUT_DIR, "model_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print("\n" + "=" * 60)
    print("  Training complete!")
    if xgb_acc:  print(f"  XGBoost direction accuracy : {xgb_acc:.1%}")
    if xgb_mae:  print(f"  XGBoost change MAE         : {xgb_mae*100:.3f}%")
    if lstm_acc: print(f"  LSTM direction accuracy    : {lstm_acc:.1%}")
    print(f"  Models saved to: {OUT_DIR}/")
    print("=" * 60)


if __name__ == "__main__":
    main()