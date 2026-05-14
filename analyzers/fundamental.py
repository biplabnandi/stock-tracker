"""
Fundamental Analyzer — Evaluates stocks on financial health and growth metrics.

Scores each metric 0-100 and returns a composite fundamental score.
"""

import logging
import pandas as pd
from config import (
    IDEAL_PE_MAX,
    IDEAL_PB_MAX,
    IDEAL_ROE_MIN,
    IDEAL_REVENUE_GROWTH,
    IDEAL_PROFIT_GROWTH,
    IDEAL_DEBT_EQUITY_MAX,
    IDEAL_CURRENT_RATIO_MIN,
    IDEAL_PROMOTER_HOLDING,
)

logger = logging.getLogger(__name__)


def _score_pe(pe: float | None) -> int:
    """Lower PE is better (but not negative). Score 0-100."""
    if pe is None or pe <= 0:
        return 30  # Neutral for missing/negative
    if pe <= 15:
        return 95
    if pe <= 25:
        return 80
    if pe <= IDEAL_PE_MAX:
        return 60
    if pe <= 60:
        return 40
    return 20  # Very expensive


def _score_pb(pb: float | None) -> int:
    """Lower PB is better. Score 0-100."""
    if pb is None or pb <= 0:
        return 30
    if pb <= 1.5:
        return 95
    if pb <= 3:
        return 80
    if pb <= IDEAL_PB_MAX:
        return 60
    if pb <= 8:
        return 40
    return 20


def _score_roe(roe: float | None) -> int:
    """Higher ROE is better. Score 0-100."""
    if roe is None:
        return 30
    if roe >= 25:
        return 95
    if roe >= 18:
        return 80
    if roe >= IDEAL_ROE_MIN:
        return 65
    if roe >= 5:
        return 40
    return 20


def _score_growth(growth: float | None, target: float) -> int:
    """Higher growth is better. Score 0-100."""
    if growth is None:
        return 30
    if growth >= target * 2.5:
        return 95
    if growth >= target * 1.5:
        return 80
    if growth >= target:
        return 65
    if growth >= 0:
        return 45
    if growth >= -10:
        return 25
    return 10  # Declining


def _score_debt_equity(de: float | None) -> int:
    """Lower D/E is better. Score 0-100."""
    if de is None:
        return 30
    if de <= 0.1:
        return 95
    if de <= 0.5:
        return 85
    if de <= IDEAL_DEBT_EQUITY_MAX:
        return 70
    if de <= 2.0:
        return 45
    return 20


def _score_promoter_holding(holding: float | None) -> int:
    """Higher promoter holding is better. Score 0-100."""
    if holding is None:
        return 40  # Slightly better neutral, data often missing
    if holding >= 70:
        return 95
    if holding >= IDEAL_PROMOTER_HOLDING:
        return 80
    if holding >= 35:
        return 60
    if holding >= 20:
        return 40
    return 25


def _score_current_ratio(cr: float | None) -> int:
    """Higher current ratio is better (liquidity). Score 0-100."""
    if cr is None:
        return 40
    if cr >= 2.5:
        return 90
    if cr >= IDEAL_CURRENT_RATIO_MIN:
        return 75
    if cr >= 1.0:
        return 55
    return 30


def _safe_get_growth(financials: pd.DataFrame, row_name: str) -> float | None:
    """
    Calculate QoQ growth from quarterly financials.
    Tries multiple row name variants since yfinance data isn't consistent.
    """
    possible_names = [
        row_name,
        row_name.replace(" ", ""),
        row_name.title(),
    ]

    for name in possible_names:
        if name in financials.index and len(financials.columns) >= 2:
            try:
                current = financials.loc[name].iloc[0]
                previous = financials.loc[name].iloc[1]
                if previous and previous != 0:
                    return round(((current - previous) / abs(previous)) * 100, 2)
            except Exception:
                continue

    return None


def analyze_fundamentals(stock_data: dict) -> dict:
    """
    Analyze fundamental metrics for a stock.

    Args:
        stock_data: Dict from fetcher containing info, quarterly_financials, etc.

    Returns:
        Dict with individual metric scores, values, and composite score.
    """
    info = stock_data.get("info", {})
    financials = stock_data.get("quarterly_financials", pd.DataFrame())
    balance_sheet = stock_data.get("quarterly_balance_sheet", pd.DataFrame())

    # ── Extract raw values ──────────────────────────────────────────
    pe = info.get("trailingPE") or info.get("forwardPE")
    pb = info.get("priceToBook")
    roe = info.get("returnOnEquity")
    if roe is not None:
        roe = roe * 100  # Convert from decimal to percentage

    de = info.get("debtToEquity")
    if de is not None:
        de = de / 100  # yfinance sometimes returns as percentage

    current_ratio = info.get("currentRatio")
    promoter_holding = info.get("heldPercentInsiders")
    if promoter_holding is not None:
        promoter_holding = promoter_holding * 100

    # Calculate growth from quarterly financials
    revenue_growth = _safe_get_growth(financials, "Total Revenue")
    profit_growth = _safe_get_growth(financials, "Net Income")

    # ── Score each metric ──────────────────────────────────────────
    scores = {
        "pe_score": _score_pe(pe),
        "pb_score": _score_pb(pb),
        "roe_score": _score_roe(roe),
        "revenue_growth_score": _score_growth(revenue_growth, IDEAL_REVENUE_GROWTH),
        "profit_growth_score": _score_growth(profit_growth, IDEAL_PROFIT_GROWTH),
        "debt_equity_score": _score_debt_equity(de),
        "promoter_holding_score": _score_promoter_holding(promoter_holding),
        "current_ratio_score": _score_current_ratio(current_ratio),
    }

    # ── Composite (weighted average) ───────────────────────────────
    weights = {
        "pe_score": 0.12,
        "pb_score": 0.08,
        "roe_score": 0.18,
        "revenue_growth_score": 0.18,
        "profit_growth_score": 0.18,
        "debt_equity_score": 0.12,
        "promoter_holding_score": 0.07,
        "current_ratio_score": 0.07,
    }

    composite = sum(scores[k] * weights[k] for k in weights)
    composite = round(composite, 1)

    return {
        "score": composite,
        "values": {
            "pe_ratio": round(pe, 2) if pe else None,
            "pb_ratio": round(pb, 2) if pb else None,
            "roe": round(roe, 2) if roe else None,
            "revenue_growth": revenue_growth,
            "profit_growth": profit_growth,
            "debt_to_equity": round(de, 2) if de else None,
            "promoter_holding": round(promoter_holding, 2) if promoter_holding else None,
            "current_ratio": round(current_ratio, 2) if current_ratio else None,
        },
        "metric_scores": scores,
    }
