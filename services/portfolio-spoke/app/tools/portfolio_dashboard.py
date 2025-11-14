"""
Portfolio Dashboard - Comprehensive portfolio summary and health scoring

Provides a unified dashboard with:
- Portfolio Health Score (0-100)
- Key Performance Metrics
- Risk Assessment
- Rebalancing Status
- Tax Efficiency
- Recommendations
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging

# Internal utilities - use absolute imports to avoid conflicts
from app.utils.data_loader import load_stock_prices, calculate_returns
from app.utils.portfolio_math import (
    sharpe_ratio, sortino_ratio, max_drawdown,
    portfolio_return, portfolio_volatility
)

logger = logging.getLogger(__name__)


async def portfolio_dashboard(
    positions: Dict[str, Dict[str, Any]],
    target_weights: Optional[Dict[str, float]] = None,
    benchmark: str = "SPY",
    risk_tolerance: str = "moderate",
    tax_bracket: float = 0.24,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive portfolio dashboard with health scoring.

    Args:
        positions: Current holdings
            {
                "AAPL": {
                    "shares": 100,
                    "cost_basis": 150,
                    "current_price": 185,
                    "purchase_date": "2023-01-15"
                },
                ...
            }
        target_weights: Target allocation (optional)
            {"AAPL": 0.25, "MSFT": 0.30, ...}
        benchmark: Benchmark ticker (default: SPY)
        risk_tolerance: "conservative", "moderate", or "aggressive"
        tax_bracket: Tax rate for calculations
        start_date: Analysis start date (default: 1 year ago)
        end_date: Analysis end date (default: today)

    Returns:
        {
            "health_score": 85,
            "health_grade": "B+",
            "portfolio_value": 50000,
            "performance": {
                "total_return": 0.25,
                "annualized_return": 0.18,
                "ytd_return": 0.12,
                "sharpe_ratio": 0.85,
                "max_drawdown": -0.15
            },
            "risk_assessment": {
                "volatility": 0.18,
                "beta": 0.92,
                "risk_level": "Moderate",
                "var_95": -0.025
            },
            "diversification": {
                "num_positions": 10,
                "effective_assets": 8.2,
                "concentration_risk": "Low",
                "sector_concentration": {...}
            },
            "rebalancing": {
                "needed": true,
                "max_drift": 0.08,
                "drifted_positions": ["AAPL", "MSFT"]
            },
            "tax_efficiency": {
                "unrealized_gains": 5000,
                "unrealized_losses": -1000,
                "tlh_opportunities": 2,
                "potential_tax_savings": 240
            },
            "recommendations": [...],
            "alerts": [...],
            "interpretation": "..."
        }

    Example:
        >>> result = await portfolio_dashboard(
        ...     positions={"AAPL": {"shares": 100, "cost_basis": 150}},
        ...     risk_tolerance="moderate"
        ... )
    """
    try:
        logger.info(f"Generating dashboard for {len(positions)} positions")

        # Set default dates
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        current_dt = pd.to_datetime(end_date)

        # Get all tickers
        tickers = list(positions.keys())

        # Load price data
        all_tickers = tickers + [benchmark]
        prices = load_stock_prices(all_tickers, start_date, end_date)

        if len(prices) < 30:
            raise ValueError(f"Insufficient data: only {len(prices)} days")

        # Update current prices
        for ticker in tickers:
            if ticker in prices.columns and "current_price" not in positions[ticker]:
                positions[ticker]["current_price"] = float(prices[ticker].iloc[-1])

        # Calculate portfolio value
        portfolio_value = sum([
            pos.get("shares", 0) * pos.get("current_price", 0)
            for pos in positions.values()
        ])

        # Performance metrics
        performance = _calculate_performance_metrics(
            positions, prices, benchmark, start_date, end_date
        )

        # Risk assessment
        risk_assessment = _assess_risk(
            positions, prices, benchmark, risk_tolerance
        )

        # Diversification analysis
        diversification = _analyze_diversification(
            positions, prices
        )

        # Rebalancing status
        rebalancing = _check_rebalancing_status(
            positions, target_weights, prices
        )

        # Tax efficiency
        tax_efficiency = _assess_tax_efficiency(
            positions, current_dt, tax_bracket
        )

        # Calculate health score
        health_score, health_components = _calculate_health_score(
            performance, risk_assessment, diversification,
            rebalancing, tax_efficiency, risk_tolerance
        )

        # Generate recommendations
        recommendations = _generate_recommendations(
            health_components, performance, risk_assessment,
            diversification, rebalancing, tax_efficiency
        )

        # Generate alerts
        alerts = _generate_alerts(
            performance, risk_assessment, rebalancing, tax_efficiency
        )

        # Interpretation
        interpretation = _generate_interpretation(
            health_score, portfolio_value, performance,
            risk_assessment, recommendations
        )

        return {
            "health_score": health_score,
            "health_grade": _score_to_grade(health_score),
            "health_components": health_components,
            "portfolio_value": round(portfolio_value, 2),
            "performance": performance,
            "risk_assessment": risk_assessment,
            "diversification": diversification,
            "rebalancing": rebalancing,
            "tax_efficiency": tax_efficiency,
            "recommendations": recommendations,
            "alerts": alerts,
            "metadata": {
                "num_positions": len(positions),
                "benchmark": benchmark,
                "risk_tolerance": risk_tolerance,
                "start_date": start_date,
                "end_date": end_date
            },
            "interpretation": interpretation
        }

    except Exception as e:
        logger.error(f"Dashboard generation failed: {str(e)}")
        return {
            "error": str(e),
            "positions": list(positions.keys())
        }


def _calculate_performance_metrics(
    positions: Dict[str, Dict],
    prices: pd.DataFrame,
    benchmark: str,
    start_date: str,
    end_date: str
) -> Dict[str, float]:
    """
    Calculate portfolio performance metrics.
    """
    # Calculate portfolio returns
    total_value = sum([pos.get("shares", 0) * pos.get("current_price", prices[t].iloc[-1] if t in prices.columns else 0)
                       for t, pos in positions.items()])

    weights = {}
    for ticker, pos in positions.items():
        if ticker not in prices.columns:
            continue
        value = pos.get("shares", 0) * pos.get("current_price", prices[ticker].iloc[-1])
        weights[ticker] = value / total_value if total_value > 0 else 0

    # Calculate returns
    returns = calculate_returns(prices[[t for t in positions.keys() if t in prices.columns]], method="log")

    # Portfolio returns
    portfolio_returns = pd.Series(0.0, index=returns.index)
    for ticker in returns.columns:
        if ticker in weights:
            portfolio_returns += returns[ticker] * weights[ticker]

    # Total return
    cumulative_return = (1 + portfolio_returns).prod() - 1

    # Annualized return
    years = len(portfolio_returns) / 252
    annualized = (1 + cumulative_return) ** (1 / years) - 1 if years > 0 else 0

    # YTD return
    ytd_start = pd.Timestamp(datetime.now().year, 1, 1, tz='UTC')
    ytd_returns = portfolio_returns[portfolio_returns.index >= ytd_start]
    ytd_return = (1 + ytd_returns).prod() - 1 if len(ytd_returns) > 0 else 0

    # Sharpe ratio
    volatility = portfolio_returns.std() * np.sqrt(252)
    sharpe = sharpe_ratio(annualized, volatility, 0.03)

    # Max drawdown
    mdd = max_drawdown(portfolio_returns)

    # Sortino ratio
    sortino = sortino_ratio(portfolio_returns, 0.03)

    return {
        "total_return": round(cumulative_return, 4),
        "annualized_return": round(annualized, 4),
        "ytd_return": round(ytd_return, 4),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "max_drawdown": round(mdd, 4),
        "volatility": round(volatility, 4)
    }


def _assess_risk(
    positions: Dict[str, Dict],
    prices: pd.DataFrame,
    benchmark: str,
    risk_tolerance: str
) -> Dict[str, Any]:
    """
    Assess portfolio risk.
    """
    # Calculate portfolio volatility
    total_value = sum([pos.get("shares", 0) * pos.get("current_price", prices[t].iloc[-1] if t in prices.columns else 0)
                       for t, pos in positions.items()])

    weights = {}
    for ticker, pos in positions.items():
        if ticker not in prices.columns:
            continue
        value = pos.get("shares", 0) * pos.get("current_price", prices[ticker].iloc[-1])
        weights[ticker] = value / total_value if total_value > 0 else 0

    returns = calculate_returns(prices[[t for t in positions.keys() if t in prices.columns]], method="log")

    portfolio_returns = pd.Series(0.0, index=returns.index)
    for ticker in returns.columns:
        if ticker in weights:
            portfolio_returns += returns[ticker] * weights[ticker]

    volatility = portfolio_returns.std() * np.sqrt(252)

    # Beta (if benchmark available)
    if benchmark in prices.columns:
        benchmark_returns = calculate_returns(prices[[benchmark]], method="log")[benchmark]
        covariance = portfolio_returns.cov(benchmark_returns)
        benchmark_var = benchmark_returns.var()
        beta = covariance / benchmark_var if benchmark_var > 0 else 1.0
    else:
        beta = 1.0

    # VaR 95%
    var_95 = np.percentile(portfolio_returns, 5)

    # Risk level assessment
    risk_profiles = {
        "conservative": 0.12,
        "moderate": 0.18,
        "aggressive": 0.25
    }

    target_vol = risk_profiles.get(risk_tolerance, 0.18)

    if volatility < target_vol * 0.8:
        risk_level = "Low"
    elif volatility < target_vol * 1.2:
        risk_level = "Appropriate"
    else:
        risk_level = "High"

    return {
        "volatility": round(volatility, 4),
        "beta": round(beta, 2),
        "var_95": round(var_95, 4),
        "risk_level": risk_level,
        "target_volatility": round(target_vol, 4)
    }


def _analyze_diversification(
    positions: Dict[str, Dict],
    prices: pd.DataFrame
) -> Dict[str, Any]:
    """
    Analyze portfolio diversification.
    """
    # Calculate portfolio weights
    total_value = sum([pos.get("shares", 0) * pos.get("current_price", prices[t].iloc[-1] if t in prices.columns else 0)
                       for t, pos in positions.items()])

    weights = []
    for ticker, pos in positions.items():
        if ticker not in prices.columns:
            continue
        value = pos.get("shares", 0) * pos.get("current_price", prices[ticker].iloc[-1])
        weight = value / total_value if total_value > 0 else 0
        weights.append(weight)

    weights_array = np.array(weights)

    # Herfindahl index
    hhi = np.sum(weights_array ** 2) if len(weights_array) > 0 else 0

    # Effective number of assets
    effective_n = 1 / hhi if hhi > 0 else 0

    # Concentration risk
    if hhi < 0.15:
        concentration = "Low"
    elif hhi < 0.25:
        concentration = "Moderate"
    else:
        concentration = "High"

    # Top 3 concentration
    sorted_weights = sorted(weights, reverse=True)
    top_3 = sum(sorted_weights[:3]) if len(sorted_weights) >= 3 else sum(sorted_weights)

    return {
        "num_positions": len(positions),
        "effective_assets": round(effective_n, 2),
        "concentration_risk": concentration,
        "herfindahl_index": round(hhi, 4),
        "top_3_concentration": round(top_3, 4)
    }


def _check_rebalancing_status(
    positions: Dict[str, Dict],
    target_weights: Optional[Dict[str, float]],
    prices: pd.DataFrame,
    threshold: float = 0.05
) -> Dict[str, Any]:
    """
    Check if rebalancing is needed.
    """
    if not target_weights:
        return {
            "needed": False,
            "max_drift": 0,
            "drifted_positions": [],
            "note": "No target weights specified"
        }

    # Calculate current weights
    total_value = sum([pos.get("shares", 0) * pos.get("current_price", prices[t].iloc[-1] if t in prices.columns else 0)
                       for t, pos in positions.items()])

    current_weights = {}
    for ticker, pos in positions.items():
        if ticker not in prices.columns:
            continue
        value = pos.get("shares", 0) * pos.get("current_price", prices[ticker].iloc[-1])
        current_weights[ticker] = value / total_value if total_value > 0 else 0

    # Check drift
    drifted = []
    max_drift = 0

    for ticker in target_weights.keys():
        target = target_weights.get(ticker, 0)
        current = current_weights.get(ticker, 0)
        drift = abs(current - target)

        if drift > threshold:
            drifted.append(ticker)
            max_drift = max(max_drift, drift)

    return {
        "needed": len(drifted) > 0,
        "max_drift": round(max_drift, 4),
        "drifted_positions": drifted,
        "threshold": threshold
    }


def _assess_tax_efficiency(
    positions: Dict[str, Dict],
    current_date: datetime,
    tax_bracket: float
) -> Dict[str, Any]:
    """
    Assess tax efficiency of portfolio.
    """
    unrealized_gains = 0
    unrealized_losses = 0
    tlh_count = 0
    potential_savings = 0

    for ticker, pos in positions.items():
        shares = pos.get("shares", 0)
        cost_basis = pos.get("cost_basis", 0)
        current_price = pos.get("current_price", 0)
        purchase_date = pos.get("purchase_date")

        if shares <= 0:
            continue

        total_cost = shares * cost_basis
        current_value = shares * current_price
        gain_loss = current_value - total_cost

        if gain_loss > 0:
            unrealized_gains += gain_loss
        else:
            unrealized_losses += gain_loss

            # Tax loss harvest opportunity
            if abs(gain_loss / total_cost) > 0.03:  # 3% threshold
                tlh_count += 1

                # Determine holding period
                if purchase_date:
                    purchase_dt = pd.to_datetime(purchase_date)
                    holding_days = (current_date - purchase_dt).days
                    tax_rate = 0.15 if holding_days >= 365 else tax_bracket
                    potential_savings += abs(gain_loss) * tax_rate

    return {
        "unrealized_gains": round(unrealized_gains, 2),
        "unrealized_losses": round(unrealized_losses, 2),
        "net_unrealized": round(unrealized_gains + unrealized_losses, 2),
        "tlh_opportunities": tlh_count,
        "potential_tax_savings": round(potential_savings, 2)
    }


def _calculate_health_score(
    performance: Dict,
    risk: Dict,
    diversification: Dict,
    rebalancing: Dict,
    tax_efficiency: Dict,
    risk_tolerance: str
) -> Tuple[int, Dict[str, int]]:
    """
    Calculate portfolio health score (0-100).

    Components:
    - Performance (30%): Returns, Sharpe ratio
    - Risk Management (25%): Volatility, drawdown
    - Diversification (20%): Effective assets, concentration
    - Rebalancing (15%): Drift from target
    - Tax Efficiency (10%): Tax optimization
    """
    components = {}

    # Performance score (30 points)
    sharpe = performance.get("sharpe_ratio", 0)
    ann_return = performance.get("annualized_return", 0)

    perf_score = 0
    if sharpe > 2.0:
        perf_score += 20
    elif sharpe > 1.0:
        perf_score += 15
    elif sharpe > 0.5:
        perf_score += 10
    elif sharpe > 0:
        perf_score += 5

    if ann_return > 0.15:
        perf_score += 10
    elif ann_return > 0.08:
        perf_score += 7
    elif ann_return > 0:
        perf_score += 3

    components["performance"] = min(30, perf_score)

    # Risk score (25 points)
    risk_level = risk.get("risk_level", "Unknown")
    mdd = abs(performance.get("max_drawdown", 0))

    risk_score = 0
    if risk_level == "Appropriate":
        risk_score += 15
    elif risk_level == "Low":
        risk_score += 10
    else:
        risk_score += 5

    if mdd < 0.10:
        risk_score += 10
    elif mdd < 0.20:
        risk_score += 7
    elif mdd < 0.30:
        risk_score += 3

    components["risk_management"] = min(25, risk_score)

    # Diversification score (20 points)
    concentration = diversification.get("concentration_risk", "Unknown")
    effective_assets = diversification.get("effective_assets", 0)

    div_score = 0
    if concentration == "Low":
        div_score += 12
    elif concentration == "Moderate":
        div_score += 8
    else:
        div_score += 4

    if effective_assets > 8:
        div_score += 8
    elif effective_assets > 5:
        div_score += 5
    else:
        div_score += 2

    components["diversification"] = min(20, div_score)

    # Rebalancing score (15 points)
    rebal_needed = rebalancing.get("needed", False)
    max_drift = rebalancing.get("max_drift", 0)

    if not rebal_needed:
        rebal_score = 15
    elif max_drift < 0.10:
        rebal_score = 10
    elif max_drift < 0.15:
        rebal_score = 5
    else:
        rebal_score = 0

    components["rebalancing"] = rebal_score

    # Tax efficiency score (10 points)
    tlh_opps = tax_efficiency.get("tlh_opportunities", 0)
    net_unrealized = tax_efficiency.get("net_unrealized", 0)

    tax_score = 10
    if tlh_opps > 5:
        tax_score -= 3
    elif tlh_opps > 0:
        tax_score -= 1

    if net_unrealized < 0:
        tax_score -= 2  # Losses reduce score slightly

    components["tax_efficiency"] = max(0, tax_score)

    # Total score
    total = sum(components.values())

    return total, components


def _score_to_grade(score: int) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def _generate_recommendations(
    health_components: Dict[str, int],
    performance: Dict,
    risk: Dict,
    diversification: Dict,
    rebalancing: Dict,
    tax_efficiency: Dict
) -> List[str]:
    """Generate actionable recommendations."""
    recommendations = []

    # Performance
    if health_components["performance"] < 20:
        recommendations.append(
            "Performance: Consider reviewing portfolio strategy. "
            f"Sharpe ratio ({performance.get('sharpe_ratio', 0):.2f}) is below target."
        )

    # Risk
    if health_components["risk_management"] < 15:
        if risk.get("risk_level") == "High":
            recommendations.append(
                f"Risk: Portfolio volatility ({risk.get('volatility', 0):.1%}) exceeds target. "
                "Consider adding lower-risk assets or hedging positions."
            )

    # Diversification
    if health_components["diversification"] < 12:
        recommendations.append(
            f"Diversification: Portfolio is concentrated ({diversification.get('concentration_risk')}). "
            "Consider adding more positions or asset classes."
        )

    # Rebalancing
    if rebalancing.get("needed", False):
        recommendations.append(
            f"Rebalancing: Portfolio has drifted from targets (max drift: {rebalancing.get('max_drift', 0):.1%}). "
            f"Rebalance positions: {', '.join(rebalancing.get('drifted_positions', []))}."
        )

    # Tax efficiency
    if tax_efficiency.get("tlh_opportunities", 0) > 0:
        recommendations.append(
            f"Tax: {tax_efficiency['tlh_opportunities']} tax loss harvesting opportunities identified. "
            f"Potential savings: ${tax_efficiency.get('potential_tax_savings', 0):.2f}."
        )

    return recommendations


def _generate_alerts(
    performance: Dict,
    risk: Dict,
    rebalancing: Dict,
    tax_efficiency: Dict
) -> List[str]:
    """Generate critical alerts."""
    alerts = []

    # Large drawdown
    mdd = abs(performance.get("max_drawdown", 0))
    if mdd > 0.25:
        alerts.append(f"⚠️ Large drawdown detected: {mdd:.1%}")

    # High volatility
    if risk.get("risk_level") == "High":
        alerts.append(f"⚠️ Portfolio volatility is high: {risk.get('volatility', 0):.1%}")

    # Significant drift
    if rebalancing.get("max_drift", 0) > 0.15:
        alerts.append(f"⚠️ Significant drift from target allocation: {rebalancing.get('max_drift', 0):.1%}")

    # Large unrealized losses
    if tax_efficiency.get("unrealized_losses", 0) < -10000:
        alerts.append(f"⚠️ Large unrealized losses: ${tax_efficiency.get('unrealized_losses', 0):.2f}")

    return alerts


def _generate_interpretation(
    health_score: int,
    portfolio_value: float,
    performance: Dict,
    risk: Dict,
    recommendations: List[str]
) -> str:
    """Generate dashboard interpretation."""
    grade = _score_to_grade(health_score)

    interpretation = (
        f"Portfolio Health Score: {health_score}/100 (Grade {grade}). "
        f"Total value: ${portfolio_value:,.2f}. "
    )

    if health_score >= 80:
        interpretation += "Portfolio is in good health. "
    elif health_score >= 60:
        interpretation += "Portfolio needs some improvements. "
    else:
        interpretation += "Portfolio requires significant attention. "

    interpretation += (
        f"Performance: {performance.get('annualized_return', 0):.1%} annualized return, "
        f"{performance.get('sharpe_ratio', 0):.2f} Sharpe ratio. "
    )

    interpretation += (
        f"Risk: {risk.get('volatility', 0):.1%} volatility, "
        f"{risk.get('risk_level')} risk level. "
    )

    if recommendations:
        interpretation += f"{len(recommendations)} recommendations provided."

    return interpretation


# Example usage
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test():
        # Test: Portfolio dashboard
        positions = {
            "AAPL": {
                "shares": 100,
                "cost_basis": 150,
                "current_price": 185,
                "purchase_date": "2023-01-15"
            },
            "MSFT": {
                "shares": 50,
                "cost_basis": 300,
                "current_price": 420,
                "purchase_date": "2023-06-01"
            },
            "GOOGL": {
                "shares": 80,
                "cost_basis": 120,
                "current_price": 150,
                "purchase_date": "2023-03-01"
            }
        }

        target_weights = {
            "AAPL": 0.33,
            "MSFT": 0.33,
            "GOOGL": 0.34
        }

        result = await portfolio_dashboard(
            positions=positions,
            target_weights=target_weights,
            risk_tolerance="moderate",
            start_date="2024-01-01"
        )

        print("\n=== Portfolio Dashboard ===")
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"\nHealth Score: {result['health_score']}/100 (Grade: {result['health_grade']})")
            print(f"Portfolio Value: ${result['portfolio_value']:,.2f}")

            print(f"\nHealth Components:")
            for component, score in result['health_components'].items():
                print(f"  {component}: {score}")

            print(f"\nPerformance:")
            for k, v in result['performance'].items():
                print(f"  {k}: {v:.2%}" if isinstance(v, float) and 'ratio' not in k else f"  {k}: {v}")

            print(f"\nRisk Assessment:")
            for k, v in result['risk_assessment'].items():
                if isinstance(v, float):
                    print(f"  {k}: {v:.2%}" if k != 'beta' else f"  {k}: {v:.2f}")
                else:
                    print(f"  {k}: {v}")

            print(f"\nDiversification:")
            for k, v in result['diversification'].items():
                print(f"  {k}: {v}")

            print(f"\nRebalancing:")
            for k, v in result['rebalancing'].items():
                print(f"  {k}: {v}")

            print(f"\nTax Efficiency:")
            for k, v in result['tax_efficiency'].items():
                print(f"  {k}: {v}")

            if result['alerts']:
                print(f"\nAlerts:")
                for alert in result['alerts']:
                    print(f"  {alert}")

            print(f"\nRecommendations:")
            for i, rec in enumerate(result['recommendations'], 1):
                print(f"  {i}. {rec}")

            print(f"\nInterpretation:\n{result['interpretation']}")

    asyncio.run(test())
