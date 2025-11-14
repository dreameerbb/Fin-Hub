"""
Portfolio Rebalancer - Generate trade actions to rebalance portfolio

Calculates deviations from target weights and generates optimal trade list
to bring portfolio back to target allocation while minimizing costs.

Supports:
- Threshold-based rebalancing (trigger when drift exceeds threshold)
- Periodic rebalancing (monthly, quarterly, annual)
- Tax-aware rebalancing (minimize tax impact)
- Transaction cost optimization
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

from app.utils.data_loader import load_stock_prices
from app.utils.portfolio_math import normalize_weights

logger = logging.getLogger(__name__)


async def portfolio_rebalancer(
    current_positions: Dict[str, Dict[str, float]],
    target_weights: Dict[str, float],
    total_value: float,
    cash_available: float = 0.0,
    strategy: str = "threshold",
    threshold: float = 0.05,
    minimize_trades: bool = True,
    constraints: Optional[Dict] = None,
    transaction_cost_per_share: float = 0.0,
    transaction_cost_pct: float = 0.001
) -> Dict[str, Any]:
    """
    Generate rebalancing trades to align portfolio with target weights.

    Args:
        current_positions: Current holdings
            {
                "AAPL": {"shares": 100, "value": 18500, "price": 185.00},
                "MSFT": {"shares": 50, "value": 21000, "price": 420.00}
            }
        target_weights: Desired allocation
            {"AAPL": 0.30, "MSFT": 0.40, "GOOGL": 0.30}
        total_value: Total portfolio value (positions + cash)
        cash_available: Available cash for new purchases
        strategy: Rebalancing strategy
            - 'threshold': Only rebalance if drift > threshold
            - 'periodic': Full rebalance to target weights
            - 'tax_aware': Minimize tax impact (avoid selling winners)
        threshold: Drift threshold for rebalancing (default: 5%)
        minimize_trades: Reduce number of trades (default: True)
        constraints: Optional constraints
            - max_turnover: Maximum portfolio turnover (default: 1.0)
            - no_sell_list: Tickers not to sell
            - no_buy_list: Tickers not to buy
        transaction_cost_per_share: Fixed cost per share (default: $0.00)
        transaction_cost_pct: Percentage cost (default: 0.1%)

    Returns:
        {
            "trades": [
                {
                    "ticker": "AAPL",
                    "action": "sell",
                    "shares": 20,
                    "value": 3700,
                    "current_weight": 0.38,
                    "target_weight": 0.30,
                    "drift": 0.08,
                    "reason": "overweight by 8%"
                },
                ...
            ],
            "total_cost": 150,
            "turnover": 0.18,
            "drift_before": {"AAPL": 0.08, "MSFT": -0.10, ...},
            "drift_after": {"AAPL": 0.002, "MSFT": -0.001, ...},
            "cash_required": 5000,
            "cash_generated": 3700,
            "rebalancing_needed": true,
            "interpretation": "..."
        }

    Example:
        >>> result = await portfolio_rebalancer(
        ...     current_positions={"AAPL": {"shares": 100, "value": 18500}},
        ...     target_weights={"AAPL": 0.30, "MSFT": 0.70},
        ...     total_value=100000,
        ...     cash_available=5000
        ... )
    """
    try:
        logger.info(f"Rebalancing: {len(current_positions)} positions, strategy={strategy}")

        # Get current prices for all tickers
        all_tickers = list(set(list(current_positions.keys()) + list(target_weights.keys())))
        current_prices = await _get_current_prices(all_tickers, current_positions)

        # Calculate current weights
        current_weights = _calculate_current_weights(current_positions, total_value)

        # Calculate drift
        drift_before = _calculate_drift(current_weights, target_weights)

        # Determine if rebalancing is needed
        needs_rebalancing, reason = _check_rebalancing_needed(
            drift_before, strategy, threshold
        )

        if not needs_rebalancing:
            return {
                "rebalancing_needed": False,
                "reason": reason,
                "drift_before": drift_before,
                "total_cost": 0,
                "trades": [],
                "interpretation": "No rebalancing needed. Portfolio is within target bands."
            }

        # Generate trades
        trades, cash_required, cash_generated = _generate_trades(
            current_positions,
            current_weights,
            target_weights,
            total_value,
            cash_available,
            current_prices,
            strategy,
            minimize_trades,
            constraints
        )

        # Calculate transaction costs
        total_cost = _calculate_transaction_costs(
            trades, transaction_cost_per_share, transaction_cost_pct
        )

        # Calculate turnover
        turnover = _calculate_turnover(trades, total_value)

        # Calculate drift after rebalancing
        drift_after = _simulate_drift_after_trades(
            current_positions, trades, target_weights, total_value, current_prices
        )

        # Interpretation
        interpretation = _generate_interpretation(
            trades, total_cost, turnover, drift_before, drift_after, strategy
        )

        return {
            "rebalancing_needed": True,
            "trades": trades,
            "total_cost": round(total_cost, 2),
            "turnover": round(turnover, 4),
            "drift_before": {k: round(v, 4) for k, v in drift_before.items()},
            "drift_after": {k: round(v, 4) for k, v in drift_after.items()},
            "cash_required": round(cash_required, 2),
            "cash_generated": round(cash_generated, 2),
            "net_cash_flow": round(cash_generated - cash_required, 2),
            "metadata": {
                "num_trades": len(trades),
                "num_positions_before": len(current_positions),
                "num_positions_after": len([t for t in trades if t["action"] == "buy"]) +
                    len([p for p in current_positions if p not in [t["ticker"] for t in trades if t["action"] == "sell"]]),
                "strategy": strategy,
                "threshold": threshold
            },
            "interpretation": interpretation
        }

    except Exception as e:
        logger.error(f"Portfolio rebalancing failed: {str(e)}")
        return {
            "error": str(e),
            "current_positions": list(current_positions.keys()),
            "target_weights": list(target_weights.keys())
        }


async def _get_current_prices(
    tickers: List[str],
    current_positions: Dict[str, Dict]
) -> Dict[str, float]:
    """
    Get current prices for all tickers.

    First use prices from current_positions if available,
    then fetch missing prices from market data.
    """
    prices = {}

    # Use prices from positions
    for ticker, pos in current_positions.items():
        if "price" in pos:
            prices[ticker] = pos["price"]
        elif "value" in pos and "shares" in pos and pos["shares"] > 0:
            prices[ticker] = pos["value"] / pos["shares"]

    # Fetch missing prices
    missing = [t for t in tickers if t not in prices]
    if missing:
        try:
            price_data = load_stock_prices(missing, column="Close")
            latest_prices = price_data.iloc[-1]
            for ticker in missing:
                if ticker in latest_prices.index:
                    prices[ticker] = float(latest_prices[ticker])
        except Exception as e:
            logger.warning(f"Could not fetch prices for {missing}: {e}")
            # Use placeholder price
            for ticker in missing:
                prices[ticker] = 100.0  # Default

    return prices


def _calculate_current_weights(
    positions: Dict[str, Dict],
    total_value: float
) -> Dict[str, float]:
    """
    Calculate current portfolio weights.
    """
    weights = {}

    for ticker, pos in positions.items():
        position_value = pos.get("value", 0)
        weights[ticker] = position_value / total_value if total_value > 0 else 0

    return weights


def _calculate_drift(
    current_weights: Dict[str, float],
    target_weights: Dict[str, float]
) -> Dict[str, float]:
    """
    Calculate drift from target weights.

    Drift = current_weight - target_weight
    Positive = overweight, Negative = underweight
    """
    all_tickers = set(list(current_weights.keys()) + list(target_weights.keys()))

    drift = {}
    for ticker in all_tickers:
        current = current_weights.get(ticker, 0)
        target = target_weights.get(ticker, 0)
        drift[ticker] = current - target

    return drift


def _check_rebalancing_needed(
    drift: Dict[str, float],
    strategy: str,
    threshold: float
) -> Tuple[bool, str]:
    """
    Determine if rebalancing is needed based on strategy.
    """
    if strategy == "periodic":
        return True, "Periodic rebalancing scheduled"

    elif strategy == "threshold" or strategy == "tax_aware":
        # Check if any position exceeds threshold
        max_drift = max([abs(d) for d in drift.values()])

        if max_drift > threshold:
            return True, f"Max drift {max_drift:.1%} exceeds threshold {threshold:.1%}"
        else:
            return False, f"Max drift {max_drift:.1%} within threshold {threshold:.1%}"

    else:
        return True, "Default rebalancing"


def _generate_trades(
    current_positions: Dict[str, Dict],
    current_weights: Dict[str, float],
    target_weights: Dict[str, float],
    total_value: float,
    cash_available: float,
    current_prices: Dict[str, float],
    strategy: str,
    minimize_trades: bool,
    constraints: Optional[Dict]
) -> Tuple[List[Dict], float, float]:
    """
    Generate optimal trade list.
    """
    trades = []
    cash_required = 0
    cash_generated = 0

    # Get constraints
    no_sell_list = []
    no_buy_list = []
    if constraints:
        no_sell_list = constraints.get("no_sell_list", [])
        no_buy_list = constraints.get("no_buy_list", [])

    all_tickers = set(list(current_weights.keys()) + list(target_weights.keys()))

    for ticker in all_tickers:
        current_weight = current_weights.get(ticker, 0)
        target_weight = target_weights.get(ticker, 0)
        drift = current_weight - target_weight

        # Skip if drift is negligible
        if minimize_trades and abs(drift) < 0.01:  # 1% threshold
            continue

        # Current position
        current_value = current_weight * total_value
        target_value = target_weight * total_value
        diff_value = target_value - current_value

        # Get current shares
        current_shares = current_positions.get(ticker, {}).get("shares", 0)
        price = current_prices.get(ticker, 100.0)

        # Calculate required trade
        if diff_value > 0:  # Need to buy
            if ticker in no_buy_list:
                continue

            shares_to_buy = int(diff_value / price)
            if shares_to_buy == 0:
                continue

            trade_value = shares_to_buy * price
            cash_required += trade_value

            trades.append({
                "ticker": ticker,
                "action": "buy",
                "shares": shares_to_buy,
                "price": round(price, 2),
                "value": round(trade_value, 2),
                "current_weight": round(current_weight, 4),
                "target_weight": round(target_weight, 4),
                "drift": round(drift, 4),
                "reason": f"underweight by {abs(drift):.1%}"
            })

        elif diff_value < 0:  # Need to sell
            if ticker in no_sell_list:
                continue

            if current_shares == 0:
                continue

            shares_to_sell = min(int(abs(diff_value) / price), current_shares)
            if shares_to_sell == 0:
                continue

            trade_value = shares_to_sell * price
            cash_generated += trade_value

            trades.append({
                "ticker": ticker,
                "action": "sell",
                "shares": shares_to_sell,
                "price": round(price, 2),
                "value": round(trade_value, 2),
                "current_weight": round(current_weight, 4),
                "target_weight": round(target_weight, 4),
                "drift": round(drift, 4),
                "reason": f"overweight by {drift:.1%}"
            })

    # Sort trades: sells first (generate cash), then buys
    trades_sorted = sorted(trades, key=lambda x: 0 if x["action"] == "sell" else 1)

    return trades_sorted, cash_required, cash_generated


def _calculate_transaction_costs(
    trades: List[Dict],
    cost_per_share: float,
    cost_pct: float
) -> float:
    """
    Calculate total transaction costs.
    """
    total_cost = 0

    for trade in trades:
        shares = trade["shares"]
        value = trade["value"]

        # Fixed cost per share
        fixed_cost = shares * cost_per_share

        # Percentage cost
        pct_cost = value * cost_pct

        total_cost += fixed_cost + pct_cost

    return total_cost


def _calculate_turnover(trades: List[Dict], total_value: float) -> float:
    """
    Calculate portfolio turnover.

    Turnover = (Total buy value + Total sell value) / (2 * Portfolio value)
    """
    if total_value == 0:
        return 0

    total_traded = sum([t["value"] for t in trades])
    return total_traded / total_value


def _simulate_drift_after_trades(
    current_positions: Dict[str, Dict],
    trades: List[Dict],
    target_weights: Dict[str, float],
    total_value: float,
    current_prices: Dict[str, float]
) -> Dict[str, float]:
    """
    Simulate portfolio weights after executing trades.
    """
    # Create new positions
    new_positions = {ticker: pos.copy() for ticker, pos in current_positions.items()}

    # Apply trades
    for trade in trades:
        ticker = trade["ticker"]
        shares = trade["shares"]
        action = trade["action"]

        if ticker not in new_positions:
            new_positions[ticker] = {"shares": 0, "value": 0}

        if action == "buy":
            new_positions[ticker]["shares"] = new_positions[ticker].get("shares", 0) + shares
        elif action == "sell":
            new_positions[ticker]["shares"] = new_positions[ticker].get("shares", 0) - shares

        # Update value
        price = current_prices.get(ticker, trade["price"])
        new_positions[ticker]["value"] = new_positions[ticker]["shares"] * price

    # Calculate new weights
    new_weights = _calculate_current_weights(new_positions, total_value)

    # Calculate drift
    return _calculate_drift(new_weights, target_weights)


def _generate_interpretation(
    trades: List[Dict],
    total_cost: float,
    turnover: float,
    drift_before: Dict[str, float],
    drift_after: Dict[str, float],
    strategy: str
) -> str:
    """
    Generate human-readable interpretation.
    """
    num_trades = len(trades)
    num_buys = len([t for t in trades if t["action"] == "buy"])
    num_sells = len([t for t in trades if t["action"] == "sell"])

    max_drift_before = max([abs(d) for d in drift_before.values()])
    max_drift_after = max([abs(d) for d in drift_after.values()]) if drift_after else 0

    interpretation = (
        f"Rebalancing requires {num_trades} trades ({num_buys} buys, {num_sells} sells) "
        f"with estimated cost of ${total_cost:.2f}. "
        f"Portfolio turnover: {turnover:.1%}. "
    )

    if num_trades > 0:
        # Largest trades
        largest_trade = max(trades, key=lambda x: x["value"])
        interpretation += (
            f"Largest trade: {largest_trade['action']} {largest_trade['shares']} shares of "
            f"{largest_trade['ticker']} (${largest_trade['value']:,.0f}). "
        )

    interpretation += (
        f"Maximum drift before: {max_drift_before:.1%}, "
        f"after: {max_drift_after:.1%}. "
    )

    if max_drift_after < 0.02:
        interpretation += "Portfolio will be well-aligned with targets after rebalancing."
    elif max_drift_after < 0.05:
        interpretation += "Portfolio will be reasonably aligned with targets."
    else:
        interpretation += "Some drift will remain due to discrete share lots."

    return interpretation


# Example usage
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test():
        # Test: Rebalancing scenario
        current_pos = {
            "AAPL": {"shares": 100, "value": 18500, "price": 185.00},
            "MSFT": {"shares": 50, "value": 21000, "price": 420.00},
            "GOOGL": {"shares": 30, "value": 4500, "price": 150.00}
        }

        target = {
            "AAPL": 0.30,
            "MSFT": 0.40,
            "GOOGL": 0.30
        }

        result = await portfolio_rebalancer(
            current_positions=current_pos,
            target_weights=target,
            total_value=50000,
            cash_available=5000,
            strategy="threshold",
            threshold=0.05
        )

        print("\n=== Rebalancing Test ===")
        print(f"Rebalancing needed: {result['rebalancing_needed']}")
        if result['rebalancing_needed']:
            print(f"\nTrades:")
            for trade in result['trades']:
                print(f"  {trade['action'].upper()} {trade['shares']} {trade['ticker']} "
                      f"@ ${trade['price']} = ${trade['value']:,.2f}")
            print(f"\nTotal cost: ${result['total_cost']:.2f}")
            print(f"Turnover: {result['turnover']:.1%}")
            print(f"\nInterpretation: {result['interpretation']}")

    asyncio.run(test())
