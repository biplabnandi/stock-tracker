"""
Fetch the full Nifty Midcap 150, Smallcap 250, and Microcap 250 constituent
lists from NSE and generate data/universe.py with all tickers.
"""
import csv
import io
import time
import requests
import yfinance as yf

MIDCAP_URLS = [
    "https://www.niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv",
    "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
]
SMALLCAP_URLS = [
    "https://www.niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv",
    "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv",
]
MICROCAP_URLS = [
    "https://www.niftyindices.com/IndexConstituent/ind_niftymicrocap250_list.csv",
    "https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/csv,text/plain,*/*",
}

SECTOR_MAP = {
    "Financial Services": "Finance",
    "Information Technology": "IT",
    "Automobile and Auto Components": "Auto",
    "Healthcare": "Healthcare",
    "Pharmaceuticals": "Healthcare",
    "Fast Moving Consumer Goods": "FMCG",
    "Consumer Durables": "Consumer",
    "Consumer Services": "Consumer",
    "Capital Goods": "Industrial",
    "Construction": "Industrial",
    "Construction Materials": "Industrial",
    "Chemicals": "Chemicals",
    "Oil Gas & Consumable Fuels": "Energy",
    "Power": "Energy",
    "Metals & Mining": "Metals",
    "Realty": "Real Estate",
    "Media Entertainment & Publication": "Media",
    "Textiles": "Textile",
    "Telecommunication": "Telecom",
    "Services": "Services",
    "Diversified": "Diversified",
    "Forest Materials": "Materials",
}


def fetch_csv(url):
    """Fetch CSV from NSE and parse into list of dicts."""
    session = requests.Session()
    # Hit NSE homepage first for cookies
    session.get("https://www.nseindia.com", headers=HEADERS, timeout=10)
    time.sleep(1)
    resp = session.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    return list(reader)


def map_sector(industry):
    """Map NSE industry to our simplified sector."""
    for key, val in SECTOR_MAP.items():
        if key.lower() in industry.lower():
            return val
    return industry[:20] if industry else "Other"


def validate_ticker(symbol):
    """Quick check if yfinance can fetch data for this ticker."""
    try:
        t = yf.Ticker(f"{symbol}.NS")
        h = t.history(period="5d")
        return not h.empty
    except Exception:
        return False


def _build_entries(raw_data):
    """Convert raw CSV rows into stock entry dicts."""
    entries = []
    for row in raw_data:
        symbol = row.get("Symbol", "").strip()
        name = row.get("Company Name", "").strip()
        industry = row.get("Industry", "").strip()
        if symbol:
            entries.append({
                "ticker": f"{symbol}.NS",
                "name": name[:40],
                "sector": map_sector(industry),
            })
    return entries


def fetch_and_build(urls, list_name):
    """Try multiple URLs, return the first successful list of stock entries."""
    for url in urls:
        try:
            print(f"  Trying: {url}")
            raw_data = fetch_csv(url)
            entries = _build_entries(raw_data)
            if entries:
                print(f"  Got {len(entries)} {list_name} stocks from NSE")
                return entries
            else:
                print(f"  Failed: Downloaded file contained no valid stock symbols (got {len(raw_data)} rows)")
        except Exception as e:
            print(f"  Failed: {e}")
    print(f"  All {list_name} URLs failed — preserving existing list from universe.py")
    return []


def main():
    print("Fetching Nifty Midcap 150 list...")
    midcaps = fetch_and_build(MIDCAP_URLS, "midcap")

    print("Fetching Nifty Smallcap 250 list...")
    smallcaps = fetch_and_build(SMALLCAP_URLS, "smallcap")

    print("Fetching Nifty Microcap 250 list...")
    microcaps = fetch_and_build(MICROCAP_URLS, "microcap")

    # Fallback: preserve existing data from universe.py when fetch fails
    if not midcaps or not smallcaps or not microcaps:
        try:
            from data.universe import MIDCAP_STOCKS, SMALLCAP_STOCKS, MICROCAP_STOCKS
            if not midcaps and MIDCAP_STOCKS:
                midcaps = MIDCAP_STOCKS
                print(f"  Preserved {len(midcaps)} existing midcap stocks")
            if not smallcaps and SMALLCAP_STOCKS:
                smallcaps = SMALLCAP_STOCKS
                print(f"  Preserved {len(smallcaps)} existing smallcap stocks")
            if not microcaps and MICROCAP_STOCKS:
                microcaps = MICROCAP_STOCKS
                print(f"  Preserved {len(microcaps)} existing microcap stocks")
        except ImportError:
            print("  Warning: Could not import existing universe.py for fallback")

    total = len(midcaps) + len(smallcaps) + len(microcaps)
    print(f"\nTotal: {len(midcaps)} midcap + {len(smallcaps)} smallcap + {len(microcaps)} microcap = {total}")

    # Generate universe.py
    lines = [
        '"""',
        'Stock Universe — Full Nifty Midcap 150 + Smallcap 250 + Microcap 250 constituents.',
        '',
        'Auto-generated from NSE index data.',
        'Tickers use the .NS suffix for yfinance compatibility.',
        '"""',
        '',
        '',
        'MIDCAP_STOCKS = [',
    ]
    for s in midcaps:
        lines.append(f'    {{"ticker": "{s["ticker"]}", "name": "{s["name"]}", "sector": "{s["sector"]}"}},')
    lines.append(']')
    lines.append('')
    lines.append('SMALLCAP_STOCKS = [')
    for s in smallcaps:
        lines.append(f'    {{"ticker": "{s["ticker"]}", "name": "{s["name"]}", "sector": "{s["sector"]}"}},')
    lines.append(']')
    lines.append('')
    lines.append('MICROCAP_STOCKS = [')
    for s in microcaps:
        lines.append(f'    {{"ticker": "{s["ticker"]}", "name": "{s["name"]}", "sector": "{s["sector"]}"}},')
    lines.append(']')
    lines.append('')
    lines.append('')
    lines.append('def get_all_stocks():')
    lines.append('    """Return all stocks with their category label."""')
    lines.append('    stocks = []')
    lines.append('    for s in MIDCAP_STOCKS:')
    lines.append('        stocks.append({**s, "category": "midcap"})')
    lines.append('    for s in SMALLCAP_STOCKS:')
    lines.append('        stocks.append({**s, "category": "smallcap"})')
    lines.append('    for s in MICROCAP_STOCKS:')
    lines.append('        stocks.append({**s, "category": "microcap"})')
    lines.append('    return stocks')
    lines.append('')
    lines.append('')
    lines.append('def get_stock_count():')
    lines.append('    """Return count of midcap, smallcap, microcap, and total stocks."""')
    lines.append('    return {')
    lines.append('        "midcap": len(MIDCAP_STOCKS),')
    lines.append('        "smallcap": len(SMALLCAP_STOCKS),')
    lines.append('        "microcap": len(MICROCAP_STOCKS),')
    lines.append('        "total": len(MIDCAP_STOCKS) + len(SMALLCAP_STOCKS) + len(MICROCAP_STOCKS),')
    lines.append('    }')
    lines.append('')

    with open("data/universe.py", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Written data/universe.py with {total} stocks")


if __name__ == "__main__":
    main()
