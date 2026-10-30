"""
export_stocks_csv.py — drop in stock-nexus-fixed/ and run:
    python3 export_stocks_csv.py
"""
import sys, os, csv, uuid, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "model"))

from app import _NGX_FULL
from ngx_scraper import fetch_ngx_prices

def simple_signal(change, price):
    if change > 1:
        return f"BUY @ {price}"
    elif change < -1:
        return f"SELL @ {price}"
    elif change == 0:
        return "NO DATA"
    else:
        return f"HOLD @ {price}"

print("Fetching live NGX prices...")
prices = fetch_ngx_prices(force=True)
print(f"Got {len(prices)} live prices.")

trade_date = datetime.date.today().isoformat()
scraped_at = datetime.datetime.now().isoformat(timespec="microseconds")

rows = []
for (ticker, name, sector, seed_price, seed_vol) in _NGX_FULL:
    live   = prices.get(ticker, {})
    price  = live.get("price")  or seed_price
    change = live.get("change") or 0.0
    volume = live.get("volume") or seed_vol

    rows.append({
        "id":         str(uuid.uuid4()),
        "ticker":     ticker,
        "company":    name,
        "price":      f"₦{price:,.2f}",
        "change":     f"{change:+.2f}%",
        "signal":     simple_signal(change, price),
        "scraped_at": scraped_at,
        "trade_date": trade_date,
        "volume":     volume,
    })

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stocks_export.csv")
fields = ["id", "ticker", "company", "price", "change", "signal", "scraped_at", "trade_date", "volume"]

with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print(f"\nExported {len(rows)} rows -> {out}")
