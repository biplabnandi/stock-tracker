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
    IDEAL_PEG_MAX,
    IDEAL_PS_MAX,
    IDEAL_OPERATING_MARGIN,
    IDEAL_ROA_MIN,
    IDEAL_INTEREST_COVERAGE,
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


# ─── New Metric Scorers ───────────────────────────────────────────


def _score_eps(eps: float | None) -> int:
    """Higher trailing EPS is better. Score 0-100."""
    if eps is None:
        return 30
    if eps <= 0:
        return 15  # Negative earnings
    if eps >= 100:
        return 95
    if eps >= 50:
        return 85
    if eps >= 20:
        return 75
    if eps >= 10:
        return 65
    if eps >= 5:
        return 55
    return 40


def _score_peg(peg: float | None) -> int:
    """PEG near 1 is ideal. Below 1 = undervalued, above 2 = overpriced. Score 0-100."""
    if peg is None or peg <= 0:
        return 30  # Negative/missing PEG is unreliable
    if peg <= 0.5:
        return 95  # Deeply undervalued
    if peg <= 1.0:
        return 90  # Classic undervalued
    if peg <= 1.5:
        return 70
    if peg <= IDEAL_PEG_MAX:
        return 55
    if peg <= 3.0:
        return 35
    return 15  # Overpriced for growth


def _score_ps(ps: float | None) -> int:
    """Lower P/S is better. Score 0-100."""
    if ps is None or ps <= 0:
        return 30
    if ps <= 1.0:
        return 95
    if ps <= 3.0:
        return 80
    if ps <= 6.0:
        return 65
    if ps <= IDEAL_PS_MAX:
        return 50
    if ps <= 20:
        return 35
    return 15


def _score_operating_margin(margin: float | None) -> int:
    """Higher operating margin is better. Score 0-100."""
    if margin is None:
        return 30
    if margin >= 30:
        return 95  # Excellent pricing power
    if margin >= 20:
        return 85
    if margin >= IDEAL_OPERATING_MARGIN:
        return 70
    if margin >= 10:
        return 55
    if margin >= 5:
        return 40
    if margin >= 0:
        return 25
    return 10  # Negative margins


def _score_roa(roa: float | None) -> int:
    """Higher ROA is better. Score 0-100."""
    if roa is None:
        return 30
    if roa >= 20:
        return 95
    if roa >= 12:
        return 80
    if roa >= IDEAL_ROA_MIN:
        return 70
    if roa >= 5:
        return 55
    if roa >= 2:
        return 40
    return 20


def _score_fcf_yield(fcf_yield: float | None) -> int:
    """Higher FCF yield is better (FCF / Market Cap). Score 0-100."""
    if fcf_yield is None:
        return 30
    if fcf_yield >= 10:
        return 95  # Exceptional cash generation
    if fcf_yield >= 6:
        return 85
    if fcf_yield >= 4:
        return 70
    if fcf_yield >= 2:
        return 55
    if fcf_yield >= 0:
        return 35  # Positive but low
    return 15  # Negative FCF yield (burning cash)


def _score_interest_coverage(ic: float | None) -> int:
    """Higher interest coverage is better. Score 0-100."""
    if ic is None:
        return 40  # Often missing for low-debt companies
    if ic >= 10:
        return 95  # Very safe
    if ic >= 5:
        return 80
    if ic >= IDEAL_INTEREST_COVERAGE:
        return 65
    if ic >= 1.5:
        return 45
    if ic >= 1.0:
        return 25  # Barely covering interest
    return 10  # Cannot cover interest payments


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


def _safe_get_interest_coverage(
    financials: pd.DataFrame,
) -> float | None:
    """
    Calculate interest coverage ratio: Operating Income / Interest Expense.
    Returns None if data is unavailable.
    """
    oi_names = ["Operating Income", "OperatingIncome", "Ebit", "EBIT"]
    ie_names = ["Interest Expense", "InterestExpense"]

    operating_income = None
    interest_expense = None

    for name in oi_names:
        if name in financials.index and len(financials.columns) >= 1:
            try:
                operating_income = float(financials.loc[name].iloc[0])
                break
            except Exception:
                continue

    for name in ie_names:
        if name in financials.index and len(financials.columns) >= 1:
            try:
                val = float(financials.loc[name].iloc[0])
                # Interest expense is often reported as negative
                interest_expense = abs(val) if val != 0 else None
                break
            except Exception:
                continue

    if operating_income is not None and interest_expense is not None and interest_expense > 0:
        return round(operating_income / interest_expense, 2)

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

    # ── New metric raw values ──────────────────────────────────────
    eps = info.get("trailingEps")

    peg = info.get("pegRatio")

    ps = info.get("priceToSalesTrailing12Months")

    operating_margin = info.get("operatingMargins")
    if operating_margin is not None:
        operating_margin = operating_margin * 100  # Convert decimal to %

    roa = info.get("returnOnAssets")
    if roa is not None:
        roa = roa * 100  # Convert decimal to %

    # FCF Yield = Free Cash Flow / Market Cap * 100
    fcf = info.get("freeCashflow")
    market_cap = info.get("marketCap")
    fcf_yield = None
    if fcf is not None and market_cap is not None and market_cap > 0:
        fcf_yield = round((fcf / market_cap) * 100, 2)

    interest_coverage = _safe_get_interest_coverage(financials)

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
        "eps_score": _score_eps(eps),
        "peg_score": _score_peg(peg),
        "ps_score": _score_ps(ps),
        "operating_margin_score": _score_operating_margin(operating_margin),
        "roa_score": _score_roa(roa),
        "fcf_yield_score": _score_fcf_yield(fcf_yield),
        "interest_coverage_score": _score_interest_coverage(interest_coverage),
    }

    # ── Composite (weighted average) ───────────────────────────────
    # Rebalanced weights across 15 metrics (total = 1.00)
    weights = {
        "pe_score": 0.07,
        "pb_score": 0.04,
        "roe_score": 0.12,
        "revenue_growth_score": 0.10,
        "profit_growth_score": 0.10,
        "debt_equity_score": 0.08,
        "promoter_holding_score": 0.05,
        "current_ratio_score": 0.04,
        "eps_score": 0.08,
        "peg_score": 0.06,
        "ps_score": 0.04,
        "operating_margin_score": 0.08,
        "roa_score": 0.06,
        "fcf_yield_score": 0.05,
        "interest_coverage_score": 0.03,
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
            "eps": round(eps, 2) if eps else None,
            "peg_ratio": round(peg, 2) if peg else None,
            "ps_ratio": round(ps, 2) if ps else None,
            "operating_margin": round(operating_margin, 2) if operating_margin else None,
            "roa": round(roa, 2) if roa else None,
            "fcf_yield": fcf_yield,
            "interest_coverage": round(interest_coverage, 2) if interest_coverage else None,
        },
        "metric_scores": scores,
    }
