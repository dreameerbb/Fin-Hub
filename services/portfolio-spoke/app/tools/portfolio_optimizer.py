"""
Portfolio Optimizer - Generate optimal portfolio weights

Supports multiple optimization methods:
- Mean-Variance (Markowitz) - scipy-based implementation
- Hierarchical Risk Parity (HRP)
- Risk Parity
- Maximum Sharpe Ratio
- Minimum Volatility

Uses scipy.optimize for professional-grade optimization without external dependencies.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging

# Portfolio optimization using scipy
from scipy.optimize import minimize
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform

from app.utils.data_loader import load_stock_prices, calculate_returns
from app.utils.portfolio_math import (
    portfolio_return, portfolio_volatility, sharpe_ratio,
    diversification_ratio, herfindahl_index, effective_number_of_assets,
    convert_to_dict, normalize_weights
)

logger = logging.getLogger(__name__)


async def portfolio_optimizer(
    tickers: List[str],
    method: str = "mean_variance",
    objective: str = "max_sharpe",
    target_return: Optional[float] = None,
    target_risk: Optional[float] = None,
    constraints: Optional[Dict] = None,
    risk_free_rate: float = 0.03,
    views: Optional[Dict] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Optimize portfolio weights using various methods.

    Args:
        tickers: List of stock symbols (2-50 stocks)
        method: Optimization method
            - 'mean_variance': Markowitz mean-variance optimization
            - 'hrp': Hierarchical Risk Parity
            - 'risk_parity': Equal risk contribution
            - 'max_sharpe': Maximum Sharpe ratio (alias for mean_variance)
            - 'min_volatility': Minimum volatility (alias for mean_variance)
        objective: Optimization objective (for mean_variance)
            - 'max_sharpe': Maximize Sharpe ratio
            - 'min_volatility': Minimize volatility
            - 'efficient_return': Target return with min risk
            - 'efficient_risk': Target risk with max return
        target_return: Target return for efficient_return objective
        target_risk: Target risk for efficient_risk objective
        constraints: Optional constraints
            - max_weight: Maximum weight per asset (default: 1.0)
            - min_weight: Minimum weight per asset (default: 0.0)
        risk_free_rate: Risk-free rate (default: 3%)
        views: (Not implemented in scipy version)
        start_date: Data start date (default: 1 year ago)
        end_date: Data end date (default: today)

    Returns:
        {
            "weights": {"AAPL": 0.35, "MSFT": 0.40, ...},
            "expected_return": 0.18,
            "expected_risk": 0.22,
            "sharpe_ratio": 0.68,
            "method_used": "mean_variance",
            "efficient_frontier": [...],
            "interpretation": "...",
            "metadata": {...}
        }
    """
    try:
        # Validate inputs
        if len(tickers) < 2:
            raise ValueError("Need at least 2 stocks for portfolio optimization")
        if len(tickers) > 50:
            raise ValueError("Maximum 50 stocks supported")

        logger.info(f"Optimizing portfolio: {len(tickers)} stocks, method={method}")

        # Load price data
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        prices = load_stock_prices(tickers, start_date, end_date)

        if len(prices) < 30:
            raise ValueError(f"Insufficient data: only {len(prices)} days (need at least 30)")

        # Calculate expected returns and covariance
        returns = calculate_returns(prices, method="log")
        mu = returns.mean() * 252  # Annualize
        S = returns.cov() * 252    # Annualize

        # Apply optimization method
        if method in ["mean_variance", "max_sharpe", "min_volatility"]:
            if method == "max_sharpe":
                objective = "max_sharpe"
            elif method == "min_volatility":
                objective = "min_volatility"

            weights, perf = _optimize_mean_variance(
                mu, S, tickers, objective, target_return, target_risk,
                constraints, risk_free_rate
            )
            method_used = "mean_variance"

        elif method == "hrp":
            weights, perf = _optimize_hrp(returns, tickers)
            method_used = "hrp"

        elif method == "risk_parity":
            weights, perf = _optimize_risk_parity(mu, S, tickers, risk_free_rate)
            method_used = "risk_parity"

        else:
            raise ValueError(f"Unknown optimization method: {method}")

        # Calculate portfolio metrics
        weights_array = np.array([weights[t] for t in tickers])
        mu_array = mu.values

        expected_ret = portfolio_return(weights_array, mu_array)
        expected_vol = portfolio_volatility(weights_array, S.values)
        sharpe = sharpe_ratio(expected_ret, expected_vol, risk_free_rate)

        # Diversification metrics
        volatilities = np.sqrt(np.diag(S.values))
        div_ratio = diversification_ratio(weights_array, volatilities, S.values)
        hhi = herfindahl_index(weights_array)
        eff_assets = effective_number_of_assets(weights_array)

        # Generate efficient frontier (for mean-variance only)
        ef_points = []
        if method_used == "mean_variance":
            try:
                ef_points = _generate_efficient_frontier(mu, S, tickers, risk_free_rate)
            except Exception as e:
                logger.warning(f"Could not generate efficient frontier: {e}")

        # Interpretation
        interpretation = _generate_interpretation(
            weights, expected_ret, expected_vol, sharpe,
            method_used, objective, hhi, div_ratio
        )

        return {
            "weights": weights,
            "expected_return": round(expected_ret, 4),
            "expected_risk": round(expected_vol, 4),
            "sharpe_ratio": round(sharpe, 2),
            "method_used": method_used,
            "objective_used": objective if method_used == "mean_variance" else method_used,
            "efficient_frontier": ef_points,
            "metadata": {
                "num_assets": len(tickers),
                "hhi": round(hhi, 3),
                "effective_assets": round(eff_assets, 2),
                "diversification_ratio": round(div_ratio, 2),
                "data_period_days": len(prices),
                "risk_free_rate": risk_free_rate
            },
            "interpretation": interpretation
        }

    except Exception as e:
        logger.error(f"Portfolio optimization failed: {str(e)}")
        return {
            "error": str(e),
            "method": method,
            "tickers": tickers
        }


def _optimize_mean_variance(
    mu: pd.Series,
    S: pd.DataFrame,
    tickers: List[str],
    objective: str,
    target_return: Optional[float],
    target_risk: Optional[float],
    constraints_dict: Optional[Dict],
    risk_free_rate: float
) -> Tuple[Dict[str, float], Dict]:
    """
    Mean-Variance optimization using scipy.optimize.
    """
    n = len(tickers)

    # Set weight bounds
    bounds = [(0, 1) for _ in range(n)]  # Long-only
    if constraints_dict:
        min_w = constraints_dict.get("min_weight", 0)
        max_w = constraints_dict.get("max_weight", 1)
        bounds = [(min_w, max_w) for _ in range(n)]

    # Constraints: weights sum to 1
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]

    # Add target return/risk constraints
    if objective == "efficient_return" and target_return is not None:
        constraints.append({
            'type': 'eq',
            'fun': lambda w: portfolio_return(w, mu.values) - target_return
        })
    elif objective == "efficient_risk" and target_risk is not None:
        constraints.append({
            'type': 'eq',
            'fun': lambda w: portfolio_volatility(w, S.values) - target_risk
        })

    # Initial guess: equal weights
    w0 = np.ones(n) / n

    # Objective function
    if objective == "max_sharpe":
        # Minimize negative Sharpe ratio
        def obj_func(w):
            ret = portfolio_return(w, mu.values)
            vol = portfolio_volatility(w, S.values)
            if vol == 0:
                return 1e10
            return -(ret - risk_free_rate) / vol

    elif objective == "min_volatility":
        # Minimize volatility
        def obj_func(w):
            return portfolio_volatility(w, S.values)

    elif objective == "efficient_return":
        # Minimize risk for target return
        def obj_func(w):
            return portfolio_volatility(w, S.values)

    elif objective == "efficient_risk":
        # Maximize return for target risk
        def obj_func(w):
            return -portfolio_return(w, mu.values)

    else:
        # Default to max Sharpe
        def obj_func(w):
            ret = portfolio_return(w, mu.values)
            vol = portfolio_volatility(w, S.values)
            if vol == 0:
                return 1e10
            return -(ret - risk_free_rate) / vol

    # Optimize
    result = minimize(
        obj_func,
        w0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 1000, 'ftol': 1e-9}
    )

    if not result.success:
        logger.warning(f"Optimization did not converge: {result.message}")

    # Get weights
    weights_array = result.x
    weights = {ticker: float(w) for ticker, w in zip(tickers, weights_array)}

    # Calculate performance
    ret = portfolio_return(weights_array, mu.values)
    vol = portfolio_volatility(weights_array, S.values)
    sharpe = sharpe_ratio(ret, vol, risk_free_rate)

    return weights, {
        "expected_return": ret,
        "volatility": vol,
        "sharpe_ratio": sharpe
    }


def _optimize_hrp(returns: pd.DataFrame, tickers: List[str]) -> Tuple[Dict[str, float], Dict]:
    """
    Hierarchical Risk Parity optimization using scipy.
    """
    # Calculate correlation matrix
    corr = returns.corr()
    dist = np.sqrt((1 - corr) / 2)  # Distance matrix

    # Hierarchical clustering
    dist_condensed = squareform(dist.values, checks=False)
    Z = linkage(dist_condensed, method='single')

    # Get cluster order
    order = leaves_list(Z)

    # Calculate weights using inverse variance
    weights_array = _hrp_weights(returns, order)

    weights = {ticker: float(w) for ticker, w in zip(tickers, weights_array)}

    # Calculate performance
    mu = returns.mean() * 252
    S = returns.cov() * 252

    ret = portfolio_return(weights_array, mu.values)
    vol = portfolio_volatility(weights_array, S.values)
    sharpe = sharpe_ratio(ret, vol)

    return weights, {
        "expected_return": ret,
        "volatility": vol,
        "sharpe_ratio": sharpe
    }


def _hrp_weights(returns: pd.DataFrame, order: np.ndarray) -> np.ndarray:
    """
    Calculate HRP weights using recursive bisection.
    """
    n = len(returns.columns)
    weights = np.ones(n)

    # Recursive bisection
    _hrp_recursive_bisection(returns, order, 0, n, weights)

    # Normalize
    return weights / np.sum(weights)


def _hrp_recursive_bisection(
    returns: pd.DataFrame,
    order: np.ndarray,
    start: int,
    end: int,
    weights: np.ndarray
):
    """
    Recursive bisection for HRP.
    """
    if end - start <= 1:
        return

    # Split cluster
    mid = start + (end - start) // 2

    # Get left and right clusters
    left_idx = order[start:mid]
    right_idx = order[mid:end]

    # Calculate cluster variances
    left_var = _cluster_variance(returns.iloc[:, left_idx])
    right_var = _cluster_variance(returns.iloc[:, right_idx])

    # Allocate weights inversely proportional to variance
    total_var = left_var + right_var
    if total_var > 0:
        left_weight = 1 - left_var / total_var
        right_weight = 1 - right_var / total_var
    else:
        left_weight = 0.5
        right_weight = 0.5

    # Update weights
    weights[left_idx] *= left_weight
    weights[right_idx] *= right_weight

    # Recursively bisect
    _hrp_recursive_bisection(returns, order, start, mid, weights)
    _hrp_recursive_bisection(returns, order, mid, end, weights)


def _cluster_variance(returns: pd.DataFrame) -> float:
    """
    Calculate variance of a cluster.
    """
    # Equal-weighted portfolio variance
    cov = returns.cov()
    n = len(returns.columns)
    w = np.ones(n) / n
    var = np.dot(w.T, np.dot(cov.values, w))
    return var


def _optimize_risk_parity(
    mu: pd.Series,
    S: pd.DataFrame,
    tickers: List[str],
    risk_free_rate: float
) -> Tuple[Dict[str, float], Dict]:
    """
    Risk Parity optimization - inverse volatility weighting.
    """
    # Get volatilities
    volatilities = np.sqrt(np.diag(S.values))

    # Inverse volatility weights
    inv_vol = 1 / volatilities
    weights_array = inv_vol / np.sum(inv_vol)

    weights = {ticker: float(w) for ticker, w in zip(tickers, weights_array)}

    # Calculate performance
    ret = portfolio_return(weights_array, mu.values)
    vol = portfolio_volatility(weights_array, S.values)
    sharpe = sharpe_ratio(ret, vol, risk_free_rate)

    return weights, {
        "expected_return": ret,
        "volatility": vol,
        "sharpe_ratio": sharpe
    }


def _generate_efficient_frontier(
    mu: pd.Series,
    S: pd.DataFrame,
    tickers: List[str],
    risk_free_rate: float,
    num_points: int = 20
) -> List[Dict]:
    """
    Generate efficient frontier points for visualization.
    """
    points = []

    try:
        # Generate range of target returns
        min_return = mu.min()
        max_return = mu.max()
        target_returns = np.linspace(min_return, max_return, num_points)

        for target in target_returns:
            try:
                weights, perf = _optimize_mean_variance(
                    mu, S, tickers,
                    objective="efficient_return",
                    target_return=target,
                    target_risk=None,
                    constraints_dict=None,
                    risk_free_rate=risk_free_rate
                )

                points.append({
                    "return": round(perf["expected_return"], 4),
                    "risk": round(perf["volatility"], 4),
                    "sharpe": round(perf["sharpe_ratio"], 2)
                })
            except Exception:
                continue

    except Exception as e:
        logger.warning(f"Efficient frontier generation failed: {e}")

    return points


def _generate_interpretation(
    weights: Dict[str, float],
    expected_return: float,
    expected_risk: float,
    sharpe: float,
    method: str,
    objective: str,
    hhi: float,
    diversification_ratio: float
) -> str:
    """
    Generate human-readable interpretation.
    """
    # Top holdings
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    top_3 = sorted_weights[:3]
    top_holdings = ", ".join([f"{t} ({w:.1%})" for t, w in top_3])

    # Diversification assessment
    if hhi < 0.15:
        div_level = "excellent"
    elif hhi < 0.25:
        div_level = "good"
    elif hhi < 0.35:
        div_level = "moderate"
    else:
        div_level = "concentrated"

    # Sharpe assessment
    if sharpe > 2.0:
        sharpe_level = "exceptional"
    elif sharpe > 1.0:
        sharpe_level = "very good"
    elif sharpe > 0.5:
        sharpe_level = "good"
    else:
        sharpe_level = "modest"

    method_desc = {
        "mean_variance": "Mean-Variance (Markowitz)",
        "hrp": "Hierarchical Risk Parity",
        "risk_parity": "Risk Parity (equal risk contribution)"
    }.get(method, method)

    interpretation = (
        f"Portfolio optimized using {method_desc} targeting {objective}. "
        f"Expected annual return: {expected_return:.1%}, Risk: {expected_risk:.1%}, "
        f"Sharpe ratio: {sharpe:.2f} ({sharpe_level}). "
        f"Top holdings: {top_holdings}. "
        f"Diversification: {div_level} (HHI: {hhi:.3f}, Div Ratio: {diversification_ratio:.2f}). "
    )

    if diversification_ratio > 1.3:
        interpretation += "Portfolio benefits significantly from diversification. "
    elif diversification_ratio < 1.1:
        interpretation += "Limited diversification benefit - consider adding uncorrelated assets. "

    return interpretation


# Example usage
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test():
        # Test 1: Max Sharpe
        result = await portfolio_optimizer(
            tickers=["AAPL", "MSFT", "GOOGL", "AMZN"],
            method="mean_variance",
            objective="max_sharpe"
        )
        print("\n=== Test 1: Max Sharpe ===")
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Weights: {result['weights']}")
            print(f"Expected Return: {result['expected_return']:.2%}")
            print(f"Sharpe: {result['sharpe_ratio']:.2f}")
            print(f"Interpretation: {result['interpretation']}")

    asyncio.run(test())
