"""
Tax Optimizer - Tax-efficient portfolio management

Provides tax optimization strategies including:
- Tax Loss Harvesting
- Wash Sale Detection (30-day rule)
- Long-term vs Short-term Capital Gains
- Tax Benefit Calculations
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging

from app.utils.data_loader import load_stock_prices

logger = logging.getLogger(__name__)


async def tax_optimizer(
    positions: Dict[str, Dict[str, Any]],
    transactions: List[Dict[str, Any]],
    tax_bracket: float = 0.24,
    ltcg_rate: float = 0.15,
    stcg_rate: Optional[float] = None,
    current_date: Optional[str] = None,
    harvest_threshold: float = 0.03
) -> Dict[str, Any]:
    """
    Optimize portfolio for tax efficiency.

    Args:
        positions: Current holdings with cost basis
            {
                "AAPL": {
                    "shares": 100,
                    "cost_basis": 150,
                    "purchase_date": "2023-06-15",
                    "current_price": 185
                },
                ...
            }
        transactions: Historical transactions
            [
                {
                    "date": "2024-01-15",
                    "ticker": "AAPL",
                    "shares": 50,
                    "price": 160,
                    "action": "buy"
                },
                ...
            ]
        tax_bracket: Ordinary income tax rate (default: 24%)
        ltcg_rate: Long-term capital gains rate (default: 15%)
        stcg_rate: Short-term capital gains rate (default: same as tax_bracket)
        current_date: Current date for calculations (default: today)
        harvest_threshold: Minimum loss % to harvest (default: 3%)

    Returns:
        {
            "tax_loss_harvest_opportunities": [
                {
                    "ticker": "TSLA",
                    "shares": 50,
                    "cost_basis": 250,
                    "current_price": 200,
                    "unrealized_loss": -2500,
                    "tax_benefit": 600,
                    "holding_period": "short",
                    "purchase_date": "2024-03-01"
                },
                ...
            ],
            "wash_sale_warnings": [
                {
                    "ticker": "AAPL",
                    "sale_date": "2024-01-15",
                    "repurchase_date": "2024-01-20",
                    "days_apart": 5,
                    "disallowed_loss": 500
                },
                ...
            ],
            "long_term_gains": 5000,
            "short_term_gains": -2000,
            "total_unrealized_gains": 8500,
            "total_unrealized_losses": -3000,
            "potential_tax_savings": 1200,
            "recommendations": [...],
            "interpretation": "..."
        }

    Example:
        >>> result = await tax_optimizer(
        ...     positions={"AAPL": {"shares": 100, "cost_basis": 150, "purchase_date": "2023-01-01"}},
        ...     transactions=[...],
        ...     tax_bracket=0.24
        ... )
    """
    try:
        logger.info(f"Tax optimization for {len(positions)} positions")

        # Set current date
        if not current_date:
            current_date = datetime.now().strftime("%Y-%m-%d")

        current_dt = pd.to_datetime(current_date)

        # Use provided STCG rate or default to tax bracket
        if stcg_rate is None:
            stcg_rate = tax_bracket

        # Load current prices if not provided
        tickers = list(positions.keys())
        prices = load_stock_prices(tickers,
                                   start_date=(current_dt - timedelta(days=5)).strftime("%Y-%m-%d"),
                                   end_date=current_date)

        # Update current prices
        for ticker in positions.keys():
            if ticker in prices.columns and "current_price" not in positions[ticker]:
                ticker_prices = prices[ticker].dropna()
                if len(ticker_prices) > 0:
                    positions[ticker]["current_price"] = float(ticker_prices.iloc[-1])

        # Analyze tax loss harvesting opportunities
        tlh_opportunities = _find_tax_loss_harvest_opportunities(
            positions, current_dt, stcg_rate, ltcg_rate, harvest_threshold
        )

        # Detect wash sales
        wash_sales = _detect_wash_sales(
            transactions, current_dt
        )

        # Calculate unrealized gains/losses
        gains_losses = _calculate_gains_losses(
            positions, current_dt, ltcg_rate, stcg_rate
        )

        # Generate recommendations
        recommendations = _generate_recommendations(
            tlh_opportunities, wash_sales, gains_losses, tax_bracket
        )

        # Interpretation
        interpretation = _generate_interpretation(
            tlh_opportunities, wash_sales, gains_losses, recommendations
        )

        return {
            "tax_loss_harvest_opportunities": tlh_opportunities,
            "wash_sale_warnings": wash_sales,
            "long_term_gains": round(gains_losses["lt_gains"], 2),
            "short_term_gains": round(gains_losses["st_gains"], 2),
            "total_unrealized_gains": round(gains_losses["total_gains"], 2),
            "total_unrealized_losses": round(gains_losses["total_losses"], 2),
            "potential_tax_savings": round(gains_losses["potential_savings"], 2),
            "recommendations": recommendations,
            "metadata": {
                "num_positions": len(positions),
                "tax_bracket": tax_bracket,
                "ltcg_rate": ltcg_rate,
                "stcg_rate": stcg_rate,
                "current_date": current_date
            },
            "interpretation": interpretation
        }

    except Exception as e:
        logger.error(f"Tax optimization failed: {str(e)}")
        return {
            "error": str(e),
            "positions": list(positions.keys())
        }


def _find_tax_loss_harvest_opportunities(
    positions: Dict[str, Dict],
    current_date: datetime,
    stcg_rate: float,
    ltcg_rate: float,
    harvest_threshold: float
) -> List[Dict[str, Any]]:
    """
    Find positions with unrealized losses suitable for harvesting.
    """
    opportunities = []

    for ticker, pos in positions.items():
        shares = pos.get("shares", 0)
        cost_basis = pos.get("cost_basis", 0)
        current_price = pos.get("current_price", 0)
        purchase_date = pos.get("purchase_date")

        if not purchase_date or shares <= 0:
            continue

        purchase_dt = pd.to_datetime(purchase_date)

        # Calculate gain/loss
        total_cost = shares * cost_basis
        current_value = shares * current_price
        unrealized_gl = current_value - total_cost

        # Only harvest losses
        if unrealized_gl >= 0:
            continue

        # Check if loss exceeds threshold
        loss_pct = unrealized_gl / total_cost
        if abs(loss_pct) < harvest_threshold:
            continue

        # Determine holding period
        holding_days = (current_date - purchase_dt).days
        holding_period = "long" if holding_days >= 365 else "short"

        # Tax benefit calculation
        tax_rate = ltcg_rate if holding_period == "long" else stcg_rate
        tax_benefit = abs(unrealized_gl) * tax_rate

        opportunities.append({
            "ticker": ticker,
            "shares": shares,
            "cost_basis": cost_basis,
            "current_price": current_price,
            "unrealized_loss": round(unrealized_gl, 2),
            "loss_percentage": round(loss_pct, 4),
            "tax_benefit": round(tax_benefit, 2),
            "holding_period": holding_period,
            "holding_days": holding_days,
            "purchase_date": purchase_date
        })

    # Sort by tax benefit (highest first)
    opportunities.sort(key=lambda x: x["tax_benefit"], reverse=True)

    return opportunities


def _detect_wash_sales(
    transactions: List[Dict],
    current_date: datetime
) -> List[Dict[str, Any]]:
    """
    Detect wash sale violations (30-day rule).

    A wash sale occurs when you sell a security at a loss and repurchase
    the same or substantially identical security within 30 days before or after.
    """
    if not transactions:
        return []

    wash_sales = []

    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(transactions)

    if df.empty or "date" not in df.columns:
        return []

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Group by ticker
    for ticker in df["ticker"].unique():
        ticker_txns = df[df["ticker"] == ticker].copy()

        # Find sells with losses
        for idx, sell_txn in ticker_txns.iterrows():
            if sell_txn.get("action") != "sell":
                continue

            # Check if it's a loss (requires cost basis tracking)
            # For simplicity, we'll check for repurchases within 30 days

            sell_date = sell_txn["date"]

            # Look for purchases within 30 days before or after
            window_start = sell_date - timedelta(days=30)
            window_end = sell_date + timedelta(days=30)

            repurchases = ticker_txns[
                (ticker_txns["action"] == "buy") &
                (ticker_txns["date"] >= window_start) &
                (ticker_txns["date"] <= window_end) &
                (ticker_txns["date"] != sell_date)
            ]

            for _, buy_txn in repurchases.iterrows():
                days_apart = abs((buy_txn["date"] - sell_date).days)

                # Estimate disallowed loss (would need actual cost basis)
                shares_sold = sell_txn.get("shares", 0)
                shares_bought = buy_txn.get("shares", 0)

                wash_shares = min(shares_sold, shares_bought)

                # This is a simplified calculation
                # Real wash sale requires tracking specific tax lots
                wash_sales.append({
                    "ticker": ticker,
                    "sale_date": sell_date.strftime("%Y-%m-%d"),
                    "repurchase_date": buy_txn["date"].strftime("%Y-%m-%d"),
                    "days_apart": days_apart,
                    "shares_affected": wash_shares,
                    "warning": "Potential wash sale - loss may be disallowed"
                })

    return wash_sales


def _calculate_gains_losses(
    positions: Dict[str, Dict],
    current_date: datetime,
    ltcg_rate: float,
    stcg_rate: float
) -> Dict[str, float]:
    """
    Calculate total unrealized gains/losses and potential tax.
    """
    lt_gains = 0  # Long-term gains
    st_gains = 0  # Short-term gains
    total_gains = 0
    total_losses = 0

    for ticker, pos in positions.items():
        shares = pos.get("shares", 0)
        cost_basis = pos.get("cost_basis", 0)
        current_price = pos.get("current_price", 0)
        purchase_date = pos.get("purchase_date")

        if not purchase_date or shares <= 0:
            continue

        purchase_dt = pd.to_datetime(purchase_date)

        # Calculate gain/loss
        total_cost = shares * cost_basis
        current_value = shares * current_price
        unrealized_gl = current_value - total_cost

        # Determine holding period
        holding_days = (current_date - purchase_dt).days
        is_long_term = holding_days >= 365

        if is_long_term:
            lt_gains += unrealized_gl
        else:
            st_gains += unrealized_gl

        if unrealized_gl > 0:
            total_gains += unrealized_gl
        else:
            total_losses += unrealized_gl

    # Potential tax on gains (or savings from losses)
    lt_tax = max(0, lt_gains) * ltcg_rate
    st_tax = max(0, st_gains) * stcg_rate
    total_tax = lt_tax + st_tax

    # Potential savings from harvesting losses
    loss_savings_lt = abs(min(0, lt_gains)) * ltcg_rate
    loss_savings_st = abs(min(0, st_gains)) * stcg_rate
    potential_savings = loss_savings_lt + loss_savings_st

    return {
        "lt_gains": lt_gains,
        "st_gains": st_gains,
        "total_gains": total_gains,
        "total_losses": total_losses,
        "lt_tax": lt_tax,
        "st_tax": st_tax,
        "total_tax": total_tax,
        "potential_savings": potential_savings
    }


def _generate_recommendations(
    tlh_opportunities: List[Dict],
    wash_sales: List[Dict],
    gains_losses: Dict,
    tax_bracket: float
) -> List[str]:
    """
    Generate actionable tax optimization recommendations.
    """
    recommendations = []

    # Tax loss harvesting
    if tlh_opportunities:
        top_opportunity = tlh_opportunities[0]
        total_benefit = sum(opp["tax_benefit"] for opp in tlh_opportunities)

        recommendations.append(
            f"Consider harvesting {len(tlh_opportunities)} positions with losses "
            f"for potential tax benefit of ${total_benefit:.2f}. "
            f"Top opportunity: {top_opportunity['ticker']} "
            f"(${top_opportunity['tax_benefit']:.2f} benefit)."
        )

    # Wash sale warnings
    if wash_sales:
        recommendations.append(
            f"Warning: {len(wash_sales)} potential wash sale violations detected. "
            f"Losses may be disallowed. Review repurchase timing."
        )

    # Long-term vs short-term
    lt_gains = gains_losses["lt_gains"]
    st_gains = gains_losses["st_gains"]

    if st_gains > 0 and st_gains > lt_gains:
        recommendations.append(
            f"Large short-term capital gains (${st_gains:.2f}). "
            f"Consider holding positions for long-term treatment to reduce tax rate "
            f"from {tax_bracket:.0%} to 15%."
        )

    # Offsetting gains with losses
    total_gains = gains_losses["total_gains"]
    total_losses = gains_losses["total_losses"]

    if total_gains > 0 and total_losses < 0:
        offset_amount = min(total_gains, abs(total_losses))
        recommendations.append(
            f"Realized gains can be offset by ${offset_amount:.2f} "
            f"in harvested losses to reduce tax liability."
        )

    # Year-end planning
    recommendations.append(
        "Consider year-end tax planning: harvest losses before Dec 31, "
        "but avoid wash sale violations in January."
    )

    return recommendations


def _generate_interpretation(
    tlh_opportunities: List[Dict],
    wash_sales: List[Dict],
    gains_losses: Dict,
    recommendations: List[str]
) -> str:
    """
    Generate human-readable interpretation.
    """
    total_unrealized = gains_losses["total_gains"] + gains_losses["total_losses"]

    interpretation = (
        f"Portfolio has ${total_unrealized:.2f} in unrealized gains/losses. "
    )

    if tlh_opportunities:
        total_benefit = sum(opp["tax_benefit"] for opp in tlh_opportunities)
        interpretation += (
            f"Tax loss harvesting could save ${total_benefit:.2f} in taxes "
            f"by realizing {len(tlh_opportunities)} losing positions. "
        )
    else:
        interpretation += "No tax loss harvesting opportunities identified. "

    if wash_sales:
        interpretation += (
            f"Warning: {len(wash_sales)} potential wash sale violations may disallow losses. "
        )

    lt_gains = gains_losses["lt_gains"]
    st_gains = gains_losses["st_gains"]

    if lt_gains > st_gains:
        interpretation += (
            f"Portfolio is tax-efficient with ${lt_gains:.2f} in long-term gains "
            f"vs ${st_gains:.2f} in short-term gains. "
        )
    elif st_gains > 0:
        interpretation += (
            f"Portfolio has ${st_gains:.2f} in short-term gains subject to higher tax rates. "
        )

    return interpretation


# Example usage
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test():
        # Test: Tax optimization
        positions = {
            "AAPL": {
                "shares": 100,
                "cost_basis": 150,
                "current_price": 185,
                "purchase_date": "2023-01-15"
            },
            "TSLA": {
                "shares": 50,
                "cost_basis": 250,
                "current_price": 200,
                "purchase_date": "2024-03-01"
            },
            "MSFT": {
                "shares": 75,
                "cost_basis": 300,
                "current_price": 420,
                "purchase_date": "2022-06-01"
            }
        }

        transactions = [
            {"date": "2024-01-15", "ticker": "AAPL", "shares": 50, "price": 160, "action": "sell"},
            {"date": "2024-01-20", "ticker": "AAPL", "shares": 50, "price": 155, "action": "buy"},
            {"date": "2024-03-01", "ticker": "TSLA", "shares": 50, "price": 250, "action": "buy"}
        ]

        result = await tax_optimizer(
            positions=positions,
            transactions=transactions,
            tax_bracket=0.24,
            ltcg_rate=0.15
        )

        print("\n=== Tax Optimization Analysis ===")
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"\nTax Loss Harvest Opportunities:")
            for opp in result['tax_loss_harvest_opportunities']:
                print(f"  {opp['ticker']}: Loss ${opp['unrealized_loss']:.2f}, "
                      f"Tax Benefit ${opp['tax_benefit']:.2f}, "
                      f"Holding: {opp['holding_period']}-term")

            print(f"\nWash Sale Warnings:")
            for ws in result['wash_sale_warnings']:
                print(f"  {ws['ticker']}: Sold {ws['sale_date']}, "
                      f"Repurchased {ws['repurchase_date']} ({ws['days_apart']} days apart)")

            print(f"\nGains/Losses Summary:")
            print(f"  Long-term gains: ${result['long_term_gains']:.2f}")
            print(f"  Short-term gains: ${result['short_term_gains']:.2f}")
            print(f"  Total unrealized gains: ${result['total_unrealized_gains']:.2f}")
            print(f"  Total unrealized losses: ${result['total_unrealized_losses']:.2f}")
            print(f"  Potential tax savings: ${result['potential_tax_savings']:.2f}")

            print(f"\nRecommendations:")
            for i, rec in enumerate(result['recommendations'], 1):
                print(f"  {i}. {rec}")

            print(f"\nInterpretation:\n{result['interpretation']}")

    asyncio.run(test())
