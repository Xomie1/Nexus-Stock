"""
STOCK NEXUS — NGX Live Price Scraper (v6)
Sources (tried in order):
  1. afrinvestor.com  — HTML table, NGN prices
  2. ngxgroup.com     — official NGX HTML table, NGN prices
  3. proshareng.com   — HTML table, NGN prices (SSL verify=False)
  4. stockanalysis.com — JSON API, prices in NGN (they show NGN for NGX)
Cache: 55s TTL, always returns last good result on failure
"""

import time, threading, warnings
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

_SESSION_LOCK = threading.Lock()
_SESSION = None

def _make_session():
    s = requests.Session()
    retry = Retry(total=2, backoff_factor=0.5,
                  status_forcelist=[500, 502, 503, 504],
                  allowed_methods=["GET"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    return s

def _get_session():
    global _SESSION
    with _SESSION_LOCK:
        if _SESSION is None:
            _SESSION = _make_session()
    return _SESSION

# ── NGX Universe ──────────────────────────────────────────────────────────────
NGX_UNIVERSE = [
    ("AIRTELAFRI","Airtel Africa Plc","Telecom",2497.00,320_000),
    ("MTNN","MTN Nigeria Communications PLC","Telecom",760.00,2_100_000),
    ("BUAFOODS","BUA Foods PLC","Consumer",798.00,490_000),
    ("DANGCEM","Dangote Cement Plc","Materials",810.00,1_240_000),
    ("BUACEMENT","BUA Cement Plc","Materials",326.70,550_000),
    ("ARADEL","Aradel Holdings Plc","Energy",1260.00,150_000),
    ("SEPLAT","Seplat Energy Plc","Energy",9099.90,180_000),
    ("GTCO","Guaranty Trust Holding Co Plc","Finance",120.95,8_800_000),
    ("ZENITHBANK","Zenith Bank Plc","Finance",103.00,12_000_000),
    ("WAPCO","Lafarge Africa Plc","Materials",220.00,400_000),
    ("GEREGU","Geregu Power Plc","Energy",1141.50,80_000),
    ("NESTLE","Nestle Nigeria Plc","Consumer",3055.50,85_000),
    ("INTBREW","International Breweries Plc","Consumer",14.00,10_000_000),
    ("PRESCO","Presco Plc","Agriculture",1980.00,67_000),
    ("TRANSPOWER","Transcorp Power Plc","Energy",306.90,300_000),
    ("NB","Nigerian Breweries Plc","Consumer",72.00,2_500_000),
    ("FIRSTHOLDCO","First HoldCo Plc","Finance",50.00,16_000_000),
    ("STANBIC","Stanbic IBTC Holdings PLC","Finance",133.10,620_000),
    ("TRANSCOHOT","Transcorp Hotels Plc","Hospitality",203.00,200_000),
    ("UBA","United Bank for Africa Plc","Finance",46.15,18_000_000),
    ("OKOMUOIL","The Okomu Oil Palm Co Plc","Agriculture",1765.00,95_000),
    ("ACCESSCORP","Access Holdings Plc","Finance",26.00,25_000_000),
    ("ETI","Ecobank Transnational Inc","Finance",46.00,5_000_000),
    ("WEMABANK","Wema Bank PLC","Finance",26.10,8_000_000),
    ("FIDELITYBK","Fidelity Bank Plc","Finance",19.25,22_000_000),
    ("GUINNESS","Guinness Nigeria Plc","Consumer",423.20,180_000),
    ("DANGSUGAR","Dangote Sugar Refinery Plc","Consumer",65.00,3_000_000),
    ("OANDO","Oando PLC","Energy",49.60,4_000_000),
    ("UNILEVER","Unilever Nigeria Plc","Consumer",94.00,500_000),
    ("FCMB","FCMB Group Plc","Finance",12.10,12_000_000),
    ("TRANSCORP","Transnational Corporation Plc","Conglomerate",48.00,5_000_000),
    ("JBERGER","Julius Berger Nigeria Plc","Construction",288.00,120_000),
    ("JAIZBANK","Jaiz Bank Plc","Finance",9.30,6_000_000),
    ("CUSTODIAN","Custodian Investment Plc","Finance",73.50,400_000),
    ("NASCON","Nascon Allied Industries Plc","Consumer",152.00,250_000),
    ("STERLINGNG","Sterling Financial Holdings Plc","Finance",8.00,10_000_000),
    ("NAHCO","Nigerian Aviation Handling Co Plc","Transport",189.95,300_000),
    ("NGXGROUP","The Nigerian Exchange Group Plc","Finance",165.00,350_000),
    ("UCAP","United Capital Plc","Finance",18.10,2_000_000),
    ("PZ","PZ Cussons Nigeria Plc","Consumer",83.00,600_000),
    ("BETAGLAS","Beta Glass Plc","Materials",498.50,50_000),
    ("UACN","UAC of Nigeria PLC","Conglomerate",99.00,400_000),
    ("FIDSON","Fidson Healthcare Plc","Healthcare",100.00,350_000),
    ("TOTAL","TotalEnergies Marketing Nigeria Plc","Energy",640.00,120_000),
    ("SKYAVN","Skyway Aviation Handling Co Plc","Transport",143.10,200_000),
    ("ETRANZACT","eTranzact International Plc","Technology",20.15,1_500_000),
    ("VITAFOAM","Vitafoam Nigeria Plc","Consumer",118.00,300_000),
    ("HONYFLOUR","Honeywell Flour Mills Plc","Consumer",20.95,2_000_000),
    ("NEM","NEM Insurance Plc","Finance",31.90,800_000),
    ("CADBURY","Cadbury Nigeria Plc","Consumer",67.20,400_000),
    ("AIICO","AIICO Insurance Plc","Finance",4.10,3_000_000),
    ("CONOIL","Conoil Plc","Energy",204.40,380_000),
    ("MANSARD","AXA Mansard Insurance Plc","Finance",15.21,1_500_000),
    ("CHAMPION","Champion Breweries Plc","Consumer",15.05,1_200_000),
    ("CORNERST","Cornerstone Insurance Plc","Finance",5.60,2_000_000),
    ("ABBEYBDS","Abbey Mortgage Bank Plc","Finance",9.90,800_000),
    ("UPDC","UPDC Plc","Real Estate",4.65,1_500_000),
    ("VFDGROUP","VFD Group PLC","Finance",11.45,500_000),
    ("IKEJAHOTEL","Ikeja Hotel Plc","Hospitality",39.00,300_000),
    ("MBENEFIT","Mutual Benefits Assurance Plc","Finance",4.40,2_500_000),
    ("CAP","Chemical and Allied Products Plc","Materials",99.80,200_000),
    ("INFINITY","Infinity Trust Mortgage Bank Plc","Finance",19.00,600_000),
    ("WAPIC","Coronation Insurance Plc","Finance",3.00,2_000_000),
    ("MAYBAKER","May & Baker Nigeria Plc","Healthcare",34.30,500_000),
    ("AFRIPRUD","Africa Prudential Plc","Finance",14.00,1_000_000),
    ("CWG","CWG Plc","Technology",20.70,800_000),
    ("CONHALLPLC","Consolidated Hallmark Holdings Plc","Finance",4.70,1_500_000),
    ("JAPAULGOLD","Japaul Gold & Ventures Plc","Materials",3.42,2_000_000),
    ("ELLAHLAKES","Ellah Lakes Plc","Agriculture",11.95,400_000),
    ("ETERNA","Eterna Plc","Energy",34.90,800_000),
    ("NEIMETH","Neimeth International Pharma Plc","Healthcare",10.00,700_000),
    ("EUNISELL","Eunisell Interlinked Plc","Materials",169.95,80_000),
    ("CHAMS","Chams Holding Company Plc","Technology",3.96,2_000_000),
    ("NPFMCRFBK","NPF Microfinance Bank Plc","Finance",6.19,800_000),
    ("SOVRENINS","Sovereign Trust Insurance Plc","Finance",1.97,2_000_000),
    ("VERITASKAP","Veritas Kapital Assurance Plc","Finance",2.00,1_500_000),
    ("LINKASSURE","Linkage Assurance Plc","Finance",1.50,1_800_000),
    ("SUNUASSUR","Sunu Assurances Nigeria Plc","Finance",4.65,600_000),
    ("REDSTAREX","Red Star Express Plc","Transport",28.15,300_000),
    ("IMG","Industrial and Medical Gases Nigeria","Materials",36.00,200_000),
    ("LIVINGTRUST","Livingtrust Mortgage Bank PLC","Finance",4.80,600_000),
    ("FTNCOCOA","FTN Cocoa Processors Plc","Agriculture",5.33,800_000),
    ("LASACO","LASACO Assurance Plc","Finance",2.05,1_500_000),
    ("CUTIX","Cutix Plc","Materials",3.17,1_200_000),
    ("BERGER","Berger Paints Nigeria Plc","Materials",75.90,150_000),
    ("TANTALIZER","Tantalizers PLC","Consumer",4.25,800_000),
    ("NCR","NCR (Nigeria) Plc","Technology",199.00,60_000),
    ("CAVERTON","Caverton Offshore Support Group Plc","Transport",6.40,1_000_000),
    ("PRESTIGE","Prestige Assurance Plc","Finance",1.53,1_200_000),
    ("LIVESTOCK","Livestock Feeds Plc","Agriculture",6.70,800_000),
    ("UNIVINSURE","Universal Insurance Plc","Finance",1.22,1_500_000),
    ("CILEASING","C & I Leasing Plc","Finance",6.95,600_000),
    ("UPDCREIT","UPDC Real Estate Investment Trust","Real Estate",7.70,400_000),
    ("REGALINS","Regency Alliance Insurance Plc","Finance",1.14,1_500_000),
    ("UNITYBNK","Unity Bank Plc","Finance",1.51,3_000_000),
    ("RTBRISCOE","R.T Briscoe (Nigeria) Plc","Consumer",10.50,600_000),
    ("CHELLARAM","Chellarams Plc","Consumer",13.20,300_000),
    ("GUINEAINS","Guinea Insurance Plc","Finance",1.13,1_000_000),
    ("ABCTRANS","ABC Transport Plc","Transport",6.24,500_000),
    ("MORISON","Morison Industries Plc","Healthcare",11.80,250_000),
    ("NNFM","Northern Nigeria Flour Mills Plc","Consumer",79.40,200_000),
    ("FLOURMILL","Flour Mills of Nigeria Plc","Consumer",54.00,1_200_000),
    ("MECURE","Mecure Industries PLC","Materials",61.50,200_000),
]
_seen = set()
NGX_UNIVERSE = [r for r in NGX_UNIVERSE if not (r[0] in _seen or _seen.add(r[0]))]

SECTOR_COLORS = {
    "Finance":"#4A9EFF","Telecom":"#FFD700","Materials":"#FF6B4A",
    "Consumer":"#F472B6","Energy":"#34D399","Agriculture":"#86EFAC",
    "Technology":"#38BDF8","Healthcare":"#E63946","Construction":"#FB923C",
    "Transport":"#2DD4BF","Hospitality":"#C084FC","Real Estate":"#FCD34D",
    "Conglomerate":"#A3E635",
}

def build_stock_list():
    return [{"id":sid,"name":name,"sector":sector,"currency":"NGN","yf":None,
             "color":SECTOR_COLORS.get(sector,"#CBD5E1")}
            for sid,name,sector,*_ in NGX_UNIVERSE]

def build_seed_prices():
    return {sid:{"price":price,"change":0.0,
                 "high":round(price*1.015,2),"low":round(price*0.985,2),
                 "vol":vol,"mktcap":"N/A"}
            for sid,name,sector,price,vol in NGX_UNIVERSE}

# ── Price cache ───────────────────────────────────────────────────────────────
_price_cache = {}
_price_cache_ts = 0
_PRICE_TTL = 55

def _looks_like_ngn(results):
    ref = results.get("DANGCEM") or results.get("MTNN") or results.get("ZENITHBANK")
    return ref.get("price", 0) >= 10 if ref else True

def _parse_html_table(html, name):
    """Generic NGN price table parser — auto-detects columns."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    results = {}

    # Find best table — one whose headers mention symbol/price
    best = None
    for t in soup.find_all("table"):
        ths = " ".join(th.get_text(strip=True).upper() for th in t.find_all("th"))
        if any(k in ths for k in ("SYMBOL","TICKER","CLOSE","LAST","PRICE")):
            best = t
            break
    if not best:
        tables = soup.find_all("table")
        best = tables[0] if tables else None
    if not best:
        print(f"[NGX {name}] no table found in page")
        return {}

    ths = [th.get_text(strip=True).upper() for th in best.find_all("th")]
    sym_i   = next((i for i,h in enumerate(ths) if "SYMBOL" in h or "TICKER" in h), 0)
    close_i = next((i for i,h in enumerate(ths) if "CLOSE" in h or "LAST" in h or "PRICE" in h), 4)
    pchg_i  = next((i for i,h in enumerate(ths) if "%" in h or "PCT" in h), -1)

    for row in best.select("tbody tr"):
        cols = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cols) < 3:
            continue
        try:
            sid = cols[sym_i].strip().upper() if sym_i < len(cols) else ""
            if not sid or not sid.replace("-","").isalnum() or len(sid) > 15:
                continue
            raw_price = cols[close_i] if close_i < len(cols) else "0"
            price = float(raw_price.replace(",","").replace("₦","").strip())
            change = 0.0
            if pchg_i >= 0 and pchg_i < len(cols):
                raw = cols[pchg_i].replace("%","").replace("+","").strip()
                try:
                    v = float(raw)
                    if -100 < v < 100:
                        change = round(v, 4)
                except Exception:
                    pass
            if price > 0:
                results[sid] = {"price": round(price, 2), "change": change, "mktcap": "N/A"}
        except Exception:
            continue

    return results

# ── Source 1: doclib.ngxgroup.com (official NGX REST API — JS-rendered data) ──
def _fetch_doclib():
    """
    The NGX equities page (ngxgroup.com/exchange/data/equities-price-list/)
    loads its table via JavaScript using this REST endpoint on doclib.ngxgroup.com.
    Discovered via ngx_probe.py which found the URL embedded in page <script> tags.

    Response shape (typical):
        {
          "d": [
            {
              "Symbol": "DANGCEM",
              "CompanyName": "Dangote Cement Plc",
              "OpeningPrice": 810.00,
              "High": 815.00,
              "Low": 808.00,
              "ClosePrice": 812.00,
              "Change": 2.00,
              "PercentChange": 0.247,
              "Volume": 1240000,
              "MarketCap": "13.83T"
            },
            ...
          ]
        }
    Keys may vary slightly (PreviousClosingPrice etc.) — we probe both.
    """
    try:
        sess = _get_session()
        # Warm-up is optional — doclib sometimes works without it.
        # Use a short timeout so a dead ngxgroup.com doesn't block startup.
        try:
            sess.get("https://ngxgroup.com/exchange/data/equities-price-list/",
                     timeout=5, headers={"Accept": "text/html"})
        except Exception:
            pass  # warm-up failed — proceed anyway, doclib may still respond

        # Fetch all pages — API may paginate (50 or 100 per page)
        # Try large pageSize first, then paginate if needed
        all_rows = []
        base_url = "https://doclib.ngxgroup.com/REST/api/statistics/equities/"
        hdrs = {
            "Referer": "https://ngxgroup.com/exchange/data/equities-price-list/",
            "Origin":  "https://ngxgroup.com",
            "Accept":  "application/json, text/plain, */*",
        }

        for market in ["", "NSM", "ASeM"]:
            page_rows = []
            for page_no in range(0, 5):  # up to 5 pages
                params = {"market": market, "sector": "", "orderby": "",
                          "pageSize": 300, "pageNo": page_no}
                try:
                    r = sess.get(base_url, params=params, timeout=15, headers=hdrs)
                    if r.status_code != 200 or len(r.text) < 50:
                        break
                    payload = r.json()
                    rows = payload if isinstance(payload, list) else (
                        payload.get("d") or payload.get("data") or payload.get("Data") or []
                    )
                    if not rows:
                        break
                    page_rows.extend(rows)
                    print(f"[NGX doclib] market={market!r} page={page_no} -> {len(rows)} rows")
                    if len(rows) < 50:  # last page
                        break
                except Exception as e:
                    print(f"[NGX doclib] page {page_no} error: {e}")
                    break
            all_rows.extend(page_rows)
            if all_rows:
                break  # got data from first market, skip others

        # Deduplicate by symbol
        seen = set()
        rows = []
        for r2 in all_rows:
            sym = (r2.get("Symbol") or r2.get("symbol") or "").strip().upper()
            if sym and sym not in seen:
                seen.add(sym)
                rows.append(r2)

        # Process as single block
        for params in [{"_dummy": True}]:  # keep loop structure, single iteration
            try:
                if not rows:
                    print("[NGX doclib] no rows fetched")
                    continue

                results = {}
                for row in rows:
                    try:
                        # Symbol — the JSON field is "Symbol"; "Company" is the full name
                        sid = (
                            row.get("Symbol") or row.get("symbol") or
                            row.get("Ticker") or row.get("ticker") or ""
                        ).strip().upper()
                        if not sid or len(sid) > 15:
                            continue

                        # Exact field names confirmed from live API response:
                        # ClosePrice, PrevClosingPrice, PercChange, Volume, Sector, Company2, TradeDate
                        price = float(row.get("ClosePrice") or row.get("Close") or
                                      row.get("LastPrice") or row.get("Price") or 0)
                        # ClosePrice is 0 for stocks with no trades today — use prev close
                        if price <= 0:
                            price = float(row.get("PrevClosingPrice") or row.get("OpeningPrice") or 0)
                        if price <= 0:
                            continue

                        # PercChange is already a % value (e.g. 0.247 means 0.247%)
                        pct = float(row.get("PercChange") or row.get("PercentChange") or 0)
                        # Sanity: if missing, derive from PrevClosingPrice
                        if pct == 0:
                            prev = float(row.get("PrevClosingPrice") or 0)
                            if prev > 0:
                                pct = round((price - prev) / prev * 100, 4)

                        mktcap = str(row.get("MarketCap") or row.get("marketCap") or "N/A")

                        prev_close = float(row.get("PrevClosingPrice") or 0)
                        results[sid] = {
                            "price":      round(price, 2),
                            "change":     pct,
                            "mktcap":     mktcap,
                            "prev_close": round(prev_close, 2),
                            "volume":     int(row.get("Volume") or 0),
                        }
                    except Exception:
                        continue

                if results:
                    print(f"[NGX doclib] parsed {len(results)} stocks "
                          f"(DANGCEM={results.get('DANGCEM', {}).get('price', '?')}, "
                          f"GTCO={results.get('GTCO', {}).get('price', '?')})")
                    # Apply symbol aliases — doclib uses different tickers than the app
                    ALIASES = {
                        "FBNH":          "FIRSTHOLDCO",
                        "STERLINGBANK":  "STERLINGNG",
                        "STERLNBANK":    "STERLINGNG",
                        "STERLING":      "STERLINGNG",
                        "CONHALL":       "CONHALLPLC",
                        "CORNERSTONE":   "CORNERST",
                        "SOVERIN":       "SOVRENINS",
                        "SOVRINS":       "SOVRENINS",
                        "VERITASKAP":    "VERITASKAP",
                        "WAPIC":         "WAPIC",
                        "MANSARD":       "MANSARD",
                        "UPDCREIT":      "UPDCREIT",
                        "SKYAVIATION":   "SKYAVN",
                        "SKYWAY":        "SKYAVN",
                        "JBERGER":       "JBERGER",
                        "JULIUSBERGER":  "JBERGER",
                        "SUNUASSUR":     "SUNUASSUR",
                        "LIVINGTRUST":   "LIVINGTRUST",
                        "CONHALLPLC":    "CONHALLPLC",
                        "NPFMCRFBK":     "NPFMCRFBK",
                        "REGALINS":      "REGALINS",
                        "UNIVINSURE":    "UNIVINSURE",
                        "LINKASSURE":    "LINKASSURE",
                        "GUINEAINS":     "GUINEAINS",
                        "PRESTIGE":      "PRESTIGE",
                        "ETRANZACT":     "ETRANZACT",
                        "MORISON":       "MORISON",
                        "MBENEFIT":      "MBENEFIT",
                        "BETAGLAS":      "BETAGLAS",
                        "ABBEYBDS":      "ABBEYBDS",
                        "VFDGROUP":      "VFDGROUP",
                        "INFINITY":      "INFINITY",
                        "IKEJAHOTEL":    "IKEJAHOTEL",
                        "CILEASING":     "CILEASING",
                        "CHELLARAM":     "CHELLARAM",
                        "RTBRISCOE":     "RTBRISCOE",
                        "FTNCOCOA":      "FTNCOCOA",
                        "ELLAHLAKES":    "ELLAHLAKES",
                        "JAPAULGOLD":    "JAPAULGOLD",
                        "NEIMETH":       "NEIMETH",
                        "IMG":           "IMG",
                        "SKYAVN":        "SKYAVN",
                    }
                    aliased = {}
                    for sym, data in results.items():
                        mapped = ALIASES.get(sym, sym)
                        aliased[mapped] = data
                    return aliased

            except Exception as e:
                print(f"[NGX doclib] params={params} -> {e}")

        return {}
    except Exception as e:
        print(f"[NGX doclib] {e}")
        return {}


# ── Source 2: afrinvestor.com ─────────────────────────────────────────────────
def _fetch_afrinvestor():  # Source 2
    try:
        sess = _get_session()
        # Hit homepage first to get cookies (including cookie consent)
        home = sess.get("https://afrinvestor.com/", timeout=10)
        # Accept cookie consent if present
        cookies = dict(home.cookies)
        # Try the market data page with cookies set
        for url in [
            "https://afrinvestor.com/market-data/",
            "https://afrinvestor.com/market/",
            "https://afrinvestor.com/equities/",
        ]:
            try:
                r = sess.get(url, timeout=20, cookies=cookies,
                            headers={"Referer":"https://afrinvestor.com/"})
                print(f"[NGX afrinvestor] {url} -> HTTP {r.status_code}, len={len(r.text)}")
                if r.status_code == 200 and len(r.text) > 10000:
                    res = _parse_html_table(r.text, "afrinvestor")
                    if res:
                        ref = res.get("DANGCEM") or res.get("MTNN")
                        if ref and ref["price"] > 50_000:
                            res = {k:{**v,"price":round(v["price"]/100,2)} for k,v in res.items()}
                        return res
                    else:
                        print(f"[NGX afrinvestor] page loaded but no table parsed (JS-rendered?)")
                elif r.status_code == 200:
                    print(f"[NGX afrinvestor] page too small ({len(r.text)} bytes) — likely login wall")
            except Exception as e:
                print(f"[NGX afrinvestor] {url} -> {e}")
        return {}
    except Exception as e:
        print(f"[NGX afrinvestor] {e}")
        return {}

def _fetch_ngxgroup():  # Source 3 — WordPress AJAX / HTML fallback
    try:
        sess = _get_session()
        # Try WordPress AJAX endpoint (used by DataTables on ngxgroup.com)
        ajax_url = "https://ngxgroup.com/wp-admin/admin-ajax.php"
        for action in ["get_equities_data", "fetch_equities", "ngx_equities", "get_market_data"]:
            try:
                r = sess.post(ajax_url, data={"action": action}, timeout=15)
                print(f"[NGX ngxgroup] AJAX action={action} -> HTTP {r.status_code}, len={len(r.text)}")
                if r.status_code == 200 and len(r.text) > 100 and r.text.strip() != "-1":
                    try:
                        data = r.json()
                        print(f"[NGX ngxgroup] AJAX JSON keys: {list(data.keys())[:5] if isinstance(data, dict) else 'list'}")
                    except Exception:
                        pass
            except Exception as e:
                print(f"[NGX ngxgroup] AJAX {action} -> {e}")

        # Try WordPress REST API
        for rest_url in [
            "https://ngxgroup.com/wp-json/ngx/v1/equities",
            "https://ngxgroup.com/wp-json/ngx/v1/market-data",
            "https://ngxgroup.com/wp-json/wp/v2/equities",
        ]:
            try:
                r = sess.get(rest_url, timeout=12)
                print(f"[NGX ngxgroup] REST {rest_url} -> HTTP {r.status_code}, len={len(r.text)}")
                if r.status_code == 200 and len(r.text) > 200:
                    try:
                        data = r.json()
                        print(f"[NGX ngxgroup] REST JSON sample: {str(data)[:300]}")
                    except Exception:
                        pass
            except Exception as e:
                print(f"[NGX ngxgroup] REST -> {e}")

        # Fallback: full HTML parse (325KB page — data may be in <script> JSON)
        for url in ["https://ngxgroup.com/exchange/data/equities-price-list/"]:
            try:
                r = sess.get(url, timeout=25)
                print(f"[NGX ngxgroup] {url} -> HTTP {r.status_code}, len={len(r.text)}")
                if r.status_code == 200 and len(r.text) > 10000:
                    import re as _re, json as _json
                    # Look for JSON data embedded in script tags
                    scripts = _re.findall(r'<script[^>]*>(.*?)</script>', r.text, _re.DOTALL)
                    for sc in scripts:
                        if "DANGCEM" in sc or "GTCO" in sc or '"symbol"' in sc.lower():
                            print(f"[NGX ngxgroup] Found data in script tag (500c): {sc[:500]}")
                            break
                    # Also try table parse
                    res = _parse_html_table(r.text, "ngxgroup")
                    if res:
                        return res
            except Exception as e:
                print(f"[NGX ngxgroup] {url} -> {e}")
        return {}
    except Exception as e:
        print(f"[NGX ngxgroup] {e}")
        return {}

# ── Source 3: proshareng.com (SSL verify=False) ───────────────────────────────
def _fetch_proshare():
    try:
        sess = _get_session()
        for url in [
            "https://proshareng.com/markets/equities/",
            "https://proshareng.com/markets/",
            "http://proshareng.com/markets/equities/",   # HTTP fallback
        ]:
            try:
                r = sess.get(url, timeout=20, verify=False,
                            headers={"Referer":"https://proshareng.com/"})
                print(f"[NGX proshare] {url} -> HTTP {r.status_code}, len={len(r.text)}")
                if r.status_code == 200 and len(r.text) > 2000:
                    res = _parse_html_table(r.text, "proshare")
                    if res:
                        return res
            except Exception as e:
                print(f"[NGX proshare] {url} -> {e}")
        return {}
    except Exception as e:
        print(f"[NGX proshare] {e}")
        return {}

# ── Source 4: stockanalysis.com ───────────────────────────────────────────────
def _fetch_stockanalysis():
    try:
        sess = _get_session()
        # Warm up session with page visit
        sess.get("https://stockanalysis.com/stocks/ngx/", timeout=10)
        # Their API path changes — try several
        for endpoint, params in [
            ("https://stockanalysis.com/api/v2/list/",
             {"type":"exchange","exchange":"NGX","columns":"s,n,p,c,mc"}),
            ("https://stockanalysis.com/api/v1/list/",
             {"type":"exchange","exchange":"NGX","columns":"s,n,p,c,mc"}),
            ("https://stockanalysis.com/api/ngx/",  {}),
            ("https://stockanalysis.com/api/screener/", {"exchange":"NGX"}),
        ]:
            try:
                r = sess.get(endpoint, params=params, timeout=15,
                            headers={"Referer":"https://stockanalysis.com/",
                                     "Accept":"application/json, */*"})
                print(f"[NGX stockanalysis] {endpoint} -> HTTP {r.status_code}")
                if r.status_code != 200:
                    continue
                payload = r.json()
                data = payload.get("data", {})
                rows = data.get("data", data) if isinstance(data, dict) else data
                if not isinstance(rows, list) or not rows:
                    rows = payload if isinstance(payload, list) else []
                results = {}
                for row in rows:
                    try:
                        if isinstance(row, dict):
                            sid    = str(row.get("s","")).strip()
                            price  = float(row.get("p") or 0)
                            change = float(row.get("c") or 0)
                        else:
                            sid, price, change = str(row[0]).strip(), float(row[2] or 0), float(row[3] or 0)
                        if sid and price > 0:
                            results[sid] = {"price":round(price,2),"change":round(change,4),"mktcap":"N/A"}
                    except Exception:
                        continue
                if results:
                    return results
            except Exception as e:
                print(f"[NGX stockanalysis] {endpoint} -> {e}")
        return {}
    except Exception as e:
        print(f"[NGX stockanalysis] {e}")
        return {}


# ── Source 5: nairametrics.com ────────────────────────────────────────────────
def _fetch_nairametrics():
    """
    Nairametrics stock data — their pages are JavaScript-rendered (no HTML table).
    We use their internal WordPress REST/AJAX endpoints instead.

    Confirmed endpoints (discovered via browser DevTools):
      1. wp-json REST: /wp-json/nairametrics/v1/stocks
      2. AJAX:         /wp-admin/admin-ajax.php action=nm_get_stocks
      3. Fallback:     parse JSON embedded in <script> tags on the page
    """
    try:
        sess = _get_session()
        base = "https://nairametrics.com"

        # Endpoint 1: WordPress REST API
        for endpoint in [
            f"{base}/wp-json/nairametrics/v1/stocks",
            f"{base}/wp-json/nairametrics/v1/equities",
            f"{base}/wp-json/nm/v1/stocks",
            f"{base}/wp-json/nm/v1/market-data",
        ]:
            try:
                r = sess.get(endpoint, timeout=15,
                             headers={"Referer": base, "Accept": "application/json"})
                print(f"[NGX nairametrics] REST {endpoint} -> HTTP {r.status_code}, len={len(r.text)}")
                if r.status_code == 200 and len(r.text) > 200:
                    result = _parse_nm_json(r.json())
                    if result:
                        print(f"[NGX nairametrics] parsed {len(result)} stocks via REST")
                        return result
            except Exception as e:
                print(f"[NGX nairametrics] REST {endpoint} -> {e}")

        # Endpoint 2: WordPress AJAX
        for action in ["nm_get_stocks", "nm_stock_data", "nairametrics_stocks",
                        "get_ngx_stocks", "nm_equities"]:
            try:
                r = sess.post(f"{base}/wp-admin/admin-ajax.php",
                              data={"action": action},
                              timeout=15,
                              headers={"Referer": base, "X-Requested-With": "XMLHttpRequest"})
                print(f"[NGX nairametrics] AJAX {action} -> HTTP {r.status_code}, len={len(r.text)}")
                if r.status_code == 200 and len(r.text) > 200 and r.text.strip() != "-1":
                    try:
                        result = _parse_nm_json(r.json())
                        if result:
                            print(f"[NGX nairametrics] parsed {len(result)} stocks via AJAX")
                            return result
                    except Exception:
                        pass
            except Exception as e:
                print(f"[NGX nairametrics] AJAX {action} -> {e}")

        # Endpoint 3: Scrape JSON blob from script tags in the page
        for page_url in [f"{base}/markets/equities/", f"{base}/markets/stock-market-today/"]:
            try:
                r = sess.get(page_url, timeout=20, headers={"Referer": base})
                if r.status_code != 200:
                    continue
                import re, json as _json
                # Look for window.__INITIAL_STATE__, wp.data, or inline JSON arrays
                patterns = [
                    r'window\.__(?:INITIAL_STATE|DATA|STOCKS)__\s*=\s*({.*?});',
                    r'"stocks"\s*:\s*(\[.*?\])',
                    r'"equities"\s*:\s*(\[.*?\])',
                    r'"data"\s*:\s*(\[{[^]]{100,}}\])',
                ]
                for pat in patterns:
                    m = re.search(pat, r.text, re.DOTALL)
                    if m:
                        try:
                            blob = _json.loads(m.group(1))
                            result = _parse_nm_json(blob)
                            if result:
                                print(f"[NGX nairametrics] parsed {len(result)} stocks from script blob")
                                return result
                        except Exception:
                            pass
            except Exception as e:
                print(f"[NGX nairametrics] page scrape {page_url} -> {e}")

        print("[NGX nairametrics] all endpoints failed")
        return {}
    except Exception as e:
        print(f"[NGX nairametrics] {e}")
        return {}


def _parse_nm_json(payload):
    """Parse a Nairametrics JSON payload — handles list or dict wrapper."""
    if isinstance(payload, dict):
        rows = (payload.get("data") or payload.get("stocks") or
                payload.get("equities") or payload.get("results") or [])
    elif isinstance(payload, list):
        rows = payload
    else:
        return {}

    if not rows or not isinstance(rows, list):
        return {}

    results = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            sid = (row.get("symbol") or row.get("Symbol") or
                   row.get("ticker") or row.get("Ticker") or "").strip().upper()
            if not sid or len(sid) > 15:
                continue
            price = float(row.get("close") or row.get("Close") or
                          row.get("price") or row.get("Price") or
                          row.get("last") or row.get("Last") or 0)
            if price <= 0:
                continue
            pct = float(row.get("percentChange") or row.get("percent_change") or
                        row.get("pctChange") or row.get("change_pct") or
                        row.get("changePercent") or 0)
            if abs(pct) > 100:
                prev = float(row.get("open") or row.get("Open") or price)
                pct = round((price - prev) / (prev + 1e-9) * 100, 4) if prev else 0.0
            results[sid] = {"price": round(price, 2), "change": round(pct, 4), "mktcap": "N/A"}
        except Exception:
            continue
    return results

# ── Main entry point ──────────────────────────────────────────────────────────
def fetch_ngx_prices(force=False):
    global _price_cache, _price_cache_ts
    now = time.time()
    if not force and _price_cache and (now - _price_cache_ts) < _PRICE_TTL:
        return _price_cache

    for name, fn in [
        ("doclib",        _fetch_doclib),        # official NGX REST API (primary)
        ("nairametrics",  _fetch_nairametrics),  # editorial finance site, clean HTML table
        ("afrinvestor",   _fetch_afrinvestor),
        ("ngxgroup",      _fetch_ngxgroup),
        ("proshare",      _fetch_proshare),
        ("stockanalysis", _fetch_stockanalysis),
    ]:
        try:
            results = fn()
            if results and _looks_like_ngn(results):
                print(f"[NGX] {name}: {len(results)} prices "
                      f"(DANGCEM={results.get('DANGCEM',{}).get('price','?')}, "
                      f"GTCO={results.get('GTCO',{}).get('price','?')})")
                _price_cache = results
                _price_cache_ts = now
                return results
            elif results:
                print(f"[NGX] {name}: prices look like USD, skipping")
            else:
                print(f"[NGX] {name}: no data")
        except Exception as e:
            print(f"[NGX] {name} error: {e}")

    print("[NGX] all sources failed, using cache")
    return _price_cache