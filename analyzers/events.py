"""
Event Tracker — Evaluates corporate events and catalysts that drive mid-term growth.

Tracks quarterly results, dividends, corporate actions, and momentum events.
"""

import logging
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)


def _score_quarterly_results(financials: pd.DataFrame) -> tuple[int, dict]:
    """
    Score based on recent quarterly results quality.
    Looks at revenue and profit trends across last 2-4 quarters.
    """
    result_info = {
        "quarters_available": 0,
        "revenue_trend": "unknown",
        "profit_trend": "unknown",
        "result_surprise": "neutral",
    }

    if financials.empty or len(financials.columns) < 2:
        return 40, result_info

    result_info["quarters_available"] = len(financials.columns)

    # Revenue trend
    rev_score = 50
    try:
        revenue_row = None
        for name in ["Total Revenue", "TotalRevenue", "Revenue"]:
            if name in financials.index:
                revenue_row = financials.loc[name]
                break

        if revenue_row is not None and len(revenue_row) >= 2:
            recent_rev = revenue_row.iloc[0]
            prev_rev = revenue_row.iloc[1]
            if prev_rev and prev_rev > 0:
                rev_growth = ((recent_rev - prev_rev) / abs(prev_rev)) * 100
                if rev_growth > 20:
                    rev_score = 90
                    result_info["revenue_trend"] = "strong_growth"
                elif rev_growth > 10:
                    rev_score = 75
                    result_info["revenue_trend"] = "growth"
                elif rev_growth > 0:
                    rev_score = 60
                    result_info["revenue_trend"] = "mild_growth"
                elif rev_growth > -10:
                    rev_score = 35
                    result_info["revenue_trend"] = "mild_decline"
                else:
                    rev_score = 15
                    result_info["revenue_trend"] = "decline"
    except Exception:
        pass

    # Profit trend
    profit_score = 50
    try:
        profit_row = None
        for name in ["Net Income", "NetIncome", "Net Income Common Stockholders"]:
            if name in financials.index:
                profit_row = financials.loc[name]
                break

        if profit_row is not None and len(profit_row) >= 2:
            recent_profit = profit_row.iloc[0]
            prev_profit = profit_row.iloc[1]
            if prev_profit and prev_profit != 0:
                profit_growth = ((recent_profit - prev_profit) / abs(prev_profit)) * 100
                if profit_growth > 25:
                    profit_score = 90
                    result_info["profit_trend"] = "strong_growth"
                    result_info["result_surprise"] = "positive"
                elif profit_growth > 10:
                    profit_score = 75
                    result_info["profit_trend"] = "growth"
                    result_info["result_surprise"] = "positive"
                elif profit_growth > 0:
                    profit_score = 60
                    result_info["profit_trend"] = "mild_growth"
                elif profit_growth > -15:
                    profit_score = 35
                    result_info["profit_trend"] = "mild_decline"
                    result_info["result_surprise"] = "negative"
                else:
                    profit_score = 15
                    result_info["profit_trend"] = "decline"
                    result_info["result_surprise"] = "negative"
    except Exception:
        pass

    # Consecutive growth bonus
    consecutive_bonus = 0
    try:
        if profit_row is not None and len(profit_row) >= 3:
            all_growing = all(
                profit_row.iloc[i] > profit_row.iloc[i + 1]
                for i in range(min(3, len(profit_row) - 1))
            )
            if all_growing:
                consecutive_bonus = 10
    except Exception:
        pass

    score = int((rev_score * 0.45 + profit_score * 0.55) + consecutive_bonus)
    return min(100, score), result_info


def _score_dividends(dividends: pd.Series) -> tuple[int, bool]:
    """Score based on recent dividend history."""
    if dividends is None or dividends.empty:
        return 40, False  # Neutral

    try:
        now = datetime.now()
        six_months_ago = now - timedelta(days=180)

        # Check for recent dividends (within 6 months)
        recent_divs = dividends[dividends.index >= pd.Timestamp(six_months_ago)]
        if len(recent_divs) > 0:
            return 75, True  # Recent dividend is a positive signal
        elif len(dividends) > 0:
            return 55, False  # Has dividend history but not recent
    except Exception:
        pass

    return 40, False


def _score_corporate_actions(actions: pd.DataFrame) -> tuple[int, bool]:
    """Score based on recent corporate actions (splits, bonuses)."""
    if actions is None or actions.empty:
        return 45, False  # Neutral

    try:
        now = datetime.now()
        six_months_ago = now - timedelta(days=180)

        recent_actions = actions[actions.index >= pd.Timestamp(six_months_ago)]

        # Check for stock splits
        if "Stock Splits" in recent_actions.columns:
            splits = recent_actions["Stock Splits"]
            if any(splits > 0):
                return 80, True  # Recent split is bullish

    except Exception:
        pass

    return 45, False


def _score_momentum_events(history: pd.DataFrame, info: dict) -> tuple[int, dict]:
    """Score based on price momentum events (breakouts, new highs)."""
    events = {
        "near_52w_high": False,
        "above_all_sma": False,
        "recent_breakout": False,
    }

    if history.empty or len(history) < 21:
        return 40, events

    try:
        current_price = float(history["Close"].iloc[-1])
        high_52w = info.get("fiftyTwoWeekHigh", 0)
        low_52w = info.get("fiftyTwoWeekLow", 0)

        # Near 52-week high (within 5%)
        if high_52w and current_price >= high_52w * 0.95:
            events["near_52w_high"] = True

        # Check for recent breakout (price broke above 1-month high)
        one_month_high = float(history["High"].tail(21).max())
        prev_month_high = float(history["High"].iloc[-42:-21].max()) if len(history) >= 42 else one_month_high

        if current_price > prev_month_high and prev_month_high > 0:
            events["recent_breakout"] = True

        # Score based on events
        score = 45
        if events["near_52w_high"]:
            score += 20
        if events["recent_breakout"]:
            score += 15

        return min(100, score), events

    except Exception:
        return 40, events


def analyze_events(stock_data: dict) -> dict:
    """
    Analyze corporate events and catalysts for a stock.

    Args:
        stock_data: Dict from fetcher containing all stock data.

    Returns:
        Dict with event scores, details, and composite score.
    """
    financials = stock_data.get("quarterly_financials", pd.DataFrame())
    dividends = stock_data.get("dividends", pd.Series(dtype=float))
    actions = stock_data.get("actions", pd.DataFrame())
    history = stock_data.get("history", pd.DataFrame())
    info = stock_data.get("info", {})

    # ── Score each event category ──────────────────────────────────
    results_score, results_info = _score_quarterly_results(financials)
    dividend_score, has_recent_dividend = _score_dividends(dividends)
    action_score, has_recent_action = _score_corporate_actions(actions)
    momentum_score, momentum_events = _score_momentum_events(history, info)

    metric_scores = {
        "results_score": results_score,
        "dividend_score": dividend_score,
        "action_score": action_score,
        "momentum_score": momentum_score,
    }

    # ── Composite (weighted average) ───────────────────────────────
    weights = {
        "results_score": 0.45,
        "dividend_score": 0.15,
        "action_score": 0.10,
        "momentum_score": 0.30,
    }

    composite = sum(metric_scores[k] * weights[k] for k in weights)
    composite = round(composite, 1)

    return {
        "score": composite,
        "details": {
            **results_info,
            "recent_dividend": has_recent_dividend,
            "recent_split_bonus": has_recent_action,
            **momentum_events,
        },
        "metric_scores": metric_scores,
    }
