"""
Factor Analyzer - Analyze factor exposures and attribution

Analyzes portfolio exposure to common equity factors:
- Market (Beta)
- Size (SMB - Small Minus Big)
- Value (HML - High Minus Low)
- Momentum (MOM - Winners Minus Losers)
- Quality (Custom quality score)

Uses regression analysis to decompose returns into factor contributions.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from scipy import stats

from app.utils.data_loader import load_stock_prices, calculate_returns
from app.utils.portfolio_math import calculate_beta, calculate_alpha

logger = logging.getLogger(__name__)


async def factor_analyzer(
    positions: Dict[str, float],
    factors: List[str] = ["market", "size", "value", "momentum", "quality"],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    benchmark: str = "SPY"
) -> Dict[str, Any]:
    """
    Analyze factor exposures and attribution.

    Args:
        positions: Portfolio weights
            {"AAPL": 0.30, "MSFT": 0.40, "GOOGL": 0.30}
        factors: Factors to analyze
            - 'market': Market beta
            - 'size': Small cap vs large cap
            - 'value': Value vs growth
            - 'momentum': Price momentum
            - 'quality': Quality metrics (ROE, profitability)
        start_date: Analysis start date (default: 1 year ago)
        end_date: Analysis end date (default: today)
        benchmark: Market benchmark (default: SPY)

    Returns:
        {
            "factor_exposures": {
                "market": 0.95,
                "size": -0.15,
                "value": -0.08,
                "momentum": 0.25,
                "quality": 0.18
            },
            "factor_returns": {
                "market": 0.12,
                "size": -0.02,
                "value": -0.01,
                "momentum": 0.04,
                "quality": 0.03,
                "alpha": 0.02
            },
            "r_squared": 0.88,
            "interpretation": "..."
        }

    Example:
        >>> result = await factor_analyzer(
        ...     positions={"AAPL": 0.35, "MSFT": 0.40, "GOOGL": 0.25},
        ...     factors=["market", "size", "value", "momentum"]
        ... )
    """
    try:
        logger.info(f"Analyzing {len(factors)} factors for {len(positions)} positions")

        # Set default dates
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        # Get tickers
        tickers = list(positions.keys())

        # Load price data
        all_tickers = tickers + [benchmark]
        prices = load_stock_prices(all_tickers, start_date, end_date)

        if len(prices) < 60:
            raise ValueError(f"Insufficient data: only {len(prices)} days")

        # Calculate portfolio returns
        returns_df = calculate_returns(prices, method="log")
        portfolio_returns = _calculate_portfolio_returns(positions, returns_df, tickers)

        # Calculate factor values
        factor_data = _calculate_factors(prices, returns_df, tickers, factors, benchmark)

        # Run factor regression
        factor_exposures, factor_returns, r_squared, alpha = _run_factor_regression(
            portfolio_returns, factor_data
        )

        # Interpretation
        interpretation = _generate_interpretation(
            factor_exposures, factor_returns, r_squared, alpha, factors
        )

        return {
            "factor_exposures": factor_exposures,
            "factor_returns": factor_returns,
            "r_squared": round(r_squared, 4),
            "alpha": round(alpha, 4),
            "metadata": {
                "num_positions": len(positions),
                "factors_analyzed": factors,
                "start_date": start_date,
                "end_date": end_date,
                "period_days": len(prices)
            },
            "interpretation": interpretation
        }

    except Exception as e:
        logger.error(f"Factor analysis failed: {str(e)}")
        return {
            "error": str(e),
            "positions": list(positions.keys()),
            "factors": factors
        }


def _calculate_portfolio_returns(
    positions: Dict[str, float],
    returns_df: pd.DataFrame,
    tickers: List[str]
) -> pd.Series:
    """
    Calculate weighted portfolio returns.
    """
    portfolio_returns = pd.Series(0.0, index=returns_df.index)

    for ticker in tickers:
        if ticker in returns_df.columns and ticker in positions:
            weight = positions[ticker]
            portfolio_returns += returns_df[ticker] * weight

    return portfolio_returns


def _calculate_factors(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    tickers: List[str],
    factor_names: List[str],
    benchmark: str
) -> pd.DataFrame:
    """
    Calculate factor values (simplified version using available data).

    In production, would use Fama-French factor data from:
    https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
    """
    factor_data = pd.DataFrame(index=returns.index)

    # Market factor (benchmark returns)
    if "market" in factor_names:
        factor_data["market"] = returns[benchmark] if benchmark in returns.columns else 0

    # Size factor (SMB - Small Minus Big)
    if "size" in factor_names:
        # Proxy: Calculate market cap ranks
        # Smaller stocks (bottom 50%) - larger stocks (top 50%)
        latest_prices = prices.iloc[-1]
        median_price = latest_prices.median()

        small_stocks = [t for t in tickers if t in prices.columns and prices[t].iloc[-1] < median_price]
        big_stocks = [t for t in tickers if t in prices.columns and prices[t].iloc[-1] >= median_price]

        if small_stocks and big_stocks:
            small_returns = returns[small_stocks].mean(axis=1)
            big_returns = returns[big_stocks].mean(axis=1)
            factor_data["size"] = small_returns - big_returns
        else:
            factor_data["size"] = 0

    # Value factor (HML - High Minus Low)
    if "value" in factor_names:
        # Proxy: Use price volatility as inverse proxy for value
        # (Lower volatility = more stable = value-like)
        rolling_vol = returns[tickers].rolling(60).std()
        latest_vol = rolling_vol.iloc[-1]

        if len(latest_vol) > 0:
            median_vol = latest_vol.median()
            value_stocks = [t for t in tickers if t in latest_vol.index and latest_vol[t] < median_vol]
            growth_stocks = [t for t in tickers if t in latest_vol.index and latest_vol[t] >= median_vol]

            if value_stocks and growth_stocks:
                value_returns = returns[value_stocks].mean(axis=1)
                growth_returns = returns[growth_stocks].mean(axis=1)
                factor_data["value"] = value_returns - growth_returns
            else:
                factor_data["value"] = 0
        else:
            factor_data["value"] = 0

    # Momentum factor (MOM - Winners Minus Losers)
    if "momentum" in factor_names:
        # 12-month momentum
        lookback = min(252, len(returns))
        if lookback >= 60:
            past_returns = returns[tickers].iloc[-lookback:]
            cumulative = (1 + past_returns).prod() - 1

            if len(cumulative) > 0:
                median_ret = cumulative.median()
                winners = [t for t in tickers if t in cumulative.index and cumulative[t] > median_ret]
                losers = [t for t in tickers if t in cumulative.index and cumulative[t] <= median_ret]

                if winners and losers:
                    winner_returns = returns[winners].mean(axis=1)
                    loser_returns = returns[losers].mean(axis=1)
                    factor_data["momentum"] = winner_returns - loser_returns
                else:
                    factor_data["momentum"] = 0
            else:
                factor_data["momentum"] = 0
        else:
            factor_data["momentum"] = 0

    # Quality factor (Custom)
    if "quality" in factor_names:
        # Proxy: Use inverse volatility as quality measure
        # (Lower volatility = higher quality)
        rolling_vol = returns[tickers].rolling(60).std()

        if len(tickers) > 1:
            # High quality (low vol) - Low quality (high vol)
            inverse_vol = 1 / (rolling_vol + 1e-6)
            quality_score = inverse_vol.mean(axis=1)
            factor_data["quality"] = quality_score / quality_score.mean() - 1
        else:
            factor_data["quality"] = 0

    return factor_data.fillna(0)


def _run_factor_regression(
    portfolio_returns: pd.Series,
    factor_data: pd.DataFrame
) -> Tuple[Dict, Dict, float, float]:
    """
    Run multivariate regression: returns = alpha + beta1*F1 + beta2*F2 + ...
    """
    # Align data
    df = pd.concat([portfolio_returns, factor_data], axis=1).dropna()
    df.columns = ["returns"] + list(factor_data.columns)

    if len(df) < 30:
        raise ValueError("Insufficient data for regression")

    # Prepare X (factors) and y (returns)
    y = df["returns"].values
    X = df[factor_data.columns].values

    # Add constant for intercept (alpha)
    X_with_const = np.column_stack([np.ones(len(X)), X])

    # OLS regression
    try:
        # Beta coefficients (including alpha as first element)
        betas, residuals, rank, s = np.linalg.lstsq(X_with_const, y, rcond=None)

        alpha = betas[0]
        factor_betas = betas[1:]

        # R-squared
        y_mean = np.mean(y)
        ss_tot = np.sum((y - y_mean) ** 2)
        ss_res = np.sum((y - X_with_const @ betas) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Factor exposures (betas)
        factor_exposures = {
            factor: round(float(beta), 2)
            for factor, beta in zip(factor_data.columns, factor_betas)
        }

        # Factor returns (contribution = beta * factor_mean_return)
        factor_means = factor_data.mean() * 252  # Annualize
        factor_returns = {
            factor: round(float(beta * factor_means[factor]), 4)
            for factor, beta in zip(factor_data.columns, factor_betas)
        }
        factor_returns["alpha"] = round(float(alpha * 252), 4)  # Annualized alpha

        return factor_exposures, factor_returns, r_squared, alpha * 252

    except Exception as e:
        logger.error(f"Regression failed: {e}")
        # Return zeros
        factor_exposures = {f: 0.0 for f in factor_data.columns}
        factor_returns = {f: 0.0 for f in factor_data.columns}
        factor_returns["alpha"] = 0.0
        return factor_exposures, factor_returns, 0.0, 0.0


def _generate_interpretation(
    factor_exposures: Dict,
    factor_returns: Dict,
    r_squared: float,
    alpha: float,
    factors: List[str]
) -> str:
    """
    Generate human-readable interpretation.
    """
    # Identify dominant factors
    abs_exposures = {k: abs(v) for k, v in factor_exposures.items()}
    sorted_factors = sorted(abs_exposures.items(), key=lambda x: x[1], reverse=True)

    top_factor, top_exposure = sorted_factors[0] if sorted_factors else ("none", 0)
    top_sign = "positive" if factor_exposures.get(top_factor, 0) > 0 else "negative"

    interpretation = (
        f"Portfolio shows {top_sign} {top_factor} tilt (exposure: {factor_exposures.get(top_factor, 0):.2f}). "
    )

    # Factor return contributions
    top_contributor = max(factor_returns.items(), key=lambda x: abs(x[1]) if x[0] != "alpha" else 0)
    if top_contributor[0] != "alpha":
        contrib_name, contrib_val = top_contributor
        interpretation += f"Largest factor contribution: {contrib_name} ({contrib_val:.1%}). "

    # Model fit
    if r_squared > 0.85:
        interpretation += f"Excellent model fit (R²: {r_squared:.2f}). "
    elif r_squared > 0.70:
        interpretation += f"Good model fit (R²: {r_squared:.2f}). "
    else:
        interpretation += f"Moderate model fit (R²: {r_squared:.2f}). "

    # Alpha assessment
    if alpha > 0.03:
        interpretation += f"Significant positive alpha ({alpha:.1%}), indicating skill beyond factor exposures. "
    elif alpha < -0.03:
        interpretation += f"Negative alpha ({alpha:.1%}), underperforming factor-implied returns. "
    else:
        interpretation += f"Alpha close to zero ({alpha:.1%}), returns explained by factor exposures. "

    # Specific factor insights
    if "market" in factor_exposures:
        beta = factor_exposures["market"]
        if beta > 1.2:
            interpretation += "High market beta indicates above-market volatility. "
        elif beta < 0.8:
            interpretation += "Low market beta indicates below-market volatility. "

    if "size" in factor_exposures:
        size_exp = factor_exposures["size"]
        if size_exp > 0.2:
            interpretation += "Strong small-cap bias. "
        elif size_exp < -0.2:
            interpretation += "Strong large-cap bias. "

    if "value" in factor_exposures:
        value_exp = factor_exposures["value"]
        if value_exp > 0.2:
            interpretation += "Value tilt. "
        elif value_exp < -0.2:
            interpretation += "Growth tilt. "

    if "momentum" in factor_exposures:
        mom_exp = factor_exposures["momentum"]
        if mom_exp > 0.2:
            interpretation += "Strong momentum strategy. "

    return interpretation


# Example usage
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test():
        # Test: Factor analysis
        positions = {
            "AAPL": 0.30,
            "MSFT": 0.40,
            "GOOGL": 0.30
        }

        result = await factor_analyzer(
            positions=positions,
            factors=["market", "size", "value", "momentum", "quality"],
            start_date="2024-01-01"
        )

        print("\n=== Factor Analysis Test ===")
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"\nFactor Exposures:")
            for factor, exposure in result['factor_exposures'].items():
                print(f"  {factor}: {exposure:.2f}")

            print(f"\nFactor Returns (Contribution):")
            for factor, ret in result['factor_returns'].items():
                print(f"  {factor}: {ret:.2%}")

            print(f"\nModel Fit:")
            print(f"  R-squared: {result['r_squared']:.2%}")
            print(f"  Alpha: {result['alpha']:.2%}")

            print(f"\nInterpretation:\n{result['interpretation']}")

    asyncio.run(test())
