"""
Portfolio Risk Analysis Tool
Analyzes risk for a portfolio of multiple assets
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from scipy import stats
from datetime import datetime


class PortfolioRiskTool:
    """Analyze risk for multi-asset portfolios"""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "stock-data"
        self.risk_free_rate = 0.04

    async def get_tool_info(self) -> Dict:
        """Get tool information for MCP protocol"""
        return {
            "name": "risk_analyze_portfolio",
            "description": "Analyze risk metrics for a portfolio of multiple assets with specified weights",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "portfolio": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "symbol": {"type": "string"},
                                "weight": {"type": "number"}
                            }
                        },
                        "description": "Array of {symbol, weight} objects. Weights should sum to 1.0"
                    },
                    "period": {
                        "type": "integer",
                        "description": "Analysis period in days (default: 252)"
                    },
                    "confidence_level": {
                        "type": "number",
                        "description": "VaR confidence level (default: 0.95)"
                    },
                    "risk_free_rate": {
                        "type": "number",
                        "description": "Annual risk-free rate (default: 0.04)"
                    },
                    "rebalance": {
                        "type": "boolean",
                        "description": "Whether to rebalance portfolio periodically (default: false)"
                    }
                },
                "required": ["portfolio"]
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute portfolio risk analysis"""
        try:
            portfolio = arguments.get("portfolio", [])
            period = arguments.get("period", 252)
            confidence = arguments.get("confidence_level", 0.95)
            rf_rate = arguments.get("risk_free_rate", self.risk_free_rate)
            rebalance = arguments.get("rebalance", False)

            # Validation
            if not portfolio:
                return {"error": "Portfolio must contain at least one asset"}

            if len(portfolio) > 50:
                return {"error": "Portfolio size limited to 50 assets"}

            # Extract symbols and weights
            symbols = [p.get("symbol", "").upper() for p in portfolio]
            weights = np.array([p.get("weight", 0) for p in portfolio])

            # Validate weights
            if not np.isclose(weights.sum(), 1.0, atol=0.01):
                return {"error": f"Weights must sum to 1.0 (currently: {weights.sum()})"}

            if np.any(weights < 0):
                return {"error": "Weights cannot be negative"}

            if not all(symbols):
                return {"error": "All portfolio items must have a symbol"}

            # Load data for all symbols
            price_data = {}
            missing_symbols = []

            for symbol in symbols:
                data_file = self.data_dir / f"{symbol}.csv"
                if not data_file.exists():
                    missing_symbols.append(symbol)
                    continue

                df = pd.read_csv(data_file, index_col=0, parse_dates=True)
                if df.empty or 'Close' not in df.columns:
                    missing_symbols.append(symbol)
                    continue

                price_data[symbol] = df['Close'].tail(period)

            if missing_symbols:
                return {"error": f"Data not available for: {', '.join(missing_symbols)}"}

            if len(price_data) < len(symbols):
                return {"error": "Could not load all portfolio data"}

            # Create aligned price matrix
            price_df = pd.DataFrame(price_data)
            price_df = price_df.dropna()

            if len(price_df) < 30:
                return {"error": f"Insufficient overlapping data: only {len(price_df)} days"}

            # Calculate returns matrix
            returns_df = price_df.pct_change().dropna()

            # Calculate portfolio metrics
            result = {
                "portfolio": portfolio,
                "period_days": len(price_df),
                "start_date": price_df.index.min().isoformat(),
                "end_date": price_df.index.max().isoformat(),
                "rebalanced": rebalance,
                "metrics": {}
            }

            # Portfolio returns
            if rebalance:
                # Rebalance daily - use weighted average of returns
                portfolio_returns = (returns_df * weights).sum(axis=1)
            else:
                # Buy and hold - calculate actual portfolio value changes
                portfolio_value = (price_df / price_df.iloc[0] * weights).sum(axis=1)
                portfolio_returns = portfolio_value.pct_change().dropna()

            # Basic return metrics
            result["metrics"]["returns"] = self._calculate_portfolio_returns(
                portfolio_returns, price_df, weights
            )

            # Risk metrics
            result["metrics"]["risk"] = self._calculate_portfolio_risk(
                returns_df, weights, portfolio_returns
            )

            # VaR calculation
            result["metrics"]["var"] = self._calculate_portfolio_var(
                portfolio_returns, confidence
            )

            # Diversification metrics
            result["metrics"]["diversification"] = self._calculate_diversification(
                returns_df, weights
            )

            # Correlation analysis
            result["metrics"]["correlation"] = self._calculate_correlation_metrics(
                returns_df
            )

            # Performance metrics
            result["metrics"]["performance"] = self._calculate_performance_metrics(
                portfolio_returns, rf_rate
            )

            # Concentration risk
            result["metrics"]["concentration"] = self._calculate_concentration_risk(
                portfolio, weights
            )

            # Interpretation
            result["interpretation"] = self._generate_portfolio_interpretation(
                result["metrics"], weights
            )

            return result

        except Exception as e:
            return {"error": f"Portfolio analysis failed: {str(e)}"}

    def _calculate_portfolio_returns(
        self, portfolio_returns: pd.Series, price_df: pd.DataFrame, weights: np.ndarray
    ) -> Dict:
        """Calculate portfolio return metrics"""
        total_return = (1 + portfolio_returns).prod() - 1
        days = len(portfolio_returns)
        years = days / 252
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # Calculate individual asset contributions
        individual_returns = (price_df.iloc[-1] / price_df.iloc[0] - 1) * weights
        contribution = individual_returns / individual_returns.sum() * 100 if individual_returns.sum() != 0 else np.zeros_like(weights)

        return {
            "total_percent": round(total_return * 100, 2),
            "annualized_percent": round(annual_return * 100, 2),
            "cumulative_return": round(total_return, 4),
            "asset_contributions": {
                symbol: round(contrib, 2)
                for symbol, contrib in zip(price_df.columns, contribution)
            }
        }

    def _calculate_portfolio_risk(
        self, returns_df: pd.DataFrame, weights: np.ndarray, portfolio_returns: pd.Series
    ) -> Dict:
        """Calculate portfolio risk metrics"""
        # Portfolio volatility from actual returns
        portfolio_vol = portfolio_returns.std() * np.sqrt(252)

        # Individual asset volatilities
        asset_vols = returns_df.std() * np.sqrt(252)

        # Weighted average volatility (undiversified)
        weighted_avg_vol = (asset_vols * weights).sum()

        # Diversification benefit
        diversification_benefit = weighted_avg_vol - portfolio_vol

        return {
            "portfolio_volatility_annual": round(portfolio_vol * 100, 2),
            "weighted_avg_volatility": round(weighted_avg_vol * 100, 2),
            "diversification_benefit": round(diversification_benefit * 100, 2),
            "volatility_reduction": round((diversification_benefit / weighted_avg_vol * 100), 2) if weighted_avg_vol > 0 else 0,
            "asset_volatilities": {
                symbol: round(vol * 100, 2)
                for symbol, vol in zip(returns_df.columns, asset_vols)
            }
        }

    def _calculate_portfolio_var(self, portfolio_returns: pd.Series, confidence: float) -> Dict:
        """Calculate portfolio VaR"""
        # Historical VaR
        sorted_returns = np.sort(portfolio_returns)
        index = int((1 - confidence) * len(sorted_returns))
        var_return = sorted_returns[index]

        # CVaR
        cvar_return = sorted_returns[:index].mean()

        # Parametric VaR
        mean_return = portfolio_returns.mean()
        std_return = portfolio_returns.std()
        z_score = stats.norm.ppf(1 - confidence)
        param_var = mean_return + z_score * std_return

        return {
            "confidence_level": confidence,
            "historical_var_percent": round(var_return * 100, 4),
            "historical_cvar_percent": round(cvar_return * 100, 4),
            "parametric_var_percent": round(param_var * 100, 4),
            "interpretation": f"With {confidence*100}% confidence, portfolio will not lose more than {abs(var_return)*100:.2f}% in one day"
        }

    def _calculate_diversification(self, returns_df: pd.DataFrame, weights: np.ndarray) -> Dict:
        """Calculate diversification metrics"""
        # Correlation matrix
        corr_matrix = returns_df.corr()

        # Weighted average correlation
        weighted_corr = 0
        total_weight = 0
        n = len(weights)

        for i in range(n):
            for j in range(i + 1, n):
                weight_product = weights[i] * weights[j]
                weighted_corr += corr_matrix.iloc[i, j] * weight_product
                total_weight += weight_product

        avg_correlation = weighted_corr / total_weight if total_weight > 0 else 0

        # Diversification ratio (Choueifaty)
        asset_vols = returns_df.std() * np.sqrt(252)
        weighted_vol = (asset_vols * weights).sum()

        cov_matrix = returns_df.cov() * 252
        portfolio_var = np.dot(weights, np.dot(cov_matrix, weights))
        portfolio_vol = np.sqrt(portfolio_var)

        div_ratio = weighted_vol / portfolio_vol if portfolio_vol > 0 else 1

        # Effective number of assets (inverse HHI of weights)
        hhi = np.sum(weights ** 2)
        effective_n = 1 / hhi if hhi > 0 else len(weights)

        return {
            "average_correlation": round(avg_correlation, 4),
            "diversification_ratio": round(div_ratio, 4),
            "effective_number_of_assets": round(effective_n, 2),
            "interpretation": self._interpret_diversification(avg_correlation, div_ratio, effective_n, len(weights))
        }

    def _interpret_diversification(
        self, avg_corr: float, div_ratio: float, effective_n: float, actual_n: int
    ) -> str:
        """Interpret diversification level"""
        if avg_corr > 0.7:
            corr_msg = "High correlation - limited diversification benefit"
        elif avg_corr > 0.4:
            corr_msg = "Moderate correlation - some diversification benefit"
        else:
            corr_msg = "Low correlation - good diversification"

        eff_pct = (effective_n / actual_n) * 100 if actual_n > 0 else 0
        if eff_pct > 80:
            eff_msg = "Well-diversified portfolio"
        elif eff_pct > 50:
            eff_msg = "Moderately diversified"
        else:
            eff_msg = "Concentrated portfolio - high concentration risk"

        return f"{corr_msg}. {eff_msg} ({effective_n:.1f} effective assets from {actual_n} holdings)"

    def _calculate_correlation_metrics(self, returns_df: pd.DataFrame) -> Dict:
        """Calculate correlation metrics"""
        corr_matrix = returns_df.corr()

        # Get all pairwise correlations
        correlations = []
        pairs = []

        for i in range(len(corr_matrix)):
            for j in range(i + 1, len(corr_matrix)):
                correlations.append(corr_matrix.iloc[i, j])
                pairs.append(f"{corr_matrix.index[i]}-{corr_matrix.columns[j]}")

        # Handle single-asset portfolio (no pairwise correlations)
        if len(correlations) == 0:
            return {
                "average_correlation": None,
                "median_correlation": None,
                "max_correlation": None,
                "min_correlation": None,
                "high_correlation_pairs": [],
                "note": "Single-asset portfolio - no correlation data"
            }

        correlations = np.array(correlations)

        # Find highest and lowest correlations
        max_idx = np.argmax(correlations)
        min_idx = np.argmin(correlations)

        return {
            "average_correlation": round(np.mean(correlations), 4),
            "median_correlation": round(np.median(correlations), 4),
            "max_correlation": {
                "value": round(correlations[max_idx], 4),
                "pair": pairs[max_idx]
            },
            "min_correlation": {
                "value": round(correlations[min_idx], 4),
                "pair": pairs[min_idx]
            },
            "high_correlation_pairs": [
                {"pair": pair, "correlation": round(corr, 4)}
                for pair, corr in zip(pairs, correlations)
                if corr > 0.7
            ][:5]  # Top 5
        }

    def _calculate_performance_metrics(self, portfolio_returns: pd.Series, rf_rate: float) -> Dict:
        """Calculate portfolio performance metrics"""
        annual_return = portfolio_returns.mean() * 252
        annual_vol = portfolio_returns.std() * np.sqrt(252)

        # Sharpe Ratio
        sharpe = (annual_return - rf_rate) / annual_vol if annual_vol > 0 else 0

        # Sortino Ratio
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else annual_vol
        sortino = (annual_return - rf_rate) / downside_vol if downside_vol > 0 else 0

        # Maximum Drawdown
        cumulative = (1 + portfolio_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()

        # Calmar Ratio
        calmar = annual_return / abs(max_dd) if max_dd != 0 else 0

        return {
            "sharpe_ratio": round(sharpe, 4),
            "sortino_ratio": round(sortino, 4),
            "calmar_ratio": round(calmar, 4),
            "max_drawdown_percent": round(max_dd * 100, 2),
            "interpretation": self._interpret_performance(sharpe, max_dd)
        }

    def _interpret_performance(self, sharpe: float, max_dd: float) -> str:
        """Interpret performance metrics"""
        if sharpe > 1.5 and max_dd > -0.15:
            return "Excellent risk-adjusted performance with controlled drawdowns"
        elif sharpe > 1 and max_dd > -0.25:
            return "Good risk-adjusted performance"
        elif sharpe > 0.5:
            return "Acceptable performance but room for improvement"
        else:
            return "Poor risk-adjusted performance - consider rebalancing"

    def _calculate_concentration_risk(self, portfolio: List[Dict], weights: np.ndarray) -> Dict:
        """Calculate concentration risk metrics"""
        # Herfindahl-Hirschman Index (HHI)
        hhi = np.sum(weights ** 2)

        # Number of assets needed to have equal weight for same HHI
        equivalent_n = 1 / hhi if hhi > 0 else len(weights)

        # Top N concentration
        sorted_indices = np.argsort(weights)[::-1]
        top3_weight = weights[sorted_indices[:min(3, len(weights))]].sum()
        top5_weight = weights[sorted_indices[:min(5, len(weights))]].sum()

        return {
            "herfindahl_index": round(hhi, 4),
            "equivalent_equal_weighted_assets": round(equivalent_n, 2),
            "top3_concentration_percent": round(top3_weight * 100, 2),
            "top5_concentration_percent": round(top5_weight * 100, 2),
            "largest_positions": [
                {
                    "symbol": portfolio[i]["symbol"],
                    "weight_percent": round(weights[i] * 100, 2)
                }
                for i in sorted_indices[:5]
            ],
            "interpretation": self._interpret_concentration(hhi, top3_weight)
        }

    def _interpret_concentration(self, hhi: float, top3: float) -> str:
        """Interpret concentration level"""
        if hhi < 0.1:
            level = "Low concentration - well diversified"
        elif hhi < 0.2:
            level = "Moderate concentration"
        else:
            level = "High concentration - significant single-asset risk"

        if top3 > 0.6:
            top_msg = "Top 3 positions dominate portfolio"
        elif top3 > 0.4:
            top_msg = "Top 3 positions have significant weight"
        else:
            top_msg = "Balanced weight distribution"

        return f"{level}. {top_msg}"

    def _generate_portfolio_interpretation(self, metrics: Dict, weights: np.ndarray) -> Dict:
        """Generate overall portfolio interpretation"""
        recommendations = []

        # Check diversification
        if "diversification" in metrics:
            avg_corr = metrics["diversification"]["average_correlation"]
            if avg_corr > 0.6:
                recommendations.append("High asset correlation reduces diversification benefits - consider adding uncorrelated assets")

        # Check concentration
        if "concentration" in metrics:
            if metrics["concentration"]["top3_concentration_percent"] > 60:
                recommendations.append("Portfolio is highly concentrated in top 3 positions - consider rebalancing")

        # Check performance
        if "performance" in metrics:
            sharpe = metrics["performance"]["sharpe_ratio"]
            if sharpe < 0.5:
                recommendations.append("Low Sharpe ratio suggests poor risk-adjusted returns")

        # Check volatility
        if "risk" in metrics:
            vol = metrics["risk"]["portfolio_volatility_annual"]
            if vol > 30:
                recommendations.append("High portfolio volatility - consider adding lower-risk assets")

        if not recommendations:
            recommendations.append("Portfolio appears well-constructed with acceptable risk metrics")

        return {
            "risk_level": self._assess_risk_level(metrics),
            "diversification_quality": self._assess_diversification(metrics),
            "recommendations": recommendations
        }

    def _assess_risk_level(self, metrics: Dict) -> str:
        """Assess overall portfolio risk level"""
        if "risk" in metrics:
            vol = metrics["risk"]["portfolio_volatility_annual"]
            if vol < 15:
                return "Low"
            elif vol < 25:
                return "Moderate"
            elif vol < 40:
                return "High"
            else:
                return "Very High"
        return "Unknown"

    def _assess_diversification(self, metrics: Dict) -> str:
        """Assess diversification quality"""
        if "diversification" in metrics:
            div_ratio = metrics["diversification"]["diversification_ratio"]
            if div_ratio > 1.4:
                return "Excellent"
            elif div_ratio > 1.2:
                return "Good"
            elif div_ratio > 1.0:
                return "Fair"
            else:
                return "Poor"
        return "Unknown"
