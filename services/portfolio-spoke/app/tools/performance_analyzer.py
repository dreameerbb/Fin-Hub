"""
Performance Analyzer - Calculate portfolio performance metrics and attribution

Provides comprehensive performance analysis including:
- Returns (Total, Annualized, YTD, MTD)
- Risk Metrics (Sharpe, Sortino, Calmar, Max Drawdown)
- Benchmark Comparison (Alpha, Beta, Information Ratio)
- Attribution Analysis (Contribution by holding)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging

from app.utils.data_loader import load_stock_prices, calculate_returns
from app.utils.portfolio_math import (
    sharpe_ratio, sortino_ratio, max_drawdown, calmar_ratio,
    calculate_beta, calculate_alpha, information_ratio,
    annualize_return, annualize_volatility
)

logger = logging.getLogger(__name__)


async def performance_analyzer(
    positions: Dict[str, Dict[str, float]],
    transactions: Optional[List[Dict]] = None,
    benchmark: str = "SPY",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    risk_free_rate: float = 0.03
) -> Dict[str, Any]:
    """
    Analyze portfolio performance metrics and attribution.

    Args:
        positions: Current holdings
            {
                "AAPL": {"shares": 100, "avg_cost": 150, "current_price": 185},
                "MSFT": {"shares": 50, "avg_cost": 300, "current_price": 420}
            }
        transactions: Historical trades (optional)
            [
                {"date": "2024-01-01", "ticker": "AAPL", "shares": 100, "price": 150, "action": "buy"},
                ...
            ]
        benchmark: Benchmark ticker (default: SPY for S&P 500)
        start_date: Analysis start date (default: 1 year ago)
        end_date: Analysis end date (default: today)
        risk_free_rate: Risk-free rate (default: 3%)

    Returns:
        {
            "returns": {
                "total_return": 0.25,
                "annualized_return": 0.18,
                "ytd_return": 0.12,
                "mtd_return": 0.03
            },
            "risk_metrics": {
                "volatility": 0.22,
                "sharpe_ratio": 0.68,
                "sortino_ratio": 0.95,
                "max_drawdown": -0.15,
                "calmar_ratio": 1.20,
                "beta": 0.85,
                "alpha": 0.03
            },
            "benchmark_comparison": {
                "benchmark_return": 0.20,
                "excess_return": 0.05,
                "tracking_error": 0.08,
                "information_ratio": 0.625
            },
            "attribution": {
                "AAPL": 0.08,
                "MSFT": 0.10,
                ...
            },
            "interpretation": "..."
        }

    Example:
        >>> result = await performance_analyzer(
        ...     positions={"AAPL": {"shares": 100, "avg_cost": 150}},
        ...     benchmark="SPY"
        ... )
    """
    try:
        logger.info(f"Analyzing performance for {len(positions)} positions")

        # Set default dates
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        # Get all tickers
        tickers = list(positions.keys())

        # Load price data for portfolio and benchmark
        all_tickers = tickers + [benchmark]
        prices = load_stock_prices(all_tickers, start_date, end_date)

        if len(prices) < 30:
            raise ValueError(f"Insufficient data: only {len(prices)} days")

        # Calculate portfolio returns
        portfolio_returns = _calculate_portfolio_returns(
            positions, prices, tickers
        )

        # Benchmark returns (use first stock if benchmark not available)
        if benchmark in prices.columns:
            benchmark_returns = calculate_returns(prices[[benchmark]], method="log")[benchmark]
        else:
            logger.warning(f"Benchmark {benchmark} not available, using first stock as proxy")
            benchmark_returns = calculate_returns(prices[[tickers[0]]], method="log")[tickers[0]]

        # Calculate return metrics
        returns_metrics = _calculate_return_metrics(
            portfolio_returns, start_date, end_date
        )

        # Calculate risk metrics
        risk_metrics = _calculate_risk_metrics(
            portfolio_returns, benchmark_returns, risk_free_rate
        )

        # Benchmark comparison
        benchmark_comparison = _calculate_benchmark_comparison(
            portfolio_returns, benchmark_returns, benchmark
        )

        # Attribution analysis
        attribution = _calculate_attribution(
            positions, prices, tickers, start_date, end_date
        )

        # Interpretation
        interpretation = _generate_interpretation(
            returns_metrics, risk_metrics, benchmark_comparison, attribution
        )

        return {
            "returns": returns_metrics,
            "risk_metrics": risk_metrics,
            "benchmark_comparison": benchmark_comparison,
            "attribution": attribution,
            "metadata": {
                "num_positions": len(positions),
                "start_date": start_date,
                "end_date": end_date,
                "period_days": len(prices),
                "benchmark": benchmark
            },
            "interpretation": interpretation
        }

    except Exception as e:
        logger.error(f"Performance analysis failed: {str(e)}")
        return {
            "error": str(e),
            "positions": list(positions.keys())
        }


def _calculate_portfolio_returns(
    positions: Dict[str, Dict],
    prices: pd.DataFrame,
    tickers: List[str]
) -> pd.Series:
    """
    Calculate portfolio returns based on holdings.
    """
    # Calculate weights from current positions
    total_value = sum([pos.get("shares", 0) * pos.get("current_price", prices[ticker].iloc[-1])
                       for ticker, pos in positions.items() if ticker in prices.columns])

    weights = {}
    for ticker in tickers:
        if ticker not in prices.columns:
            continue
        pos = positions[ticker]
        shares = pos.get("shares", 0)
        current_price = pos.get("current_price", prices[ticker].iloc[-1])
        value = shares * current_price
        weights[ticker] = value / total_value if total_value > 0 else 0

    # Calculate individual returns
    returns_df = calculate_returns(prices[tickers], method="log")

    # Weighted portfolio returns
    portfolio_returns = pd.Series(0.0, index=returns_df.index)
    for ticker in tickers:
        if ticker in returns_df.columns and ticker in weights:
            portfolio_returns += returns_df[ticker] * weights[ticker]

    return portfolio_returns


def _calculate_return_metrics(
    returns: pd.Series,
    start_date: str,
    end_date: str
) -> Dict[str, float]:
    """
    Calculate various return metrics.
    """
    # Total return
    cumulative_return = (1 + returns).prod() - 1

    # Annualized return
    days = len(returns)
    years = days / 252
    annualized = (1 + cumulative_return) ** (1 / years) - 1 if years > 0 else 0

    # YTD return
    ytd_start = pd.Timestamp(datetime.now().year, 1, 1, tz='UTC')
    ytd_returns = returns[returns.index >= ytd_start]
    ytd_return = (1 + ytd_returns).prod() - 1 if len(ytd_returns) > 0 else 0

    # MTD return
    mtd_start = pd.Timestamp(datetime.now().year, datetime.now().month, 1, tz='UTC')
    mtd_returns = returns[returns.index >= mtd_start]
    mtd_return = (1 + mtd_returns).prod() - 1 if len(mtd_returns) > 0 else 0

    return {
        "total_return": round(cumulative_return, 4),
        "annualized_return": round(annualized, 4),
        "ytd_return": round(ytd_return, 4),
        "mtd_return": round(mtd_return, 4),
        "period_days": days
    }


def _calculate_risk_metrics(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float
) -> Dict[str, float]:
    """
    Calculate risk-adjusted performance metrics.
    """
    # Volatility
    volatility = portfolio_returns.std() * np.sqrt(252)

    # Sharpe ratio
    sharpe = sharpe_ratio(
        portfolio_returns.mean() * 252,
        volatility,
        risk_free_rate
    )

    # Sortino ratio
    sortino = sortino_ratio(portfolio_returns, risk_free_rate)

    # Max drawdown
    mdd = max_drawdown(portfolio_returns)

    # Calmar ratio
    calmar = calmar_ratio(portfolio_returns)

    # Beta and Alpha
    beta = calculate_beta(portfolio_returns, benchmark_returns)
    alpha = calculate_alpha(portfolio_returns, benchmark_returns, risk_free_rate)

    return {
        "volatility": round(volatility, 4),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "max_drawdown": round(mdd, 4),
        "calmar_ratio": round(calmar, 2),
        "beta": round(beta, 2),
        "alpha": round(alpha, 4)
    }


def _calculate_benchmark_comparison(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    benchmark_ticker: str
) -> Dict[str, Any]:
    """
    Compare portfolio performance to benchmark.
    """
    # Benchmark total return
    benchmark_total = (1 + benchmark_returns).prod() - 1

    # Portfolio total return
    portfolio_total = (1 + portfolio_returns).prod() - 1

    # Excess return
    excess = portfolio_total - benchmark_total

    # Tracking error
    excess_returns = portfolio_returns - benchmark_returns
    tracking_error = excess_returns.std() * np.sqrt(252)

    # Information ratio
    info_ratio = information_ratio(portfolio_returns, benchmark_returns)

    return {
        "benchmark": benchmark_ticker,
        "benchmark_return": round(benchmark_total, 4),
        "portfolio_return": round(portfolio_total, 4),
        "excess_return": round(excess, 4),
        "tracking_error": round(tracking_error, 4),
        "information_ratio": round(info_ratio, 2)
    }


def _calculate_attribution(
    positions: Dict[str, Dict],
    prices: pd.DataFrame,
    tickers: List[str],
    start_date: str,
    end_date: str
) -> Dict[str, float]:
    """
    Calculate contribution of each position to total return.
    """
    attribution = {}

    # Calculate total portfolio value
    total_value = sum([pos.get("shares", 0) * pos.get("current_price", prices[ticker].iloc[-1])
                       for ticker, pos in positions.items() if ticker in prices.columns])

    for ticker in tickers:
        if ticker not in prices.columns:
            continue

        pos = positions[ticker]
        shares = pos.get("shares", 0)

        # Calculate return for this stock
        start_price = prices[ticker].iloc[0]
        end_price = prices[ticker].iloc[-1]
        stock_return = (end_price - start_price) / start_price

        # Weight
        current_value = shares * end_price
        weight = current_value / total_value if total_value > 0 else 0

        # Contribution = weight * stock_return
        contribution = weight * stock_return

        attribution[ticker] = round(contribution, 4)

    return attribution


def _generate_interpretation(
    returns_metrics: Dict,
    risk_metrics: Dict,
    benchmark_comparison: Dict,
    attribution: Dict
) -> str:
    """
    Generate human-readable interpretation.
    """
    total_ret = returns_metrics["total_return"]
    ann_ret = returns_metrics["annualized_return"]
    sharpe = risk_metrics["sharpe_ratio"]
    mdd = risk_metrics["max_drawdown"]
    excess_ret = benchmark_comparison["excess_return"]
    benchmark = benchmark_comparison["benchmark"]

    # Performance assessment
    if sharpe > 2.0:
        perf_level = "exceptional"
    elif sharpe > 1.0:
        perf_level = "very good"
    elif sharpe > 0.5:
        perf_level = "good"
    else:
        perf_level = "modest"

    # Top contributor
    if attribution:
        top_contributor = max(attribution.items(), key=lambda x: x[1])
        top_name, top_contrib = top_contributor
    else:
        top_name, top_contrib = "N/A", 0

    interpretation = (
        f"Portfolio achieved {total_ret:.1%} total return ({ann_ret:.1%} annualized) "
        f"with {perf_level} risk-adjusted performance (Sharpe: {sharpe:.2f}). "
    )

    if excess_ret > 0:
        interpretation += f"Outperformed {benchmark} by {excess_ret:.1%}. "
    elif excess_ret < 0:
        interpretation += f"Underperformed {benchmark} by {abs(excess_ret):.1%}. "
    else:
        interpretation += f"Matched {benchmark} performance. "

    interpretation += (
        f"Maximum drawdown: {mdd:.1%}. "
        f"Top contributor: {top_name} ({top_contrib:.1%}). "
    )

    # Risk assessment
    beta = risk_metrics["beta"]
    if beta > 1.2:
        interpretation += "Portfolio is significantly more volatile than market (high beta). "
    elif beta < 0.8:
        interpretation += "Portfolio is less volatile than market (low beta). "

    return interpretation


# Example usage
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test():
        # Test: Performance analysis
        positions = {
            "AAPL": {"shares": 100, "avg_cost": 150, "current_price": 185},
            "MSFT": {"shares": 50, "avg_cost": 300, "current_price": 420},
            "GOOGL": {"shares": 80, "avg_cost": 120, "current_price": 150}
        }

        result = await performance_analyzer(
            positions=positions,
            benchmark="SPY",
            start_date="2024-01-01"
        )

        print("\n=== Performance Analysis Test ===")
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"\nReturns:")
            for k, v in result['returns'].items():
                if 'days' not in k:
                    print(f"  {k}: {v:.2%}")

            print(f"\nRisk Metrics:")
            for k, v in result['risk_metrics'].items():
                print(f"  {k}: {v:.2f}" if 'ratio' in k or k == 'beta' else f"  {k}: {v:.2%}")

            print(f"\nBenchmark Comparison:")
            for k, v in result['benchmark_comparison'].items():
                if k != 'benchmark':
                    print(f"  {k}: {v:.2%}" if isinstance(v, float) and 'ratio' not in k else f"  {k}: {v}")

            print(f"\nAttribution:")
            for ticker, contrib in result['attribution'].items():
                print(f"  {ticker}: {contrib:.2%}")

            print(f"\nInterpretation:\n{result['interpretation']}")

    asyncio.run(test())
