"""
Composite Scorer — Combines fundamental, technical, and event scores
into a single growth potential ranking.
"""

from config import (
    FUNDAMENTAL_WEIGHT,
    TECHNICAL_WEIGHT,
    EVENT_WEIGHT,
    TIER_STRONG_BUY,
    TIER_BUY,
    TIER_WATCH,
)


def compute_composite_score(
    fundamental_score: float,
    technical_score: float,
    event_score: float,
) -> dict:
    """
    Compute the weighted composite score and assign a tier.

    Args:
        fundamental_score: Score from fundamental analyzer (0-100)
        technical_score: Score from technical analyzer (0-100)
        event_score: Score from event analyzer (0-100)

    Returns:
        Dict with composite score, tier, and breakdown.
    """
    composite = (
        fundamental_score * FUNDAMENTAL_WEIGHT
        + technical_score * TECHNICAL_WEIGHT
        + event_score * EVENT_WEIGHT
    )
    composite = round(composite, 1)

    # Assign tier
    if composite >= TIER_STRONG_BUY:
        tier = "strong_buy"
    elif composite >= TIER_BUY:
        tier = "buy"
    elif composite >= TIER_WATCH:
        tier = "watch"
    else:
        tier = "avoid"

    return {
        "composite": composite,
        "tier": tier,
        "breakdown": {
            "fundamental": round(fundamental_score, 1),
            "technical": round(technical_score, 1),
            "event": round(event_score, 1),
        },
        "weights": {
            "fundamental": FUNDAMENTAL_WEIGHT,
            "technical": TECHNICAL_WEIGHT,
            "event": EVENT_WEIGHT,
        },
    }


def generate_summary(stocks_results: list[dict]) -> dict:
    """
    Generate summary statistics from all scanned stocks.
    """
    if not stocks_results:
        return {
            "strong_buy": 0,
            "buy": 0,
            "watch": 0,
            "avoid": 0,
            "avg_score": 0,
            "top_sectors": [],
            "total": 0,
        }

    tier_counts = {"strong_buy": 0, "buy": 0, "watch": 0, "avoid": 0}
    sector_scores = {}
    total_score = 0

    for stock in stocks_results:
        tier = stock.get("tier", "avoid")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

        score = stock.get("scores", {}).get("composite", 0)
        total_score += score

        sector = stock.get("sector", "Other")
        if sector not in sector_scores:
            sector_scores[sector] = []
        sector_scores[sector].append(score)

    avg_score = round(total_score / len(stocks_results), 1) if stocks_results else 0

    # Top sectors by average score
    sector_avg = {
        sector: round(sum(scores) / len(scores), 1)
        for sector, scores in sector_scores.items()
        if len(scores) >= 2  # At least 2 stocks to count
    }
    top_sectors = sorted(sector_avg.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        **tier_counts,
        "avg_score": avg_score,
        "top_sectors": [
            {"sector": s, "avg_score": sc, "count": len(sector_scores[s])}
            for s, sc in top_sectors
        ],
        "total": len(stocks_results),
    }
