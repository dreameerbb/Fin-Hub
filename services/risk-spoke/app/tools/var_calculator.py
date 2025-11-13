"""
Value at Risk (VaR) Calculator Tool
Implements Historical, Parametric, and Monte Carlo VaR methods
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from scipy import stats
from datetime import datetime, timedelta


class VaRCalculatorTool:
    """Calculate Value at Risk using multiple methods"""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "stock-data"

    async def get_tool_info(self) -> Dict:
        """Get tool information for MCP protocol"""
        return {
            "name": "risk_calculate_var",
            "description": "Calculate Value at Risk (VaR) using Historical, Parametric, or Monte Carlo methods",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, MSFT)"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["historical", "parametric", "monte_carlo", "all"],
                        "description": "VaR calculation method (default: all)"
                    },
                    "confidence_level": {
                        "type": "number",
                        "description": "Confidence level (e.g., 0.95, 0.99) - default: 0.95"
                    },
                    "time_horizon": {
                        "type": "integer",
                        "description": "Time horizon in days (default: 1)"
                    },
                    "portfolio_value": {
                        "type": "number",
                        "description": "Portfolio value in USD (default: 10000)"
                    },
                    "period": {
                        "type": "integer",
                        "description": "Historical data period in days (default: 252 = 1 year)"
                    },
                    "simulations": {
                        "type": "integer",
                        "description": "Number of Monte Carlo simulations (default: 10000)"
                    }
                },
                "required": ["symbol"]
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute VaR calculation"""
        try:
            symbol = arguments.get("symbol", "").upper()
            method = arguments.get("method", "all").lower()
            confidence = arguments.get("confidence_level", 0.95)
            time_horizon = arguments.get("time_horizon", 1)
            portfolio_value = arguments.get("portfolio_value", 10000)
            period = arguments.get("period", 252)
            simulations = arguments.get("simulations", 10000)

            # Validation
            if not symbol:
                return {"error": "Symbol is required"}

            if not 0 < confidence < 1:
                return {"error": "Confidence level must be between 0 and 1"}

            if time_horizon < 1:
                return {"error": "Time horizon must be at least 1 day"}

            # Load stock data
            data_file = self.data_dir / f"{symbol}.csv"
            if not data_file.exists():
                return {"error": f"No data available for {symbol}"}

            df = pd.read_csv(data_file, index_col=0, parse_dates=True)

            if df.empty or 'Close' not in df.columns:
                return {"error": f"Invalid data for {symbol}"}

            # Get recent data
            df = df.tail(period)

            if len(df) < 30:
                return {"error": f"Insufficient data: only {len(df)} days available"}

            # Calculate returns
            returns = df['Close'].pct_change().dropna()

            if len(returns) < 2:
                return {"error": "Not enough return data"}

            # Calculate VaR based on method
            result = {
                "symbol": symbol,
                "portfolio_value": portfolio_value,
                "confidence_level": confidence,
                "time_horizon": time_horizon,
                "data_period_days": len(df),
                "calculation_date": datetime.now().isoformat(),
                "methods": {}
            }

            if method == "historical" or method == "all":
                var_hist = self._calculate_historical_var(
                    returns, confidence, time_horizon, portfolio_value
                )
                result["methods"]["historical"] = var_hist

            if method == "parametric" or method == "all":
                var_param = self._calculate_parametric_var(
                    returns, confidence, time_horizon, portfolio_value
                )
                result["methods"]["parametric"] = var_param

            if method == "monte_carlo" or method == "all":
                var_mc = self._calculate_monte_carlo_var(
                    returns, confidence, time_horizon, portfolio_value, simulations
                )
                result["methods"]["monte_carlo"] = var_mc

            # Add summary
            if method == "all":
                result["summary"] = self._generate_summary(result["methods"], confidence)

            return result

        except Exception as e:
            return {"error": f"VaR calculation failed: {str(e)}"}

    def _calculate_historical_var(
        self, returns: pd.Series, confidence: float, horizon: int, portfolio_value: float
    ) -> Dict:
        """Calculate Historical VaR"""
        # Scale returns to time horizon
        if horizon > 1:
            scaled_returns = returns * np.sqrt(horizon)
        else:
            scaled_returns = returns

        # Sort returns and find percentile
        sorted_returns = np.sort(scaled_returns)
        index = int((1 - confidence) * len(sorted_returns))
        var_return = sorted_returns[index]

        # Calculate VaR in USD
        var_usd = abs(var_return * portfolio_value)

        # Calculate CVaR (Expected Shortfall)
        cvar_return = sorted_returns[:index].mean()
        cvar_usd = abs(cvar_return * portfolio_value)

        return {
            "method": "Historical Simulation",
            "description": "Uses actual historical returns distribution",
            "var_percent": float(round(var_return * 100, 4)),
            "var_usd": float(round(var_usd, 2)),
            "cvar_percent": float(round(cvar_return * 100, 4)),
            "cvar_usd": float(round(cvar_usd, 2)),
            "interpretation": f"With {confidence*100}% confidence, maximum loss over {horizon} day(s) will not exceed ${var_usd:,.2f}",
            "worst_case": f"Expected loss in worst {(1-confidence)*100}% scenarios: ${cvar_usd:,.2f}"
        }

    def _calculate_parametric_var(
        self, returns: pd.Series, confidence: float, horizon: int, portfolio_value: float
    ) -> Dict:
        """Calculate Parametric VaR (Variance-Covariance method)"""
        # Calculate mean and std of returns
        mean_return = returns.mean()
        std_return = returns.std()

        # Scale to time horizon
        if horizon > 1:
            mean_scaled = mean_return * horizon
            std_scaled = std_return * np.sqrt(horizon)
        else:
            mean_scaled = mean_return
            std_scaled = std_return

        # Get z-score for confidence level
        z_score = stats.norm.ppf(1 - confidence)

        # Calculate VaR
        var_return = mean_scaled + z_score * std_scaled
        var_usd = abs(var_return * portfolio_value)

        # Calculate CVaR for normal distribution
        # CVaR = mean + std * (phi(z) / (1 - confidence))
        phi_z = stats.norm.pdf(z_score)
        cvar_return = mean_scaled + std_scaled * (phi_z / (1 - confidence))
        cvar_usd = abs(cvar_return * portfolio_value)

        # Normality test
        _, p_value = stats.normaltest(returns)
        is_normal = p_value > 0.05

        return {
            "method": "Parametric (Variance-Covariance)",
            "description": "Assumes normal distribution of returns",
            "var_percent": float(round(var_return * 100, 4)),
            "var_usd": float(round(var_usd, 2)),
            "cvar_percent": float(round(cvar_return * 100, 4)),
            "cvar_usd": float(round(cvar_usd, 2)),
            "mean_return": float(round(mean_return * 100, 4)),
            "std_return": float(round(std_return * 100, 4)),
            "z_score": float(round(z_score, 4)),
            "normality_test": {
                "is_normal": bool(is_normal),
                "p_value": float(round(p_value, 4)),
                "warning": "Parametric VaR may be inaccurate" if not is_normal else None
            },
            "interpretation": f"Assuming normal distribution, {confidence*100}% confidence max loss is ${var_usd:,.2f}"
        }

    def _calculate_monte_carlo_var(
        self, returns: pd.Series, confidence: float, horizon: int,
        portfolio_value: float, simulations: int
    ) -> Dict:
        """Calculate Monte Carlo VaR"""
        mean_return = returns.mean()
        std_return = returns.std()

        # Generate random scenarios
        np.random.seed(42)  # For reproducibility
        random_returns = np.random.normal(mean_return, std_return, simulations)

        # Scale to time horizon
        if horizon > 1:
            scaled_returns = random_returns * np.sqrt(horizon)
        else:
            scaled_returns = random_returns

        # Sort and find VaR
        sorted_returns = np.sort(scaled_returns)
        index = int((1 - confidence) * simulations)
        var_return = sorted_returns[index]
        var_usd = abs(var_return * portfolio_value)

        # Calculate CVaR
        cvar_return = sorted_returns[:index].mean()
        cvar_usd = abs(cvar_return * portfolio_value)

        # Calculate percentiles for risk distribution
        percentiles = {
            "95%": np.percentile(scaled_returns, 5),
            "99%": np.percentile(scaled_returns, 1),
            "99.9%": np.percentile(scaled_returns, 0.1)
        }

        return {
            "method": "Monte Carlo Simulation",
            "description": "Uses random sampling to simulate potential outcomes",
            "var_percent": float(round(var_return * 100, 4)),
            "var_usd": float(round(var_usd, 2)),
            "cvar_percent": float(round(cvar_return * 100, 4)),
            "cvar_usd": float(round(cvar_usd, 2)),
            "simulations": int(simulations),
            "risk_percentiles": {
                "95% confidence": float(round(abs(percentiles["95%"] * portfolio_value), 2)),
                "99% confidence": float(round(abs(percentiles["99%"] * portfolio_value), 2)),
                "99.9% confidence": float(round(abs(percentiles["99.9%"] * portfolio_value), 2))
            },
            "interpretation": f"Based on {simulations} simulations, {confidence*100}% confidence max loss is ${var_usd:,.2f}"
        }

    def _generate_summary(self, methods: Dict, confidence: float) -> Dict:
        """Generate summary comparing all methods"""
        var_values = [m["var_usd"] for m in methods.values()]
        cvar_values = [m["cvar_usd"] for m in methods.values()]

        avg_var = np.mean(var_values)
        avg_cvar = np.mean(cvar_values)
        std_var = np.std(var_values)

        # Determine which method is most conservative
        max_var_method = max(methods.items(), key=lambda x: x[1]["var_usd"])
        min_var_method = min(methods.items(), key=lambda x: x[1]["var_usd"])

        return {
            "comparison": {
                "average_var": float(round(avg_var, 2)),
                "average_cvar": float(round(avg_cvar, 2)),
                "std_deviation": float(round(std_var, 2)),
                "coefficient_of_variation": float(round((std_var / avg_var) * 100, 2))
            },
            "most_conservative": {
                "method": max_var_method[0],
                "var_usd": max_var_method[1]["var_usd"]
            },
            "least_conservative": {
                "method": min_var_method[0],
                "var_usd": min_var_method[1]["var_usd"]
            },
            "recommendation": self._get_recommendation(methods, std_var, avg_var)
        }

    def _get_recommendation(self, methods: Dict, std_var: float, avg_var: float) -> str:
        """Generate recommendation based on results"""
        cv = (std_var / avg_var) * 100

        if cv < 5:
            return "All methods agree closely. Results are reliable."
        elif cv < 15:
            return "Methods show moderate variation. Consider average for decision-making."
        else:
            rec = "Significant variation between methods. "
            if "parametric" in methods:
                if not methods["parametric"]["normality_test"]["is_normal"]:
                    rec += "Returns are not normally distributed - prefer Historical or Monte Carlo methods."
                else:
                    rec += "Consider using multiple methods for risk assessment."
            return rec
