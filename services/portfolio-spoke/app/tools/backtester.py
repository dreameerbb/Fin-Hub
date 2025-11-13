"""
Backtester - Simulate portfolio strategies on historical data

Supports multiple strategies:
- Momentum: Buy top N stocks by momentum
- Mean Reversion: Buy oversold, sell overbought
- Equal Weight: Equal allocation rebalanced periodically
- Custom: User-defined strategy function

Provides comprehensive backtest results with equity curve and metrics.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
import logging

# Internal utilities
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.data_loader import load_stock_prices, calculate_returns, get_available_tickers
from utils.portfolio_math import (
    sharpe_ratio, sortino_ratio, max_drawdown, calmar_ratio,
    annualize_return, annualize_volatility
)

logger = logging.getLogger(__name__)


async def backtester(
    strategy: str = "momentum",
    universe: str = "sp500",
    custom_tickers: Optional[List[str]] = None,
    start_date: str = "2020-01-01",
    end_date: Optional[str] = None,
    initial_capital: float = 100000,
    rebalance_frequency: str = "monthly",
    parameters: Optional[Dict] = None,
    transaction_cost: float = 0.001,
    slippage: float = 0.0005
) -> Dict[str, Any]:
    """
    Backtest portfolio strategies on historical data.

    Args:
        strategy: Strategy name
            - 'momentum': Buy top N stocks by momentum
            - 'mean_reversion': Buy oversold, sell overbought
            - 'equal_weight': Equal weight all stocks
            - 'custom': User-defined (requires custom function)
        universe: Stock universe
            - 'sp500': S&P 500 stocks (default)
            - 'custom': Custom ticker list
        custom_tickers: Custom ticker list (if universe='custom')
        start_date: Backtest start date
        end_date: Backtest end date (default: today)
        initial_capital: Starting capital
        rebalance_frequency: Rebalancing frequency
            - 'daily', 'weekly', 'monthly', 'quarterly'
        parameters: Strategy-specific parameters
            - momentum: {'lookback': 60, 'top_n': 20}
            - mean_reversion: {'lookback': 20, 'oversold': 30, 'overbought': 70}
        transaction_cost: Transaction cost as percentage (default: 0.1%)
        slippage: Slippage as percentage (default: 0.05%)

    Returns:
        {
            "performance": {
                "total_return": 0.85,
                "annualized_return": 0.16,
                "sharpe_ratio": 1.25,
                "max_drawdown": -0.22,
                "win_rate": 0.58
            },
            "equity_curve": [...],
            "trades": [...],
            "monthly_returns": [...],
            "metrics_by_year": {...},
            "benchmark_comparison": {...},
            "interpretation": "..."
        }

    Example:
        >>> result = await backtester(
        ...     strategy="momentum",
        ...     universe="sp500",
        ...     start_date="2020-01-01",
        ...     parameters={"lookback": 60, "top_n": 20}
        ... )
    """
    try:
        logger.info(f"Backtesting {strategy} strategy from {start_date}")

        # Set default end date
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # Get ticker universe
        if universe == "sp500":
            tickers = get_available_tickers()
            # Limit to 100 stocks for performance
            tickers = tickers[:100]
        elif universe == "custom" and custom_tickers:
            tickers = custom_tickers
        else:
            raise ValueError("Invalid universe or missing custom_tickers")

        # Load price data
        prices = load_stock_prices(tickers, start_date, end_date)

        if len(prices) < 60:
            raise ValueError(f"Insufficient data: only {len(prices)} days")

        # Get benchmark (S&P 500 equal weight as proxy)
        benchmark_returns = _calculate_benchmark_returns(prices)

        # Run backtest
        if strategy == "momentum":
            equity_curve, trades = _backtest_momentum(
                prices, initial_capital, rebalance_frequency,
                parameters or {}, transaction_cost, slippage
            )
        elif strategy == "mean_reversion":
            equity_curve, trades = _backtest_mean_reversion(
                prices, initial_capital, rebalance_frequency,
                parameters or {}, transaction_cost, slippage
            )
        elif strategy == "equal_weight":
            equity_curve, trades = _backtest_equal_weight(
                prices, initial_capital, rebalance_frequency,
                transaction_cost, slippage
            )
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Calculate performance metrics
        performance = _calculate_performance_metrics(equity_curve, initial_capital)

        # Monthly returns
        monthly_returns = _calculate_monthly_returns(equity_curve)

        # Metrics by year
        metrics_by_year = _calculate_yearly_metrics(equity_curve)

        # Benchmark comparison
        benchmark_comparison = _calculate_benchmark_comparison(
            equity_curve, benchmark_returns, initial_capital
        )

        # Interpretation
        interpretation = _generate_interpretation(
            performance, benchmark_comparison, strategy, len(trades)
        )

        return {
            "performance": performance,
            "equity_curve": {str(k): float(v) for k, v in equity_curve.items()},
            "trades": trades[:100],  # Limit to first 100 trades for output
            "monthly_returns": monthly_returns,
            "metrics_by_year": metrics_by_year,
            "benchmark_comparison": benchmark_comparison,
            "metadata": {
                "strategy": strategy,
                "universe": universe,
                "num_tickers": len(tickers),
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": float(initial_capital),
                "rebalance_frequency": rebalance_frequency,
                "total_trades": len(trades)
            },
            "interpretation": interpretation
        }

    except Exception as e:
        logger.error(f"Backtesting failed: {str(e)}")
        return {
            "error": str(e),
            "strategy": strategy
        }


def _backtest_momentum(
    prices: pd.DataFrame,
    initial_capital: float,
    rebalance_freq: str,
    parameters: Dict,
    transaction_cost: float,
    slippage: float
) -> Tuple[pd.Series, List[Dict]]:
    """
    Momentum strategy: Buy top N stocks by past returns.
    """
    lookback = parameters.get("lookback", 60)
    top_n = parameters.get("top_n", 20)

    # Rebalance dates
    rebalance_dates = _get_rebalance_dates(prices.index, rebalance_freq)

    # Initialize
    equity = pd.Series(initial_capital, index=prices.index)
    cash = initial_capital
    holdings = {}
    trades = []

    for i, date in enumerate(prices.index):
        # Rebalance on schedule
        if date in rebalance_dates and i >= lookback:
            # Calculate momentum (past returns)
            past_prices = prices.iloc[i-lookback:i]
            momentum = (prices.loc[date] / past_prices.iloc[0] - 1).dropna()
            momentum = momentum.sort_values(ascending=False)

            # Select top N stocks
            selected = momentum.head(top_n).index.tolist()

            # Equal weight
            target_value_per_stock = equity.iloc[i-1] / top_n

            # Sell holdings not in selected
            for ticker in list(holdings.keys()):
                if ticker not in selected:
                    shares = holdings[ticker]
                    price = prices.loc[date, ticker] * (1 - slippage)
                    proceeds = shares * price
                    cost = proceeds * transaction_cost
                    cash += proceeds - cost
                    trades.append({
                        "date": str(date),
                        "ticker": ticker,
                        "action": "sell",
                        "shares": shares,
                        "price": float(price),
                        "cost": float(cost)
                    })
                    del holdings[ticker]

            # Buy selected stocks
            for ticker in selected:
                if ticker not in holdings:
                    price = prices.loc[date, ticker] * (1 + slippage)
                    shares = int(target_value_per_stock / price)
                    if shares > 0:
                        cost_with_fees = shares * price * (1 + transaction_cost)
                        if cost_with_fees <= cash:
                            cash -= cost_with_fees
                            holdings[ticker] = shares
                            trades.append({
                                "date": str(date),
                                "ticker": ticker,
                                "action": "buy",
                                "shares": shares,
                                "price": float(price),
                                "cost": float(cost_with_fees - shares * price)
                            })

        # Update equity value
        holdings_value = sum([shares * prices.loc[date, ticker]
                              for ticker, shares in holdings.items()
                              if ticker in prices.columns])
        equity.loc[date] = cash + holdings_value

    return equity, trades


def _backtest_mean_reversion(
    prices: pd.DataFrame,
    initial_capital: float,
    rebalance_freq: str,
    parameters: Dict,
    transaction_cost: float,
    slippage: float
) -> Tuple[pd.Series, List[Dict]]:
    """
    Mean reversion strategy: Buy oversold, sell overbought.
    """
    lookback = parameters.get("lookback", 20)
    oversold = parameters.get("oversold_pct", 0.30)  # Bottom 30%
    overbought = parameters.get("overbought_pct", 0.70)  # Top 30%

    # Rebalance dates
    rebalance_dates = _get_rebalance_dates(prices.index, rebalance_freq)

    # Initialize
    equity = pd.Series(initial_capital, index=prices.index)
    cash = initial_capital
    holdings = {}
    trades = []

    for i, date in enumerate(prices.index):
        if date in rebalance_dates and i >= lookback:
            # Calculate z-scores
            past_prices = prices.iloc[i-lookback:i]
            current_prices = prices.loc[date]

            mean_prices = past_prices.mean()
            std_prices = past_prices.std()

            z_scores = (current_prices - mean_prices) / std_prices
            z_scores = z_scores.dropna()

            # Oversold (buy): bottom percentile
            oversold_threshold = z_scores.quantile(oversold)
            oversold_stocks = z_scores[z_scores <= oversold_threshold].index.tolist()

            # Target allocation
            if len(oversold_stocks) > 0:
                target_value_per_stock = equity.iloc[i-1] / len(oversold_stocks)

                # Sell all current holdings
                for ticker in list(holdings.keys()):
                    shares = holdings[ticker]
                    price = prices.loc[date, ticker] * (1 - slippage)
                    proceeds = shares * price
                    cost = proceeds * transaction_cost
                    cash += proceeds - cost
                    trades.append({
                        "date": str(date),
                        "ticker": ticker,
                        "action": "sell",
                        "shares": shares,
                        "price": float(price),
                        "cost": float(cost)
                    })
                holdings = {}

                # Buy oversold stocks
                for ticker in oversold_stocks:
                    price = prices.loc[date, ticker] * (1 + slippage)
                    shares = int(target_value_per_stock / price)
                    if shares > 0:
                        cost_with_fees = shares * price * (1 + transaction_cost)
                        if cost_with_fees <= cash:
                            cash -= cost_with_fees
                            holdings[ticker] = shares
                            trades.append({
                                "date": str(date),
                                "ticker": ticker,
                                "action": "buy",
                                "shares": shares,
                                "price": float(price),
                                "cost": float(cost_with_fees - shares * price)
                            })

        # Update equity
        holdings_value = sum([shares * prices.loc[date, ticker]
                              for ticker, shares in holdings.items()
                              if ticker in prices.columns])
        equity.loc[date] = cash + holdings_value

    return equity, trades


def _backtest_equal_weight(
    prices: pd.DataFrame,
    initial_capital: float,
    rebalance_freq: str,
    transaction_cost: float,
    slippage: float
) -> Tuple[pd.Series, List[Dict]]:
    """
    Equal weight strategy: Allocate equally to all stocks.
    """
    # Limit to 30 stocks for equal weight
    tickers = prices.columns[:30].tolist()
    prices = prices[tickers]

    # Rebalance dates
    rebalance_dates = _get_rebalance_dates(prices.index, rebalance_freq)

    # Initialize
    equity = pd.Series(initial_capital, index=prices.index)
    cash = initial_capital
    holdings = {}
    trades = []

    target_value_per_stock = initial_capital / len(tickers)

    for i, date in enumerate(prices.index):
        if date in rebalance_dates:
            # Sell all and rebalance
            for ticker in list(holdings.keys()):
                shares = holdings[ticker]
                price = prices.loc[date, ticker] * (1 - slippage)
                proceeds = shares * price
                cost = proceeds * transaction_cost
                cash += proceeds - cost
                trades.append({
                    "date": str(date),
                    "ticker": ticker,
                    "action": "sell",
                    "shares": shares,
                    "price": float(price),
                    "cost": float(cost)
                })
            holdings = {}

            # Buy equal weight
            for ticker in tickers:
                price = prices.loc[date, ticker] * (1 + slippage)
                shares = int(target_value_per_stock / price)
                if shares > 0:
                    cost_with_fees = shares * price * (1 + transaction_cost)
                    if cost_with_fees <= cash:
                        cash -= cost_with_fees
                        holdings[ticker] = shares
                        trades.append({
                            "date": str(date),
                            "ticker": ticker,
                            "action": "buy",
                            "shares": shares,
                            "price": float(price),
                            "cost": float(cost_with_fees - shares * price)
                        })

        # Update equity
        holdings_value = sum([shares * prices.loc[date, ticker]
                              for ticker, shares in holdings.items()])
        equity.loc[date] = cash + holdings_value

    return equity, trades


def _get_rebalance_dates(dates: pd.DatetimeIndex, frequency: str) -> List:
    """
    Get rebalancing dates based on frequency.
    """
    if frequency == "daily":
        return dates.tolist()
    elif frequency == "weekly":
        return [d for d in dates if d.dayofweek == 0]  # Monday
    elif frequency == "monthly":
        return [d for i, d in enumerate(dates) if i == 0 or d.month != dates[i-1].month]
    elif frequency == "quarterly":
        return [d for i, d in enumerate(dates)
                if i == 0 or (d.month - 1) // 3 != (dates[i-1].month - 1) // 3]
    else:
        return [dates[0], dates[-1]]


def _calculate_performance_metrics(equity: pd.Series, initial_capital: float) -> Dict:
    """
    Calculate backtest performance metrics.
    """
    # Returns
    returns = equity.pct_change().dropna()

    # Total return
    total_return = (equity.iloc[-1] - initial_capital) / initial_capital

    # Annualized return
    days = len(equity)
    years = days / 252
    ann_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

    # Sharpe ratio
    sharpe = sharpe_ratio(ann_return, returns.std() * np.sqrt(252), 0.03)

    # Sortino ratio
    sortino = sortino_ratio(returns, 0.03)

    # Max drawdown
    mdd = max_drawdown(returns)

    # Calmar ratio
    calmar = calmar_ratio(returns)

    # Win rate
    winning_days = (returns > 0).sum()
    win_rate = winning_days / len(returns) if len(returns) > 0 else 0

    return {
        "total_return": round(total_return, 4),
        "annualized_return": round(ann_return, 4),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "max_drawdown": round(mdd, 4),
        "calmar_ratio": round(calmar, 2),
        "win_rate": round(win_rate, 4),
        "volatility": round(returns.std() * np.sqrt(252), 4)
    }


def _calculate_monthly_returns(equity: pd.Series) -> List[Dict]:
    """
    Calculate monthly returns.
    """
    monthly = equity.resample('ME').last()
    monthly_ret = monthly.pct_change().dropna()

    return [
        {
            "month": str(date.strftime("%Y-%m")),
            "return": round(ret, 4)
        }
        for date, ret in monthly_ret.items()
    ]


def _calculate_yearly_metrics(equity: pd.Series) -> Dict:
    """
    Calculate metrics by year.
    """
    yearly_metrics = {}

    for year in equity.index.year.unique():
        year_data = equity[equity.index.year == year]
        if len(year_data) > 1:
            year_return = (year_data.iloc[-1] - year_data.iloc[0]) / year_data.iloc[0]
            yearly_metrics[str(year)] = {
                "return": round(year_return, 4)
            }

    return yearly_metrics


def _calculate_benchmark_returns(prices: pd.DataFrame) -> pd.Series:
    """
    Calculate benchmark returns (equal-weight portfolio).
    """
    returns = calculate_returns(prices, method="log")
    # Equal weight all stocks
    benchmark_returns = returns.mean(axis=1)
    return benchmark_returns


def _calculate_benchmark_comparison(
    equity: pd.Series,
    benchmark_returns: pd.Series,
    initial_capital: float
) -> Dict:
    """
    Compare strategy to benchmark.
    """
    # Strategy return
    strategy_return = (equity.iloc[-1] - initial_capital) / initial_capital

    # Benchmark return (buy and hold)
    benchmark_equity = initial_capital * (1 + benchmark_returns).cumprod()
    benchmark_return = (benchmark_equity.iloc[-1] - initial_capital) / initial_capital

    # Outperformance
    outperformance = strategy_return - benchmark_return

    return {
        "strategy_return": round(strategy_return, 4),
        "benchmark_return": round(benchmark_return, 4),
        "outperformance": round(outperformance, 4)
    }


def _generate_interpretation(
    performance: Dict,
    benchmark_comparison: Dict,
    strategy: str,
    num_trades: int
) -> str:
    """
    Generate human-readable interpretation.
    """
    total_ret = performance["total_return"]
    ann_ret = performance["annualized_return"]
    sharpe = performance["sharpe_ratio"]
    mdd = performance["max_drawdown"]
    outperf = benchmark_comparison["outperformance"]

    interpretation = (
        f"{strategy.title()} strategy achieved {total_ret:.1%} total return "
        f"({ann_ret:.1%} annualized) over the backtest period. "
    )

    if sharpe > 1.5:
        interpretation += f"Excellent risk-adjusted performance (Sharpe: {sharpe:.2f}). "
    elif sharpe > 1.0:
        interpretation += f"Good risk-adjusted performance (Sharpe: {sharpe:.2f}). "
    else:
        interpretation += f"Modest risk-adjusted performance (Sharpe: {sharpe:.2f}). "

    if outperf > 0:
        interpretation += f"Outperformed buy-and-hold benchmark by {outperf:.1%}. "
    else:
        interpretation += f"Underperformed buy-and-hold benchmark by {abs(outperf):.1%}. "

    interpretation += (
        f"Maximum drawdown: {mdd:.1%}. "
        f"Executed {num_trades} trades during backtest. "
    )

    return interpretation


# Example usage
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test():
        # Test: Momentum strategy
        result = await backtester(
            strategy="momentum",
            universe="sp500",
            start_date="2023-01-01",
            end_date="2024-01-01",
            initial_capital=100000,
            rebalance_frequency="monthly",
            parameters={"lookback": 60, "top_n": 20}
        )

        print("\n=== Backtest Test ===")
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"\nPerformance:")
            for k, v in result['performance'].items():
                if 'rate' in k:
                    print(f"  {k}: {v:.2%}")
                elif 'ratio' in k:
                    print(f"  {k}: {v:.2f}")
                else:
                    print(f"  {k}: {v:.2%}")

            print(f"\nBenchmark Comparison:")
            for k, v in result['benchmark_comparison'].items():
                print(f"  {k}: {v:.2%}")

            print(f"\nInterpretation:\n{result['interpretation']}")

    asyncio.run(test())
