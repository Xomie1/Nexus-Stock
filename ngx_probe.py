"""
NGX Probe — tests the official doclib.ngxgroup.com REST API discovered
by inspecting the JavaScript on the NGX equities price-list page.

Run:
    python3 ngx_probe.py

Expected output if the API is accessible:
    [doclib] HTTP 200, rows=XXX
    Sample: {'Symbol': 'DANGCEM', 'ClosePrice': 812.0, ...}
"""

import requests, json, sys

sess = requests.Session()
sess.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
})

# Step 1: warm-up page hit (sets cookies, satisfies CORS preflight)
print("Warming up session with NGX page visit...")
try:
    warm = sess.get(
        "https://ngxgroup.com/exchange/data/equities-price-list/",
        timeout=15,
        headers={"Accept": "text/html"},
    )
    print(f"  Warm-up HTTP {warm.status_code}")
except Exception as e:
    print(f"  Warm-up failed: {e}")

# Step 2: hit the doclib API directly
BASE = "https://doclib.ngxgroup.com/REST/api/statistics/equities/"
for params in [
    {"market": "", "sector": "", "orderby": "", "pageSize": 300, "pageNo": 0},
    {"market": "NSM", "sector": "", "orderby": "", "pageSize": 300, "pageNo": 0},
    {},
]:
    print(f"\nTrying params={params} ...")
    try:
        r = sess.get(
            BASE,
            params=params,
            timeout=15,
            headers={
                "Referer": "https://ngxgroup.com/exchange/data/equities-price-list/",
                "Origin":  "https://ngxgroup.com",
                "Accept":  "application/json, text/plain, */*",
            },
        )
        print(f"  HTTP {r.status_code}  Content-Type: {r.headers.get('Content-Type', '?')}")
        print(f"  Response (first 500 chars): {r.text[:500]}")

        if r.status_code == 200:
            try:
                payload = r.json()
            except Exception:
                print("  Could not parse as JSON.")
                continue

            rows = (
                payload.get("d") or payload.get("data") or
                payload.get("Data") or
                (payload if isinstance(payload, list) else [])
            )
            if not rows:
                print(f"  JSON parsed but no rows. Keys: {list(payload.keys()) if isinstance(payload, dict) else 'list'}")
                continue

            print(f"  SUCCESS — {len(rows)} rows")
            print(f"  First row keys: {list(rows[0].keys())}")
            print(f"  Sample row:\n{json.dumps(rows[0], indent=2)}")

            by_sym = {}
            for row in rows:
                sym = (row.get("Symbol") or row.get("symbol") or row.get("Ticker") or "").strip().upper()
                price = float(row.get("ClosePrice") or row.get("Close") or row.get("Price") or 0)
                pct   = float(row.get("PercentChange") or row.get("PctChange") or 0)
                if sym and price > 0:
                    by_sym[sym] = (price, pct)

            for sym in ["DANGCEM", "GTCO", "ZENITHBANK", "MTNN", "AIRTELAFRI"]:
                if sym in by_sym:
                    p, c = by_sym[sym]
                    print(f"  {sym:15s}: N{p:>10,.2f}  ({c:+.2f}%)")
                else:
                    print(f"  {sym:15s}: not in response")
            break

    except Exception as e:
        print(f"  Error: {e}")

print("\nDone.")