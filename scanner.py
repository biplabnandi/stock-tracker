"""
Scanner — Main orchestrator that runs the full stock analysis pipeline.

Fetches data → Analyzes fundamentals/technicals/events → Scores → Outputs JSON.
"""

import json
import math
import os
import sys
import logging
from datetime import datetime

from data.universe import get_all_stocks, get_stock_count
from data.fetcher import fetch_stock_data, compute_price_changes
from analyzers.fundamental import analyze_fundamentals
from analyzers.technical import analyze_technicals
from analyzers.events import analyze_events
from scoring.scorer import compute_composite_score, generate_summary
from config import OUTPUT_DIR, OUTPUT_FILE

# ─── Logging Setup ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scanner")


def sanitize_data(obj):
    """Recursively replace NaN/Inf float values with None for JSON safety."""
    if isinstance(obj, dict):
        return {k: sanitize_data(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_data(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj


def scan_stock(stock_info: dict) -> dict | None:
    """
    Run the full analysis pipeline for a single stock.

    Returns a result dict or None if the stock couldn't be analyzed.
    """
    ticker = stock_info["ticker"]
    name = stock_info["name"]
    sector = stock_info["sector"]
    category = stock_info["category"]

    logger.info(f"Scanning {ticker} ({name})...")

    # ── Fetch data ─────────────────────────────────────────────────
    data = fetch_stock_data(ticker)
    if data is None:
        logger.warning(f"  ✗ Skipping {ticker} — no data available")
        return None

    # ── Analyze ────────────────────────────────────────────────────
    try:
        fundamental = analyze_fundamentals(data)
    except Exception as e:
        logger.error(f"  ✗ Fundamental analysis failed for {ticker}: {e}")
        fundamental = {"score": 30, "values": {}, "metric_scores": {}}

    try:
        technical = analyze_technicals(data)
    except Exception as e:
        logger.error(f"  ✗ Technical analysis failed for {ticker}: {e}")
        technical = {"score": 30, "values": {}, "signals": {}, "metric_scores": {}}

    try:
        events = analyze_events(data)
    except Exception as e:
        logger.error(f"  ✗ Event analysis failed for {ticker}: {e}")
        events = {"score": 40, "details": {}, "metric_scores": {}}

    # ── Score ──────────────────────────────────────────────────────
    scoring = compute_composite_score(
        fundamental["score"],
        technical["score"],
        events["score"],
    )

    # ── Price data ────────────────────────────────────────────────
    history = data.get("history")
    info = data.get("info", {})
    current_price = float(history["Close"].iloc[-1]) if not history.empty else 0
    price_changes = compute_price_changes(history)

    result = {
        "ticker": ticker.replace(".NS", ""),
        "full_ticker": ticker,
        "name": name,
        "sector": sector,
        "category": category,
        "current_price": round(current_price, 2),
        "market_cap": info.get("marketCap"),
        "industry": info.get("industry", sector),
        **price_changes,
        "scores": {
            "fundamental": fundamental["score"],
            "technical": technical["score"],
            "event": events["score"],
            "composite": scoring["composite"],
        },
        "tier": scoring["tier"],
        "fundamentals": fundamental.get("values", {}),
        "fundamental_scores": fundamental.get("metric_scores", {}),
        "technicals": technical.get("values", {}),
        "technical_scores": technical.get("metric_scores", {}),
        "events": events.get("details", {}),
        "event_scores": events.get("metric_scores", {}),
    }

    tier_emoji = {"strong_buy": "🟢", "buy": "🔵", "watch": "🟡", "avoid": "🔴"}
    emoji = tier_emoji.get(scoring["tier"], "⚪")
    logger.info(
        f"  {emoji} {ticker}: Score={scoring['composite']} "
        f"(F={fundamental['score']}, T={technical['score']}, E={events['score']}) "
        f"→ {scoring['tier'].upper()}"
    )

    return sanitize_data(result)


def run_scan(subset: list[dict] | None = None):
    """
    Run the full scan across all stocks in the universe.

    Args:
        subset: Optional list of stocks to scan (for testing). If None, scans all.
    """
    stocks = subset if subset else get_all_stocks()
    counts = get_stock_count()

    logger.info("=" * 60)
    logger.info("STOCK GROWTH TRACKER — Scan Starting")
    logger.info(f"Universe: {counts['total']} stocks ({counts['midcap']} midcap, {counts['smallcap']} smallcap, {counts.get('microcap', 0)} microcap)")
    logger.info(f"Scanning: {len(stocks)} stocks")
    logger.info("=" * 60)

    results = []
    failed = 0

    for i, stock in enumerate(stocks, 1):
        logger.info(f"\n[{i}/{len(stocks)}] ─────────────────────────────")
        result = scan_stock(stock)
        if result:
            results.append(result)
        else:
            failed += 1

    # ── Sort by composite score (descending) ───────────────────────
    results.sort(key=lambda x: x["scores"]["composite"], reverse=True)

    # ── Generate summary ───────────────────────────────────────────
    summary = generate_summary(results)

    # ── Historical score tracking ──────────────────────────────
    history_file = os.path.join(OUTPUT_DIR, "history.json")
    history = []
    prev_scores = {}
    try:
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            # Get most recent scan's scores for delta calculation
            if history:
                for entry in history[-1].get("scores", []):
                    prev_scores[entry["ticker"]] = entry["composite"]
    except Exception as e:
        logger.warning(f"Could not load history: {e}")

    # Build per-ticker score timeline from history (before appending current)
    ticker_timeline = {}  # ticker -> [score1, score2, ...] in chronological order
    for scan_entry in history:
        for s in scan_entry.get("scores", []):
            ticker_timeline.setdefault(s["ticker"], []).append(s["composite"])

    # Add score_change, score_history, and score_streak to each result
    for stock in results:
        ticker = stock["ticker"]
        prev = prev_scores.get(ticker)
        if prev is not None:
            stock["score_change"] = round(stock["scores"]["composite"] - prev, 1)
        else:
            stock["score_change"] = None

        # Score history: past scores + current (keep last 15 data points)
        past = ticker_timeline.get(ticker, [])
        current = stock["scores"]["composite"]
        full_history = past + [current]
        stock["score_history"] = full_history[-15:]

        # Score streak: count consecutive improvements (+) or declines (-)
        streak = 0
        if len(full_history) >= 2:
            # Walk backwards from the most recent pair
            for i in range(len(full_history) - 1, 0, -1):
                diff = full_history[i] - full_history[i - 1]
                if diff > 0:
                    if streak >= 0:
                        streak += 1
                    else:
                        break  # direction changed
                elif diff < 0:
                    if streak <= 0:
                        streak -= 1
                    else:
                        break
                else:
                    break  # no change, streak stops
        stock["score_streak"] = streak

    # Append current scan to history (keep last 30 entries)
    scan_date = datetime.now().isoformat()
    history.append({
        "date": scan_date,
        "scores": [
            {"ticker": s["ticker"], "composite": s["scores"]["composite"]}
            for s in results
        ],
    })
    history = history[-30:]  # Keep last 30 scans

    # ── Build output ───────────────────────────────────────────────
    output = {
        "scan_date": scan_date,
        "total_scanned": len(stocks),
        "total_analyzed": len(results),
        "total_failed": failed,
        "stocks": results,
        "summary": summary,
    }

    # ── Write JSON ─────────────────────────────────────────────────
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    # Write history
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, default=str)
    logger.info(f"  History:  {len(history)} scans saved")

    logger.info("\n" + "=" * 60)
    logger.info("SCAN COMPLETE")
    logger.info(f"  Analyzed: {len(results)}/{len(stocks)} stocks")
    logger.info(f"  Failed:   {failed}")
    logger.info(f"  Strong Buy: {summary['strong_buy']}")
    logger.info(f"  Buy:        {summary['buy']}")
    logger.info(f"  Watch:      {summary['watch']}")
    logger.info(f"  Avoid:      {summary['avoid']}")
    logger.info(f"  Avg Score:  {summary['avg_score']}")
    logger.info(f"  Output:     {OUTPUT_FILE}")
    logger.info("=" * 60)

    return output


if __name__ == "__main__":
    # Allow passing --test flag for quick test with 5 stocks
    if "--test" in sys.argv:
        from data.universe import MIDCAP_STOCKS, SMALLCAP_STOCKS

        test_stocks = [
            {**MIDCAP_STOCKS[0], "category": "midcap"},
            {**MIDCAP_STOCKS[5], "category": "midcap"},
            {**SMALLCAP_STOCKS[0], "category": "smallcap"},
            {**SMALLCAP_STOCKS[8], "category": "smallcap"},
            {**SMALLCAP_STOCKS[15], "category": "smallcap"},
        ]
        run_scan(subset=test_stocks)
    else:
        run_scan()
