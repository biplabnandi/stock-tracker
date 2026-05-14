"""
Technical Analyzer — Evaluates stocks on price action and technical indicators.

Uses pandas_ta_classic for indicator calculations. Scores each 0-100 and returns composite.
"""

import logging
import pandas as pd
import pandas_ta_classic as ta
from config import (
    RSI_PERIOD,
    RSI_SWEET_SPOT,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    SMA_SHORT,
    SMA_LONG,
    EMA_PERIOD,
    BOLLINGER_PERIOD,
    BOLLINGER_STD,
    ADX_PERIOD,
    ADX_STRONG_TREND,
)

logger = logging.getLogger(__name__)


def _score_rsi(rsi: float | None) -> int:
    """
    Score RSI for mid-term growth potential.
    Sweet spot: 40-65 (momentum without being overbought).
    """
    if rsi is None:
        return 40
    if RSI_SWEET_SPOT[0] <= rsi <= RSI_SWEET_SPOT[1]:
        return 85  # Ideal range
    if RSI_OVERSOLD <= rsi < RSI_SWEET_SPOT[0]:
        return 70  # Potentially setting up
    if RSI_SWEET_SPOT[1] < rsi <= RSI_OVERBOUGHT:
        return 55  # Strong but be cautious
    if rsi < RSI_OVERSOLD:
        return 50  # Oversold, could bounce but risky
    return 25  # Overbought


def _score_macd(macd_val: float | None, signal_val: float | None, hist: float | None) -> tuple[int, str]:
    """Score MACD for trend strength and direction."""
    if macd_val is None or signal_val is None:
        return 40, "neutral"

    if hist is not None and hist > 0 and macd_val > signal_val:
        if macd_val > 0:
            return 90, "strong_bullish"
        return 75, "bullish_crossover"
    elif hist is not None and hist > 0:
        return 60, "weakening_bullish"
    elif hist is not None and hist < 0 and macd_val < signal_val:
        if macd_val < 0:
            return 20, "strong_bearish"
        return 35, "bearish_crossover"
    return 45, "neutral"


def _score_moving_averages(price: float, sma50: float | None, sma200: float | None, ema20: float | None) -> tuple[int, dict]:
    """Score based on moving average alignment."""
    score = 50
    signals = {
        "price_vs_ema20": "neutral",
        "sma50_above_sma200": None,
        "golden_cross": False,
    }

    if ema20 is not None:
        if price > ema20:
            score += 10
            signals["price_vs_ema20"] = "above"
        else:
            score -= 10
            signals["price_vs_ema20"] = "below"

    if sma50 is not None and sma200 is not None:
        if sma50 > sma200:
            score += 20
            signals["sma50_above_sma200"] = True
            # Check for recent golden cross (SMA50 just crossed above SMA200)
            if abs(sma50 - sma200) / sma200 < 0.02:
                score += 10
                signals["golden_cross"] = True
        else:
            score -= 15
            signals["sma50_above_sma200"] = False

    if sma50 is not None and price > sma50:
        score += 5
    elif sma50 is not None:
        score -= 5

    return max(0, min(100, score)), signals


def _score_bollinger(price: float, upper: float | None, lower: float | None, mid: float | None) -> tuple[int, str]:
    """Score based on Bollinger Band position."""
    if upper is None or lower is None or mid is None:
        return 40, "unknown"

    band_width = upper - lower
    if band_width == 0:
        return 40, "unknown"

    position = (price - lower) / band_width

    if position <= 0.2:
        return 75, "near_lower"  # Potential bounce
    if position <= 0.5:
        return 65, "lower_half"
    if position <= 0.8:
        return 55, "upper_half"
    return 30, "near_upper"  # Potentially overbought


def _score_adx(adx: float | None) -> tuple[int, str]:
    """Score ADX for trend strength."""
    if adx is None:
        return 40, "unknown"
    if adx >= 40:
        return 85, "very_strong_trend"
    if adx >= ADX_STRONG_TREND:
        return 75, "strong_trend"
    if adx >= 20:
        return 55, "moderate_trend"
    return 35, "weak_trend"


def _score_volume_trend(history: pd.DataFrame) -> tuple[int, str]:
    """Score volume trend (increasing volume on up-days is bullish)."""
    try:
        if len(history) < 21:
            return 40, "insufficient_data"

        recent = history.tail(21)
        avg_vol_recent = recent["Volume"].mean()
        avg_vol_prior = history.iloc[-63:-21]["Volume"].mean() if len(history) >= 63 else history["Volume"].mean()

        # Volume trend
        vol_ratio = avg_vol_recent / avg_vol_prior if avg_vol_prior > 0 else 1

        # Up-day volume vs down-day volume
        up_days = recent[recent["Close"] >= recent["Open"]]
        down_days = recent[recent["Close"] < recent["Open"]]

        avg_up_vol = up_days["Volume"].mean() if len(up_days) > 0 else 0
        avg_down_vol = down_days["Volume"].mean() if len(down_days) > 0 else 1

        vol_bias = avg_up_vol / avg_down_vol if avg_down_vol > 0 else 1

        if vol_ratio > 1.2 and vol_bias > 1.2:
            return 85, "strong_accumulation"
        if vol_ratio > 1.0 and vol_bias > 1.0:
            return 70, "accumulation"
        if vol_bias > 1.0:
            return 55, "mild_accumulation"
        if vol_bias < 0.8:
            return 30, "distribution"
        return 45, "neutral"

    except Exception:
        return 40, "error"


def _score_52w_position(price: float, high_52w: float | None, low_52w: float | None) -> tuple[int, float | None]:
    """
    Score based on position within 52-week range.
    Best: 40-70% from low (momentum without being at top).
    """
    if high_52w is None or low_52w is None or high_52w == low_52w:
        return 40, None

    range_pct = ((price - low_52w) / (high_52w - low_52w)) * 100
    pct_from_high = ((high_52w - price) / high_52w) * 100

    if 30 <= range_pct <= 65:
        score = 80  # Sweet spot
    elif 65 < range_pct <= 85:
        score = 60  # Good momentum but getting high
    elif 20 <= range_pct < 30:
        score = 55  # Could be bottoming
    elif range_pct > 85:
        score = 35  # Near top
    else:
        score = 30  # Near 52w low

    return score, round(pct_from_high, 2)


def analyze_technicals(stock_data: dict) -> dict:
    """
    Analyze technical indicators for a stock.

    Args:
        stock_data: Dict from fetcher containing history DataFrame.

    Returns:
        Dict with individual indicator scores, values, and composite score.
    """
    history = stock_data.get("history", pd.DataFrame())
    info = stock_data.get("info", {})

    if history.empty or len(history) < 50:
        return {
            "score": 30,
            "values": {},
            "signals": {},
            "metric_scores": {},
        }

    # ── Calculate indicators using pandas_ta_classic ──────────────
    close = history["Close"]
    current_price = float(close.iloc[-1])

    # RSI
    rsi_series = ta.rsi(close, length=RSI_PERIOD)
    rsi_val = float(rsi_series.iloc[-1]) if rsi_series is not None and not rsi_series.empty else None

    # MACD
    macd_df = ta.macd(close, fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
    macd_val = signal_val = hist_val = None
    if macd_df is not None and not macd_df.empty:
        cols = macd_df.columns.tolist()
        macd_val = float(macd_df[cols[0]].iloc[-1]) if len(cols) > 0 else None
        hist_val = float(macd_df[cols[1]].iloc[-1]) if len(cols) > 1 else None
        signal_val = float(macd_df[cols[2]].iloc[-1]) if len(cols) > 2 else None

    # Moving Averages
    sma50 = ta.sma(close, length=SMA_SHORT)
    sma200 = ta.sma(close, length=SMA_LONG)
    ema20 = ta.ema(close, length=EMA_PERIOD)

    sma50_val = float(sma50.iloc[-1]) if sma50 is not None and not sma50.empty else None
    sma200_val = float(sma200.iloc[-1]) if sma200 is not None and not sma200.empty else None
    ema20_val = float(ema20.iloc[-1]) if ema20 is not None and not ema20.empty else None

    # Bollinger Bands
    bb = ta.bbands(close, length=BOLLINGER_PERIOD, std=BOLLINGER_STD)
    bb_upper = bb_lower = bb_mid = None
    if bb is not None and not bb.empty:
        cols = bb.columns.tolist()
        bb_lower = float(bb[cols[0]].iloc[-1]) if len(cols) > 0 else None
        bb_mid = float(bb[cols[1]].iloc[-1]) if len(cols) > 1 else None
        bb_upper = float(bb[cols[2]].iloc[-1]) if len(cols) > 2 else None

    # ADX
    adx_df = ta.adx(history["High"], history["Low"], close, length=ADX_PERIOD)
    adx_val = None
    if adx_df is not None and not adx_df.empty:
        adx_col = [c for c in adx_df.columns if "ADX" in c and "DM" not in c]
        if adx_col:
            adx_val = float(adx_df[adx_col[0]].iloc[-1])

    # 52-week range
    high_52w = info.get("fiftyTwoWeekHigh")
    low_52w = info.get("fiftyTwoWeekLow")

    # ── Score each indicator ───────────────────────────────────────
    rsi_score = _score_rsi(rsi_val)
    macd_score, macd_signal_label = _score_macd(macd_val, signal_val, hist_val)
    ma_score, ma_signals = _score_moving_averages(current_price, sma50_val, sma200_val, ema20_val)
    bb_score, bb_position = _score_bollinger(current_price, bb_upper, bb_lower, bb_mid)
    adx_score, adx_label = _score_adx(adx_val)
    vol_score, vol_label = _score_volume_trend(history)
    w52_score, pct_from_high = _score_52w_position(current_price, high_52w, low_52w)

    metric_scores = {
        "rsi_score": rsi_score,
        "macd_score": macd_score,
        "ma_score": ma_score,
        "bollinger_score": bb_score,
        "adx_score": adx_score,
        "volume_score": vol_score,
        "w52_score": w52_score,
    }

    # ── Composite (weighted average) ───────────────────────────────
    weights = {
        "rsi_score": 0.15,
        "macd_score": 0.20,
        "ma_score": 0.20,
        "bollinger_score": 0.10,
        "adx_score": 0.10,
        "volume_score": 0.15,
        "w52_score": 0.10,
    }

    composite = sum(metric_scores[k] * weights[k] for k in weights)
    composite = round(composite, 1)

    return {
        "score": composite,
        "values": {
            "rsi": round(rsi_val, 2) if rsi_val else None,
            "macd": round(macd_val, 4) if macd_val else None,
            "macd_signal": macd_signal_label,
            "sma50": round(sma50_val, 2) if sma50_val else None,
            "sma200": round(sma200_val, 2) if sma200_val else None,
            "ema20": round(ema20_val, 2) if ema20_val else None,
            "adx": round(adx_val, 2) if adx_val else None,
            "bollinger_position": bb_position,
            "volume_trend": vol_label,
            "pct_from_52w_high": pct_from_high,
            **ma_signals,
        },
        "metric_scores": metric_scores,
    }
