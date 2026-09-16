"""
STOCK NEXUS — Chart Retrieval Engine
======================================
Given an uploaded chart image (and optionally indicator data),
find the most similar historical chart in the DB and return its analysis.

Key idea:
  1. Convert query image → flat greyscale vector (same as storage)
  2. Optionally compute indicator similarity as a secondary score
  3. Rank by combined cosine similarity → return top match's analysis
"""

import io, json, os, sqlite3
from typing import Optional, List, Dict
import numpy as np
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "trained", "chart_retrieval.db")

# ── vector helpers ─────────────────────────────────────────────────────────────

def _img_bytes_to_vec(png_bytes: bytes, size: int = 64) -> np.ndarray:
    """PNG bytes → flat normalised float32 greyscale vector."""
    img = Image.open(io.BytesIO(png_bytes)).convert("L").resize((size, size), Image.LANCZOS)
    arr = np.array(img, dtype=np.float32) / 255.0
    return arr.flatten()

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a); nb = np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))

# ── indicator similarity ───────────────────────────────────────────────────────

_IND_KEYS = ["rsi","rsi_7","bb_pct","stoch_k","adx","vol_ratio","atr"]
_IND_NORM = [100,  100,     100,     100,      100,  3.0,        5.0]   # rough max per key

def _ind_vec(ind_dict: dict) -> np.ndarray:
    return np.array(
        [ind_dict.get(k, 0) / n for k, n in zip(_IND_KEYS, _IND_NORM)],
        dtype=np.float32,
    )

# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def db_ready() -> bool:
    """Return True if the DB exists and has at least one record."""
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        n = conn.execute("SELECT COUNT(*) FROM charts").fetchone()[0]
        conn.close()
        return n > 0
    except Exception:
        return False

def db_stats() -> dict:
    if not os.path.exists(DB_PATH):
        return {"total": 0}
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM charts").fetchone()[0]
    by_dir = dict(conn.execute(
        "SELECT direction, COUNT(*) FROM charts GROUP BY direction").fetchall())
    conn.close()
    return {"total": total, "by_direction": by_dir}

def retrieve(
    query_png: bytes,
    query_indicators: Optional[Dict] = None,
    direction_filter: Optional[str] = None,
    top_k: int = 1,
    img_weight: float = 0.7,
) -> List[Dict]:
    """
    Find the most similar chart(s) to the query image.

    Parameters
    ----------
    query_png        : raw PNG bytes of the uploaded chart
    query_indicators : optional dict of computed indicators for the query
    direction_filter : optional "BULLISH" | "BEARISH" | "NEUTRAL" to restrict pool
    top_k            : how many matches to return
    img_weight       : 0–1 weight for image similarity (1-img_weight for indicators)

    Returns
    -------
    List of dicts with keys:
        stock_id, stock_name, sector, currency, date_end,
        direction, confidence, indicators (dict), analysis (str),
        img_sim, ind_sim, combined_sim
    """
    if not db_ready():
        return []

    try:
        q_vec = _img_bytes_to_vec(query_png)
    except Exception as e:
        return [{"error": f"Could not process image: {e}"}]

    q_ind_vec = _ind_vec(query_indicators) if query_indicators else None

    conn = sqlite3.connect(DB_PATH)
    sql = "SELECT stock_id,stock_name,sector,currency,date_end,direction,confidence,indicators,analysis,img_vec FROM charts"
    if direction_filter:
        sql += f" WHERE direction='{direction_filter}'"
    rows = conn.execute(sql).fetchall()
    conn.close()

    if not rows:
        return []

    scored = []
    vec_size = 64 * 64

    for row in rows:
        sid, sname, sector, currency, date_end, direction, conf, ind_json, analysis, vec_blob = row
        try:
            db_vec = np.frombuffer(vec_blob, dtype=np.float32)
            if db_vec.shape[0] != vec_size:
                continue
            img_sim = _cosine(q_vec, db_vec)

            ind_sim = 0.5  # neutral default
            if q_ind_vec is not None:
                try:
                    db_ind = _ind_vec(json.loads(ind_json))
                    ind_sim = _cosine(q_ind_vec, db_ind)
                except Exception:
                    pass

            combined = img_weight * img_sim + (1 - img_weight) * ind_sim
            scored.append({
                "stock_id":   sid,
                "stock_name": sname,
                "sector":     sector,
                "currency":   currency,
                "date_end":   date_end,
                "direction":  direction,
                "confidence": conf,
                "indicators": json.loads(ind_json),
                "analysis":   analysis,
                "img_sim":    round(img_sim, 4),
                "ind_sim":    round(ind_sim, 4),
                "combined_sim": round(combined, 4),
            })
        except Exception:
            continue

    if not scored:
        return []

    scored.sort(key=lambda x: x["combined_sim"], reverse=True)
    return scored[:top_k]

def retrieve_top(
    query_png: bytes,
    query_indicators: Optional[Dict] = None,
) -> Optional[Dict]:
    """Convenience wrapper — returns the single best match or None."""
    results = retrieve(query_png, query_indicators, top_k=1)
    return results[0] if results else None
