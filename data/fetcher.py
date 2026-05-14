"""
Data Fetcher — Retrieves stock data from yfinance with rate limiting.
"""

import time
import logging
import yfinance as yf
import pandas as pd
from config import FETCH_DELAY_SECONDS, HISTORY_PERIOD, MAX_RETRIES

logger = logging.getLogger(__name__)


def fetch_stock_data(ticker_symbol: str, retries: int = MAX_RETRIES) -> dict | None:
    """
    Fetch all required data for a single stock.

    Returns a dict with keys: info, history, quarterly_financials,
    quarterly_balance_sheet, dividends, actions, or None on failure.
    """
    for attempt in range(retries + 1):
        try:
            ticker = yf.Ticker(ticker_symbol)

            # Fetch price history (1 year)
            history = ticker.history(period=HISTORY_PERIOD)
            if history.empty:
                logger.warning(f"No price history for {ticker_symbol}")
                return None

            # Flatten multi-level columns (yfinance 1.3+ returns MultiIndex)
            if isinstance(history.columns, pd.MultiIndex):
                history.columns = history.columns.get_level_values(0)

            # Drop rows where Close is NaN (e.g. today's incomplete data)
            history = history.dropna(subset=["Close"])
            if history.empty:
                logger.warning(f"No valid price data for {ticker_symbol}")
                return None
            # Fetch fundamental data
            info = {}
            try:
                info = ticker.info or {}
            except Exception:
                logger.warning(f"Could not fetch info for {ticker_symbol}")

            # Quarterly financials
            quarterly_financials = pd.DataFrame()
            try:
                quarterly_financials = ticker.quarterly_financials
                if quarterly_financials is None:
                    quarterly_financials = pd.DataFrame()
            except Exception:
                pass

            # Quarterly balance sheet
            quarterly_balance_sheet = pd.DataFrame()
            try:
                quarterly_balance_sheet = ticker.quarterly_balance_sheet
                if quarterly_balance_sheet is None:
                    quarterly_balance_sheet = pd.DataFrame()
            except Exception:
                pass

            # Dividends and corporate actions
            dividends = pd.Series(dtype=float)
            try:
                dividends = ticker.dividends
                if dividends is None:
                    dividends = pd.Series(dtype=float)
            except Exception:
                pass

            actions = pd.DataFrame()
            try:
                actions = ticker.actions
                if actions is None:
                    actions = pd.DataFrame()
            except Exception:
                pass

            # Rate limiting
            time.sleep(FETCH_DELAY_SECONDS)

            return {
                "info": info,
                "history": history,
                "quarterly_financials": quarterly_financials,
                "quarterly_balance_sheet": quarterly_balance_sheet,
                "dividends": dividends,
                "actions": actions,
            }

        except Exception as e:
            logger.error(
                f"Error fetching {ticker_symbol} (attempt {attempt + 1}): {e}"
            )
            if attempt < retries:
                time.sleep(FETCH_DELAY_SECONDS * 2)
            continue

    return None


def compute_price_changes(history: pd.DataFrame) -> dict:
    """
    Compute price change percentages over various periods.
    """
    if history.empty or len(history) < 2:
        return {
            "change_1d": 0,
            "change_1w": 0,
            "change_1m": 0,
            "change_3m": 0,
            "change_6m": 0,
        }

    current_price = history["Close"].iloc[-1]

    def pct_change(days_ago):
        idx = min(days_ago, len(history) - 1)
        old_price = history["Close"].iloc[-idx - 1] if idx < len(history) else history["Close"].iloc[0]
        if old_price == 0:
            return 0
        return round(((current_price - old_price) / old_price) * 100, 2)

    return {
        "change_1d": pct_change(1),
        "change_1w": pct_change(5),
        "change_1m": pct_change(21),
        "change_3m": pct_change(63),
        "change_6m": pct_change(126),
    }
