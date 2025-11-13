"""
Tail Risk Analyzer Tool
Analyzes extreme losses and black swan events using Extreme Value Theory
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
from scipy import stats
from datetime import datetime


class TailRiskTool:
    """Advanced tail risk analysis using Extreme Value Theory"""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "stock-data"

    async def get_tool_info(self) -> Dict:
        """Get tool information for MCP protocol"""
        return {
            "name": "risk_analyze_tail_risk",
            "description": "Analyze tail risk, black swan probability, and extreme value distributions",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, TSLA)"
                    },
                    "period": {
                        "type": "integer",
                        "description": "Analysis period in days (default: 1000)"
                    },
                    "threshold_percentile": {
                        "type": "number",
                        "description": "Percentile for extreme value threshold (default: 0.95)"
                    },
                    "analysis": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Analyses to perform: extreme_value, fat_tail, skewness_kurtosis, black_swan, all"
                    }
                },
                "required": ["symbol"]
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tail risk analysis"""
        try:
            symbol = arguments.get("symbol", "").upper()
            period = arguments.get("period", 1000)
            threshold_pct = arguments.get("threshold_percentile", 0.95)
            analysis_types = arguments.get("analysis", ["all"])

            # Validation
            if not symbol:
                return {"error": "Symbol is required"}

            # Load data
            data_file = self.data_dir / f"{symbol}.csv"
            if not data_file.exists():
                return {"error": f"No data available for {symbol}"}

            df = pd.read_csv(data_file, index_col=0, parse_dates=True)
            if df.empty or 'Close' not in df.columns:
                return {"error": f"Invalid data for {symbol}"}

            # Get sufficient data
            df = df.tail(min(period, len(df)))

            if len(df) < 100:
                return {"error": f"Insufficient data: only {len(df)} days available"}

            # Calculate returns
            returns = df['Close'].pct_change().dropna()

            result = {
                "symbol": symbol,
                "period_days": len(df),
                "start_date": df.index.min().isoformat(),
                "end_date": df.index.max().isoformat(),
                "analyses": {}
            }

            # Determine analyses to run
            if "all" in analysis_types:
                analysis_types = ["extreme_value", "fat_tail", "skewness_kurtosis", "black_swan"]

            # Run analyses
            if "extreme_value" in analysis_types:
                result["analyses"]["extreme_value_theory"] = self._extreme_value_analysis(
                    returns, threshold_pct
                )

            if "fat_tail" in analysis_types:
                result["analyses"]["fat_tail"] = self._fat_tail_analysis(returns)

            if "skewness_kurtosis" in analysis_types:
                result["analyses"]["skewness_kurtosis"] = self._skewness_kurtosis_analysis(returns)

            if "black_swan" in analysis_types:
                result["analyses"]["black_swan"] = self._black_swan_analysis(returns)

            # Overall tail risk assessment
            result["assessment"] = self._generate_tail_risk_assessment(result["analyses"])

            return result

        except Exception as e:
            return {"error": f"Tail risk analysis failed: {str(e)}"}

    def _extreme_value_analysis(self, returns: pd.Series, threshold_pct: float) -> Dict:
        """Extreme Value Theory (EVT) analysis using Peaks Over Threshold (POT) method"""
        # Focus on left tail (losses)
        losses = -returns

        # Determine threshold (e.g., 95th percentile)
        threshold = np.percentile(losses, threshold_pct * 100)

        # Extract exceedances (losses beyond threshold)
        exceedances = losses[losses > threshold] - threshold

        if len(exceedances) < 10:
            return {
                "error": "Insufficient extreme events for EVT analysis",
                "threshold_percentile": threshold_pct * 100,
                "events_found": len(exceedances)
            }

        # Fit Generalized Pareto Distribution (GPD)
        # Using method of moments for simplicity
        mean_excess = exceedances.mean()
        var_excess = exceedances.var()

        # Shape parameter (xi) estimation
        xi = 0.5 * (1 - (mean_excess ** 2) / var_excess)

        # Scale parameter (beta) estimation
        beta = 0.5 * mean_excess * ((mean_excess ** 2) / var_excess + 1)

        # Calculate extreme VaR and CVaR
        n = len(losses)
        n_exceedances = len(exceedances)

        # Probability of exceeding threshold
        prob_exceed = n_exceedances / n

        # Extreme VaR at 99% and 99.9% confidence levels
        def calculate_extreme_var(confidence_level):
            q = 1 - confidence_level
            if abs(xi) < 1e-6:  # xi ≈ 0
                var = threshold + beta * np.log(prob_exceed / q)
            else:
                var = threshold + (beta / xi) * ((prob_exceed / q) ** (-xi) - 1)
            return var

        var_99 = calculate_extreme_var(0.99)
        var_999 = calculate_extreme_var(0.999)

        # Tail index (alpha) - measures tail heaviness
        # Lower alpha = heavier tail
        tail_index = 1 / xi if xi > 0 else None

        return {
            "method": "Generalized Pareto Distribution (GPD)",
            "threshold": float(round(threshold * 100, 4)),
            "exceedances_count": int(len(exceedances)),
            "exceedances_percent": float(round((n_exceedances / n) * 100, 2)),
            "parameters": {
                "shape_xi": float(round(xi, 4)),
                "scale_beta": float(round(beta, 4)),
                "tail_index_alpha": float(round(tail_index, 4)) if tail_index else "Infinite (no tail)"
            },
            "extreme_var": {
                "99_percent": float(round(var_99 * 100, 4)),
                "99_9_percent": float(round(var_999 * 100, 4))
            },
            "interpretation": self._interpret_evt(xi, tail_index)
        }

    def _interpret_evt(self, xi: float, tail_index: Optional[float]) -> str:
        """Interpret EVT results"""
        if xi < -0.5:
            return "Short-tailed distribution - extreme events unlikely"
        elif xi < 0:
            return "Light-tailed distribution - moderate tail risk"
        elif xi < 0.5:
            return "Heavy-tailed distribution - significant tail risk"
        else:
            return "Extremely heavy-tailed - high black swan risk"

    def _fat_tail_analysis(self, returns: pd.Series) -> Dict:
        """Analyze fat tail characteristics"""
        # Compare actual distribution to normal distribution
        losses = -returns

        # Calculate percentiles
        percentiles = [90, 95, 99, 99.5, 99.9]
        actual_percentiles = {}
        normal_percentiles = {}

        mean_loss = losses.mean()
        std_loss = losses.std()

        for p in percentiles:
            actual_percentiles[f"{p}%"] = float(round(np.percentile(losses, p) * 100, 4))
            normal_percentiles[f"{p}%"] = float(round((mean_loss + stats.norm.ppf(p/100) * std_loss) * 100, 4))

        # Fat tail ratio (actual vs normal at 99%)
        actual_99 = np.percentile(losses, 99)
        normal_99 = mean_loss + stats.norm.ppf(0.99) * std_loss
        fat_tail_ratio = actual_99 / normal_99 if normal_99 > 0 else 1.0

        # Count of extreme events (beyond 3 standard deviations)
        threshold_3std = mean_loss + 3 * std_loss
        extreme_events = losses[losses > threshold_3std]
        extreme_count = len(extreme_events)

        # Expected vs actual under normality
        expected_extreme = len(losses) * (1 - stats.norm.cdf(3))

        return {
            "fat_tail_ratio": float(round(fat_tail_ratio, 4)),
            "interpretation": self._interpret_fat_tail(fat_tail_ratio),
            "actual_percentiles": actual_percentiles,
            "normal_percentiles": normal_percentiles,
            "extreme_events_3std": {
                "actual_count": int(extreme_count),
                "expected_under_normality": float(round(expected_extreme, 2)),
                "multiplier": float(round(extreme_count / expected_extreme, 2)) if expected_extreme > 0 else "N/A"
            },
            "largest_losses": [float(round(x * 100, 4)) for x in sorted(losses, reverse=True)[:5]]
        }

    def _interpret_fat_tail(self, ratio: float) -> str:
        """Interpret fat tail ratio"""
        if ratio < 1.1:
            return "Normal-like tails - low tail risk"
        elif ratio < 1.5:
            return "Moderately fat tails - elevated tail risk"
        elif ratio < 2.0:
            return "Fat tails - significant tail risk"
        else:
            return "Extremely fat tails - severe tail risk"

    def _skewness_kurtosis_analysis(self, returns: pd.Series) -> Dict:
        """Analyze skewness and kurtosis"""
        # Calculate skewness (asymmetry)
        skewness = stats.skew(returns)

        # Calculate kurtosis (tail thickness)
        # Using excess kurtosis (subtract 3 for normal distribution baseline)
        kurtosis_excess = stats.kurtosis(returns)

        # Jarque-Bera test for normality
        jb_stat, jb_pvalue = stats.jarque_bera(returns)

        return {
            "skewness": float(round(skewness, 4)),
            "skewness_interpretation": self._interpret_skewness(skewness),
            "excess_kurtosis": float(round(kurtosis_excess, 4)),
            "kurtosis_interpretation": self._interpret_kurtosis(kurtosis_excess),
            "jarque_bera_test": {
                "statistic": float(round(jb_stat, 4)),
                "p_value": float(round(jb_pvalue, 6)),
                "is_normal": bool(jb_pvalue > 0.05),
                "interpretation": "Distribution is normal" if jb_pvalue > 0.05 else "Distribution is NOT normal - reject normality"
            },
            "overall_assessment": self._assess_distribution_shape(skewness, kurtosis_excess)
        }

    def _interpret_skewness(self, skewness: float) -> str:
        """Interpret skewness value"""
        if skewness < -0.5:
            return "Strong negative skew - frequent small gains, rare large losses (HIGH TAIL RISK)"
        elif skewness < -0.1:
            return "Moderate negative skew - asymmetric downside risk"
        elif skewness < 0.1:
            return "Approximately symmetric"
        elif skewness < 0.5:
            return "Moderate positive skew - frequent small losses, rare large gains"
        else:
            return "Strong positive skew - rare large gains dominate"

    def _interpret_kurtosis(self, kurtosis: float) -> str:
        """Interpret excess kurtosis"""
        if kurtosis < 0:
            return f"Light tails (platykurtic) - fewer extremes than normal"
        elif kurtosis < 1:
            return f"Near normal tail thickness"
        elif kurtosis < 3:
            return f"Moderately heavy tails (leptokurtic) - more extremes than normal"
        elif kurtosis < 5:
            return f"Heavy tails - significantly more extremes than normal"
        else:
            return f"Extremely heavy tails - very high frequency of extreme events"

    def _assess_distribution_shape(self, skewness: float, kurtosis: float) -> str:
        """Overall assessment of distribution shape"""
        if abs(skewness) < 0.1 and abs(kurtosis) < 1:
            return "Near-normal distribution - standard risk models applicable"
        elif skewness < -0.3 and kurtosis > 1:
            return "Dangerous combination: negative skew + heavy tails = HIGH TAIL RISK"
        elif skewness < -0.3:
            return "Asymmetric downside risk - consider tail hedges"
        elif kurtosis > 3:
            return "Fat tails present - expect frequent extreme events"
        else:
            return "Non-normal distribution - use robust risk measures"

    def _black_swan_analysis(self, returns: pd.Series) -> Dict:
        """Analyze black swan event probability"""
        losses = -returns
        mean_loss = losses.mean()
        std_loss = losses.std()

        # Define black swan thresholds
        thresholds = {
            "3_sigma": mean_loss + 3 * std_loss,
            "4_sigma": mean_loss + 4 * std_loss,
            "5_sigma": mean_loss + 5 * std_loss
        }

        # Count actual events
        events_3sigma = len(losses[losses > thresholds["3_sigma"]])
        events_4sigma = len(losses[losses > thresholds["4_sigma"]])
        events_5sigma = len(losses[losses > thresholds["5_sigma"]])

        # Expected frequencies under normality
        n = len(losses)
        expected_3sigma = n * (1 - stats.norm.cdf(3))
        expected_4sigma = n * (1 - stats.norm.cdf(4))
        expected_5sigma = n * (1 - stats.norm.cdf(5))

        # Black swan probability estimation
        # Using empirical frequency for extreme events
        if events_5sigma > 0:
            black_swan_prob = events_5sigma / n
            black_swan_expected_years = 252 / events_5sigma if events_5sigma > 0 else float('inf')
        else:
            black_swan_prob = 1 / n  # Use 1 event as minimum
            black_swan_expected_years = n / 252

        # Worst observed event
        worst_loss = losses.max()
        worst_loss_sigma = (worst_loss - mean_loss) / std_loss if std_loss > 0 else 0

        return {
            "black_swan_probability": {
                "annual_probability": float(round(black_swan_prob * 252, 6)),
                "expected_once_every_n_years": float(round(black_swan_expected_years, 2))
            },
            "extreme_event_frequencies": {
                "3_sigma_events": {
                    "actual": int(events_3sigma),
                    "expected_normal": float(round(expected_3sigma, 2)),
                    "multiplier": float(round(events_3sigma / expected_3sigma, 2)) if expected_3sigma > 0 else "N/A"
                },
                "4_sigma_events": {
                    "actual": int(events_4sigma),
                    "expected_normal": float(round(expected_4sigma, 4)),
                    "multiplier": float(round(events_4sigma / expected_4sigma, 2)) if expected_4sigma > 0.01 else "N/A"
                },
                "5_sigma_events": {
                    "actual": int(events_5sigma),
                    "expected_normal": float(round(expected_5sigma, 6)),
                    "multiplier": float(round(events_5sigma / expected_5sigma, 2)) if expected_5sigma > 0.001 else "N/A"
                }
            },
            "worst_observed_event": {
                "loss_percent": float(round(worst_loss * 100, 4)),
                "sigma_level": float(round(worst_loss_sigma, 2)),
                "interpretation": self._interpret_worst_event(worst_loss_sigma)
            },
            "tail_risk_alert": self._generate_tail_risk_alert(events_3sigma, expected_3sigma, events_5sigma)
        }

    def _interpret_worst_event(self, sigma: float) -> str:
        """Interpret worst event severity"""
        if sigma < 2:
            return "Within 2σ - normal market volatility"
        elif sigma < 3:
            return "2-3σ event - uncommon but expected"
        elif sigma < 4:
            return "3-4σ event - rare, significant stress"
        elif sigma < 5:
            return "4-5σ event - very rare, extreme stress"
        else:
            return "Beyond 5σ - BLACK SWAN event"

    def _generate_tail_risk_alert(
        self, events_3sigma: int, expected_3sigma: float, events_5sigma: int
    ) -> str:
        """Generate tail risk alert based on extreme events"""
        if events_5sigma > 0:
            return "CRITICAL: Black swan events (5σ+) observed. Tail risk hedging strongly recommended."
        elif events_3sigma > expected_3sigma * 2:
            return "HIGH: Extreme events occur more than 2x expected frequency. Consider tail risk hedges."
        elif events_3sigma > expected_3sigma * 1.5:
            return "MODERATE: Elevated tail risk. Monitor and consider protective strategies."
        else:
            return "LOW: Tail risk within normal ranges for the asset class."

    def _generate_tail_risk_assessment(self, analyses: Dict) -> Dict:
        """Generate overall tail risk assessment"""
        risk_score = 0
        max_score = 0
        warnings = []
        recommendations = []

        # Extreme Value Theory score
        if "extreme_value_theory" in analyses:
            evt = analyses["extreme_value_theory"]
            max_score += 25
            if "parameters" in evt:
                xi = evt["parameters"]["shape_xi"]
                if xi > 0.5:
                    risk_score += 25
                    warnings.append("Extremely heavy tail detected (EVT)")
                elif xi > 0.2:
                    risk_score += 18
                    warnings.append("Heavy tail detected (EVT)")
                elif xi > 0:
                    risk_score += 10

        # Fat Tail score
        if "fat_tail" in analyses:
            ft = analyses["fat_tail"]
            max_score += 25
            ratio = ft.get("fat_tail_ratio", 1.0)
            if ratio > 2.0:
                risk_score += 25
                warnings.append("Extremely fat tails detected")
            elif ratio > 1.5:
                risk_score += 18
                warnings.append("Significant fat tails")
            elif ratio > 1.2:
                risk_score += 10

        # Skewness/Kurtosis score
        if "skewness_kurtosis" in analyses:
            sk = analyses["skewness_kurtosis"]
            max_score += 25
            skew = sk.get("skewness", 0)
            kurt = sk.get("excess_kurtosis", 0)

            if skew < -0.3 and kurt > 2:
                risk_score += 25
                warnings.append("Dangerous: negative skew + high kurtosis")
            elif skew < -0.3:
                risk_score += 15
            elif kurt > 3:
                risk_score += 15

        # Black Swan score
        if "black_swan" in analyses:
            bs = analyses["black_swan"]
            max_score += 25
            if "extreme_event_frequencies" in bs:
                events_5 = bs["extreme_event_frequencies"]["5_sigma_events"]["actual"]
                events_3_mult = bs["extreme_event_frequencies"]["3_sigma_events"].get("multiplier")

                if events_5 > 0:
                    risk_score += 25
                    warnings.append("Black swan events (5σ+) observed")
                elif isinstance(events_3_mult, (int, float)) and events_3_mult > 2:
                    risk_score += 15
                    warnings.append("Frequent extreme events (3σ+)")

        # Calculate percentage
        tail_risk_percent = (risk_score / max_score * 100) if max_score > 0 else 0

        # Generate recommendations
        if tail_risk_percent > 70:
            recommendations.append("URGENT: Implement tail risk hedging immediately (put options, VIX calls)")
            recommendations.append("Reduce position sizes and increase diversification")
            recommendations.append("Consider stop-loss orders or dynamic hedging strategies")
        elif tail_risk_percent > 50:
            recommendations.append("High tail risk: Consider protective puts or collar strategies")
            recommendations.append("Monitor closely and maintain adequate reserves")
        elif tail_risk_percent > 30:
            recommendations.append("Moderate tail risk: Diversify and monitor tail risk metrics")
        else:
            recommendations.append("Tail risk within acceptable range for asset class")

        return {
            "tail_risk_score": float(round(tail_risk_percent, 2)),
            "risk_level": self._risk_level(tail_risk_percent),
            "warnings": warnings if warnings else ["No significant tail risk warnings"],
            "recommendations": recommendations
        }

    def _risk_level(self, score: float) -> str:
        """Determine risk level from score"""
        if score < 20:
            return "LOW"
        elif score < 40:
            return "MODERATE"
        elif score < 60:
            return "HIGH"
        elif score < 80:
            return "SEVERE"
        else:
            return "CRITICAL"
