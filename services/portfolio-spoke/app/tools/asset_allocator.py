"""
Asset Allocator - Strategic and tactical asset allocation

Provides asset allocation strategies including:
- Strategic Allocation (long-term, policy-based)
- Tactical Allocation (short-term, market-timing)
- Diversification Analysis
- Correlation Analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging

from app.utils.data_loader import load_stock_prices, calculate_returns, get_covariance_matrix
from app.utils.portfolio_math import (
    sharpe_ratio, portfolio_return, portfolio_volatility,
    calculate_beta, annualize_return, annualize_volatility
)

logger = logging.getLogger(__name__)


async def asset_allocator(
    asset_classes: Dict[str, List[str]],
    allocation_type: str = "strategic",
    risk_tolerance: str = "moderate",
    constraints: Optional[Dict[str, float]] = None,
    rebalancing_threshold: float = 0.05,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    risk_free_rate: float = 0.03
) -> Dict[str, Any]:
    """
    Perform asset allocation across multiple asset classes.

    Args:
        asset_classes: Asset classes with representative tickers
            {
                "US_Equity": ["AAPL", "MSFT", "GOOGL"],
                "International_Equity": ["TSM", "BABA"],
                "Fixed_Income": ["TLT", "AGG"],
                "Commodities": ["GLD", "SLV"],
                "Cash": ["SHY"]
            }
        allocation_type: "strategic" or "tactical"
        risk_tolerance: "conservative", "moderate", or "aggressive"
        constraints: Asset class constraints
            {
                "US_Equity": {"min": 0.3, "max": 0.6},
                "Fixed_Income": {"min": 0.2, "max": 0.5}
            }
        rebalancing_threshold: Drift threshold for rebalancing (default: 5%)
        start_date: Analysis start date (default: 1 year ago)
        end_date: Analysis end date (default: today)
        risk_free_rate: Risk-free rate (default: 3%)

    Returns:
        {
            "allocation": {
                "US_Equity": 0.45,
                "International_Equity": 0.15,
                "Fixed_Income": 0.25,
                "Commodities": 0.10,
                "Cash": 0.05
            },
            "asset_weights": {
                "AAPL": 0.15,
                "MSFT": 0.15,
                ...
            },
            "diversification": {
                "effective_assets": 8.5,
                "concentration_risk": "Low",
                "herfindahl_index": 0.12
            },
            "correlation_analysis": {
                "average_correlation": 0.35,
                "max_correlation_pair": ["AAPL", "MSFT", 0.85],
                "min_correlation_pair": ["GLD", "AAPL", -0.15]
            },
            "rebalancing_needed": false,
            "expected_return": 0.08,
            "expected_volatility": 0.12,
            "sharpe_ratio": 0.42,
            "interpretation": "..."
        }

    Example:
        >>> result = await asset_allocator(
        ...     asset_classes={
        ...         "US_Equity": ["AAPL", "MSFT", "GOOGL"],
        ...         "Fixed_Income": ["TLT", "AGG"]
        ...     },
        ...     allocation_type="strategic",
        ...     risk_tolerance="moderate"
        ... )
    """
    try:
        logger.info(f"Asset allocation: {allocation_type}, risk={risk_tolerance}")

        # Set default dates
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        # Flatten all tickers
        all_tickers = []
        for tickers in asset_classes.values():
            all_tickers.extend(tickers)

        # Load price data
        prices = load_stock_prices(all_tickers, start_date, end_date)

        if len(prices) < 30:
            raise ValueError(f"Insufficient data: only {len(prices)} days")

        # Calculate returns
        returns = calculate_returns(prices, method="log")

        # Get asset class allocation
        if allocation_type == "strategic":
            allocation = _strategic_allocation(
                asset_classes, returns, risk_tolerance, constraints
            )
        elif allocation_type == "tactical":
            allocation = _tactical_allocation(
                asset_classes, returns, prices, risk_tolerance, constraints
            )
        else:
            raise ValueError(f"Unknown allocation_type: {allocation_type}")

        # Calculate individual asset weights within classes
        asset_weights = _calculate_asset_weights(
            asset_classes, allocation, returns
        )

        # Diversification analysis
        diversification = _analyze_diversification(
            asset_weights, returns
        )

        # Correlation analysis
        correlation_analysis = _analyze_correlations(
            returns, asset_weights
        )

        # Portfolio metrics
        weights_array = np.array([asset_weights.get(t, 0) for t in returns.columns])
        mu = returns.mean() * 252
        cov = returns.cov() * 252

        expected_return = portfolio_return(weights_array, mu.values)
        expected_volatility = portfolio_volatility(weights_array, cov.values)
        sharpe = sharpe_ratio(expected_return, expected_volatility, risk_free_rate)

        # Rebalancing check
        rebalancing_needed = _check_rebalancing_needed(
            allocation, asset_classes, prices, rebalancing_threshold
        )

        # Interpretation
        interpretation = _generate_interpretation(
            allocation, allocation_type, risk_tolerance, diversification,
            correlation_analysis, expected_return, expected_volatility, sharpe
        )

        return {
            "allocation": allocation,
            "asset_weights": asset_weights,
            "diversification": diversification,
            "correlation_analysis": correlation_analysis,
            "rebalancing_needed": rebalancing_needed,
            "expected_return": round(expected_return, 4),
            "expected_volatility": round(expected_volatility, 4),
            "sharpe_ratio": round(sharpe, 2),
            "metadata": {
                "allocation_type": allocation_type,
                "risk_tolerance": risk_tolerance,
                "num_asset_classes": len(asset_classes),
                "num_assets": len(all_tickers),
                "start_date": start_date,
                "end_date": end_date
            },
            "interpretation": interpretation
        }

    except Exception as e:
        logger.error(f"Asset allocation failed: {str(e)}")
        return {
            "error": str(e),
            "asset_classes": list(asset_classes.keys())
        }


def _strategic_allocation(
    asset_classes: Dict[str, List[str]],
    returns: pd.DataFrame,
    risk_tolerance: str,
    constraints: Optional[Dict[str, float]]
) -> Dict[str, float]:
    """
    Strategic allocation based on long-term risk/return profiles.
    """
    # Calculate asset class returns and volatilities
    class_metrics = {}
    for class_name, tickers in asset_classes.items():
        available = [t for t in tickers if t in returns.columns]
        if not available:
            continue

        class_returns = returns[available].mean(axis=1)
        ann_return = class_returns.mean() * 252
        ann_vol = class_returns.std() * np.sqrt(252)

        class_metrics[class_name] = {
            "return": ann_return,
            "volatility": ann_vol,
            "sharpe": (ann_return - 0.03) / ann_vol if ann_vol > 0 else 0
        }

    # Risk tolerance profiles
    risk_profiles = {
        "conservative": {"equity_max": 0.40, "fixed_income_min": 0.40},
        "moderate": {"equity_max": 0.65, "fixed_income_min": 0.20},
        "aggressive": {"equity_max": 0.85, "fixed_income_min": 0.10}
    }

    profile = risk_profiles.get(risk_tolerance, risk_profiles["moderate"])

    # Initial allocation based on risk tolerance
    allocation = {}
    total_equity = 0
    total_fixed = 0

    # Identify asset classes
    equity_classes = [c for c in asset_classes.keys() if "Equity" in c or "Stock" in c]
    fixed_classes = [c for c in asset_classes.keys() if "Fixed" in c or "Bond" in c or "Income" in c]
    other_classes = [c for c in asset_classes.keys() if c not in equity_classes and c not in fixed_classes]

    # Equal weight within equity classes
    if equity_classes:
        equity_weight = profile["equity_max"] / len(equity_classes)
        for eq_class in equity_classes:
            if eq_class in class_metrics:
                allocation[eq_class] = equity_weight
                total_equity += equity_weight

    # Equal weight within fixed income
    if fixed_classes:
        fixed_weight = profile["fixed_income_min"] / len(fixed_classes)
        for fix_class in fixed_classes:
            if fix_class in class_metrics:
                allocation[fix_class] = fixed_weight
                total_fixed += fixed_weight

    # Allocate remainder to other classes
    remainder = 1.0 - total_equity - total_fixed
    if other_classes and remainder > 0:
        other_weight = remainder / len(other_classes)
        for other_class in other_classes:
            if other_class in class_metrics:
                allocation[other_class] = other_weight

    # Apply constraints
    if constraints:
        allocation = _apply_constraints(allocation, constraints)

    # Normalize to 1.0
    total = sum(allocation.values())
    if total > 0:
        allocation = {k: v / total for k, v in allocation.items()}

    return allocation


def _tactical_allocation(
    asset_classes: Dict[str, List[str]],
    returns: pd.DataFrame,
    prices: pd.DataFrame,
    risk_tolerance: str,
    constraints: Optional[Dict[str, float]]
) -> Dict[str, float]:
    """
    Tactical allocation based on recent market trends and momentum.
    """
    # Start with strategic allocation
    strategic = _strategic_allocation(asset_classes, returns, risk_tolerance, constraints)

    # Calculate momentum for each asset class (3-month and 6-month)
    lookback_short = min(60, len(prices) // 2)  # ~3 months
    lookback_long = min(120, len(prices) - 1)  # ~6 months

    class_momentum = {}
    for class_name, tickers in asset_classes.items():
        available = [t for t in tickers if t in prices.columns]
        if not available:
            continue

        # Average momentum across class
        momentum_scores = []
        for ticker in available:
            if len(prices[ticker]) < lookback_short:
                continue

            short_mom = (prices[ticker].iloc[-1] / prices[ticker].iloc[-lookback_short] - 1)
            long_mom = (prices[ticker].iloc[-1] / prices[ticker].iloc[-lookback_long] - 1) if len(prices[ticker]) >= lookback_long else short_mom

            # Combined momentum score
            mom_score = 0.6 * short_mom + 0.4 * long_mom
            momentum_scores.append(mom_score)

        if momentum_scores:
            class_momentum[class_name] = np.mean(momentum_scores)

    # Adjust strategic allocation based on momentum
    # Overweight positive momentum, underweight negative
    tactical = strategic.copy()

    momentum_adjustment = 0.15  # Max 15% tilt from strategic

    for class_name in tactical.keys():
        if class_name in class_momentum:
            mom = class_momentum[class_name]

            # Normalize momentum to [-1, 1] range
            all_mom = list(class_momentum.values())
            mom_std = np.std(all_mom) if len(all_mom) > 1 else 0.1
            mom_normalized = np.clip(mom / mom_std, -1, 1)

            # Adjust allocation
            adjustment = momentum_adjustment * mom_normalized
            tactical[class_name] = strategic[class_name] * (1 + adjustment)

    # Apply constraints and normalize
    if constraints:
        tactical = _apply_constraints(tactical, constraints)

    total = sum(tactical.values())
    if total > 0:
        tactical = {k: v / total for k, v in tactical.items()}

    return tactical


def _calculate_asset_weights(
    asset_classes: Dict[str, List[str]],
    allocation: Dict[str, float],
    returns: pd.DataFrame
) -> Dict[str, float]:
    """
    Distribute asset class weights to individual assets.
    """
    asset_weights = {}

    for class_name, class_weight in allocation.items():
        if class_name not in asset_classes:
            continue

        tickers = asset_classes[class_name]
        available = [t for t in tickers if t in returns.columns]

        if not available:
            continue

        # Equal weight within asset class (simple approach)
        # Could be enhanced with optimization
        weight_per_asset = class_weight / len(available)

        for ticker in available:
            asset_weights[ticker] = weight_per_asset

    return asset_weights


def _analyze_diversification(
    weights: Dict[str, float],
    returns: pd.DataFrame
) -> Dict[str, Any]:
    """
    Analyze portfolio diversification.
    """
    if not weights:
        return {
            "effective_assets": 0,
            "concentration_risk": "N/A",
            "herfindahl_index": 0
        }

    # Herfindahl-Hirschman Index (HHI)
    weights_array = np.array(list(weights.values()))
    hhi = np.sum(weights_array ** 2)

    # Effective number of assets
    effective_n = 1 / hhi if hhi > 0 else 0

    # Concentration risk assessment
    if hhi < 0.15:
        concentration = "Low"
    elif hhi < 0.25:
        concentration = "Moderate"
    else:
        concentration = "High"

    # Top 3 holdings concentration
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    top_3_concentration = sum([w for _, w in sorted_weights[:3]])

    return {
        "effective_assets": round(effective_n, 2),
        "concentration_risk": concentration,
        "herfindahl_index": round(hhi, 4),
        "top_3_concentration": round(top_3_concentration, 4)
    }


def _analyze_correlations(
    returns: pd.DataFrame,
    weights: Dict[str, float]
) -> Dict[str, Any]:
    """
    Analyze correlations between assets.
    """
    # Filter to weighted assets
    weighted_tickers = [t for t in weights.keys() if t in returns.columns and weights[t] > 0.01]

    if len(weighted_tickers) < 2:
        return {
            "average_correlation": 0,
            "max_correlation_pair": None,
            "min_correlation_pair": None
        }

    corr_matrix = returns[weighted_tickers].corr()

    # Average correlation (excluding diagonal)
    mask = np.triu(np.ones_like(corr_matrix), k=1).astype(bool)
    correlations = corr_matrix.where(mask).stack()

    avg_corr = correlations.mean()

    # Max and min correlation pairs
    max_corr = correlations.max()
    min_corr = correlations.min()

    max_pair = correlations.idxmax()
    min_pair = correlations.idxmin()

    return {
        "average_correlation": round(avg_corr, 4),
        "max_correlation_pair": [max_pair[0], max_pair[1], round(max_corr, 4)],
        "min_correlation_pair": [min_pair[0], min_pair[1], round(min_corr, 4)]
    }


def _check_rebalancing_needed(
    target_allocation: Dict[str, float],
    asset_classes: Dict[str, List[str]],
    prices: pd.DataFrame,
    threshold: float
) -> bool:
    """
    Check if rebalancing is needed based on drift.
    """
    # Calculate current allocation based on latest prices
    current_values = {}
    total_value = 0

    for class_name, tickers in asset_classes.items():
        class_value = 0
        for ticker in tickers:
            if ticker in prices.columns:
                class_value += prices[ticker].iloc[-1]
        current_values[class_name] = class_value
        total_value += class_value

    if total_value == 0:
        return False

    # Current allocation percentages
    current_allocation = {k: v / total_value for k, v in current_values.items()}

    # Check drift
    for class_name in target_allocation.keys():
        target = target_allocation.get(class_name, 0)
        current = current_allocation.get(class_name, 0)
        drift = abs(current - target)

        if drift > threshold:
            return True

    return False


def _apply_constraints(
    allocation: Dict[str, float],
    constraints: Dict[str, Dict[str, float]]
) -> Dict[str, float]:
    """
    Apply min/max constraints to allocation.
    """
    constrained = allocation.copy()

    for class_name, limits in constraints.items():
        if class_name in constrained:
            min_weight = limits.get("min", 0)
            max_weight = limits.get("max", 1)

            constrained[class_name] = np.clip(
                constrained[class_name],
                min_weight,
                max_weight
            )

    return constrained


def _generate_interpretation(
    allocation: Dict[str, float],
    allocation_type: str,
    risk_tolerance: str,
    diversification: Dict,
    correlation: Dict,
    expected_return: float,
    expected_volatility: float,
    sharpe: float
) -> str:
    """
    Generate human-readable interpretation.
    """
    # Dominant asset class
    dominant = max(allocation.items(), key=lambda x: x[1])

    interpretation = (
        f"{allocation_type.capitalize()} asset allocation for {risk_tolerance} risk tolerance: "
        f"{dominant[0]} dominates at {dominant[1]:.1%}. "
    )

    interpretation += (
        f"Expected return: {expected_return:.1%}, "
        f"volatility: {expected_volatility:.1%}, "
        f"Sharpe ratio: {sharpe:.2f}. "
    )

    # Diversification assessment
    eff_assets = diversification.get("effective_assets", 0)
    concentration = diversification.get("concentration_risk", "Unknown")

    interpretation += (
        f"Portfolio has {eff_assets:.1f} effective assets "
        f"with {concentration.lower()} concentration risk. "
    )

    # Correlation assessment
    avg_corr = correlation.get("average_correlation", 0)
    if avg_corr < 0.3:
        corr_assessment = "well-diversified (low correlation)"
    elif avg_corr < 0.6:
        corr_assessment = "moderately diversified"
    else:
        corr_assessment = "concentrated (high correlation)"

    interpretation += f"Assets are {corr_assessment}. "

    # Risk assessment
    if risk_tolerance == "conservative" and expected_volatility > 0.15:
        interpretation += "Volatility may be higher than suitable for conservative profile. "
    elif risk_tolerance == "aggressive" and sharpe < 0.5:
        interpretation += "Risk-adjusted returns could be improved. "

    return interpretation


# Example usage
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test():
        # Test: Asset allocation
        asset_classes = {
            "US_Equity": ["AAPL", "MSFT", "GOOGL"],
            "Tech": ["NVDA", "AMD"],
            "Healthcare": ["JNJ", "PFE"],
            "Financial": ["JPM", "BAC"]
        }

        # Strategic allocation
        result = await asset_allocator(
            asset_classes=asset_classes,
            allocation_type="strategic",
            risk_tolerance="moderate",
            start_date="2024-01-01"
        )

        print("\n=== Strategic Asset Allocation ===" )
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"\nAsset Class Allocation:")
            for class_name, weight in result['allocation'].items():
                print(f"  {class_name}: {weight:.2%}")

            print(f"\nDiversification:")
            for k, v in result['diversification'].items():
                print(f"  {k}: {v}")

            print(f"\nCorrelation Analysis:")
            for k, v in result['correlation_analysis'].items():
                print(f"  {k}: {v}")

            print(f"\nExpected Return: {result['expected_return']:.2%}")
            print(f"Expected Volatility: {result['expected_volatility']:.2%}")
            print(f"Sharpe Ratio: {result['sharpe_ratio']:.2f}")
            print(f"Rebalancing Needed: {result['rebalancing_needed']}")

            print(f"\nInterpretation:\n{result['interpretation']}")

        # Tactical allocation
        print("\n\n=== Tactical Asset Allocation ===")
        result2 = await asset_allocator(
            asset_classes=asset_classes,
            allocation_type="tactical",
            risk_tolerance="aggressive",
            start_date="2024-01-01"
        )

        if "error" not in result2:
            print(f"\nAsset Class Allocation:")
            for class_name, weight in result2['allocation'].items():
                print(f"  {class_name}: {weight:.2%}")

    asyncio.run(test())
