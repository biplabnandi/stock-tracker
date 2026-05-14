"""
Fetch the full Nifty Midcap 150 and Smallcap 250 constituent lists from NSE
and generate data/universe.py with all tickers.
"""
import csv
import io
import time
import requests
import yfinance as yf

MIDCAP_URL = "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv"
SMALLCAP_URL = "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv"

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


def main():
    print("Fetching Nifty Midcap 150 list...")
    try:
        midcap_data = fetch_csv(MIDCAP_URL)
        print(f"  Got {len(midcap_data)} midcap stocks from NSE")
    except Exception as e:
        print(f"  Failed to fetch from NSE: {e}")
        print("  Using fallback method...")
        midcap_data = []

    print("Fetching Nifty Smallcap 250 list...")
    try:
        smallcap_data = fetch_csv(SMALLCAP_URL)
        print(f"  Got {len(smallcap_data)} smallcap stocks from NSE")
    except Exception as e:
        print(f"  Failed to fetch from NSE: {e}")
        smallcap_data = []

    # Build stock entries
    midcaps = []
    for row in midcap_data:
        symbol = row.get("Symbol", "").strip()
        name = row.get("Company Name", "").strip()
        industry = row.get("Industry", "").strip()
        if symbol:
            midcaps.append({
                "ticker": f"{symbol}.NS",
                "name": name[:40],
                "sector": map_sector(industry),
            })

    smallcaps = []
    for row in smallcap_data:
        symbol = row.get("Symbol", "").strip()
        name = row.get("Company Name", "").strip()
        industry = row.get("Industry", "").strip()
        if symbol:
            smallcaps.append({
                "ticker": f"{symbol}.NS",
                "name": name[:40],
                "sector": map_sector(industry),
            })

    print(f"\nTotal: {len(midcaps)} midcap + {len(smallcaps)} smallcap = {len(midcaps)+len(smallcaps)}")

    # Generate universe.py
    lines = [
        '"""',
        'Stock Universe — Full Nifty Midcap 150 + Smallcap 250 constituents.',
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
    lines.append('')
    lines.append('def get_all_stocks():')
    lines.append('    """Return all stocks with their category label."""')
    lines.append('    stocks = []')
    lines.append('    for s in MIDCAP_STOCKS:')
    lines.append('        stocks.append({**s, "category": "midcap"})')
    lines.append('    for s in SMALLCAP_STOCKS:')
    lines.append('        stocks.append({**s, "category": "smallcap"})')
    lines.append('    return stocks')
    lines.append('')
    lines.append('')
    lines.append('def get_stock_count():')
    lines.append('    """Return count of midcap, smallcap, and total stocks."""')
    lines.append('    return {')
    lines.append('        "midcap": len(MIDCAP_STOCKS),')
    lines.append('        "smallcap": len(SMALLCAP_STOCKS),')
    lines.append('        "total": len(MIDCAP_STOCKS) + len(SMALLCAP_STOCKS),')
    lines.append('    }')
    lines.append('')

    with open("data/universe.py", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Written data/universe.py with {len(midcaps)+len(smallcaps)} stocks")


if __name__ == "__main__":
    main()
