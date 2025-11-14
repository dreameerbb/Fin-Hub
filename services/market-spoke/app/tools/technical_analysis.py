"""
Technical Analysis Tool - Advanced market analysis with technical indicators
Provides RSI, MACD, Bollinger Bands, Moving Averages, and more
"""

import sys
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from pathlib import Path
import json


class TechnicalAnalysisTool:
    """Advanced technical analysis using historical stock data"""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent.parent.parent / 'data' / 'stock-data'

    async def get_tool_info(self) -> Dict:
        """Get tool information for MCP protocol"""
        return {
            "name": "technical_analysis",
            "description": "Perform comprehensive technical analysis on stocks with indicators like RSI, MACD, Bollinger Bands, and Moving Averages",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, MSFT)"
                    },
                    "indicators": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["rsi", "macd", "bollinger", "sma", "ema", "all"]
                        },
                        "description": "List of indicators to calculate (default: all)",
                        "default": ["all"]
                    },
                    "period": {
                        "type": "integer",
                        "description": "Number of days for analysis (default: 30)",
                        "default": 30
                    }
                },
                "required": ["symbol"]
            }
        }

    def _load_stock_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Load stock data from CSV file"""
        try:
            file_path = self.data_dir / f"{symbol.upper()}.csv"
            if not file_path.exists():
                return None

            df = pd.read_csv(file_path)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
            return df
        except Exception as e:
            print(f"Error loading data for {symbol}: {e}", file=sys.stderr)
            return None

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index (RSI)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, prices: pd.Series,
                        fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            "macd_line": macd_line,
            "signal_line": signal_line,
            "histogram": histogram
        }

    def _calculate_bollinger_bands(self, prices: pd.Series,
                                    period: int = 20, std_dev: int = 2) -> Dict:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        return {
            "upper_band": upper_band,
            "middle_band": sma,
            "lower_band": lower_band
        }

    def _calculate_sma(self, prices: pd.Series, periods: List[int] = [20, 50, 200]) -> Dict:
        """Calculate Simple Moving Averages"""
        smas = {}
        for period in periods:
            smas[f"sma_{period}"] = prices.rolling(window=period).mean()
        return smas

    def _calculate_ema(self, prices: pd.Series, periods: List[int] = [12, 26, 50]) -> Dict:
        """Calculate Exponential Moving Averages"""
        emas = {}
        for period in periods:
            emas[f"ema_{period}"] = prices.ewm(span=period, adjust=False).mean()
        return emas

    def _generate_signals(self, df: pd.DataFrame, indicators: Dict) -> Dict:
        """Generate trading signals based on indicators"""
        signals = {}
        latest = df.iloc[-1]

        # RSI signals
        if 'rsi' in indicators:
            rsi_value = indicators['rsi'].iloc[-1]
            if rsi_value < 30:
                signals['rsi_signal'] = "OVERSOLD - Potential BUY"
            elif rsi_value > 70:
                signals['rsi_signal'] = "OVERBOUGHT - Potential SELL"
            else:
                signals['rsi_signal'] = "NEUTRAL"

        # MACD signals
        if 'macd' in indicators:
            macd_hist = indicators['macd']['histogram'].iloc[-1]
            prev_hist = indicators['macd']['histogram'].iloc[-2]

            if macd_hist > 0 and prev_hist <= 0:
                signals['macd_signal'] = "BULLISH CROSSOVER - BUY"
            elif macd_hist < 0 and prev_hist >= 0:
                signals['macd_signal'] = "BEARISH CROSSOVER - SELL"
            else:
                signals['macd_signal'] = "NEUTRAL"

        # Bollinger Bands signals
        if 'bollinger' in indicators:
            price = latest['Close']
            upper = indicators['bollinger']['upper_band'].iloc[-1]
            lower = indicators['bollinger']['lower_band'].iloc[-1]

            if price >= upper:
                signals['bollinger_signal'] = "OVERBOUGHT - Near upper band"
            elif price <= lower:
                signals['bollinger_signal'] = "OVERSOLD - Near lower band"
            else:
                signals['bollinger_signal'] = "NEUTRAL"

        # Moving Average signals
        if 'sma' in indicators:
            price = latest['Close']
            sma_20 = indicators['sma']['sma_20'].iloc[-1]
            sma_50 = indicators['sma']['sma_50'].iloc[-1]

            if price > sma_20 > sma_50:
                signals['trend_signal'] = "STRONG UPTREND"
            elif price < sma_20 < sma_50:
                signals['trend_signal'] = "STRONG DOWNTREND"
            else:
                signals['trend_signal'] = "MIXED/RANGING"

        return signals

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute technical analysis"""
        symbol = arguments.get("symbol", "").upper()
        # Normalize indicator names to lowercase
        requested_indicators = [ind.lower() for ind in arguments.get("indicators", ["all"])]
        period = arguments.get("period", 30)

        if not symbol:
            return {"error": "Symbol is required"}

        # Load stock data
        df = self._load_stock_data(symbol)
        if df is None:
            return {
                "error": f"No data found for {symbol}",
                "suggestion": "Try symbols like AAPL, MSFT, GOOGL, etc."
            }

        # Get recent data based on period
        df_recent = df.tail(period + 200)  # Extra data for indicator calculation

        if len(df_recent) < period:
            return {
                "error": f"Insufficient data for {symbol}",
                "available_days": len(df_recent)
            }

        # Determine which indicators to calculate
        calc_all = "all" in requested_indicators
        indicators_result = {}
        calculated = {}

        # Calculate RSI
        if calc_all or "rsi" in requested_indicators:
            rsi = self._calculate_rsi(df_recent['Close'])
            calculated['rsi'] = rsi
            indicators_result['rsi'] = {
                "current": float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None,
                "interpretation": "Oversold (<30), Neutral (30-70), Overbought (>70)"
            }

        # Calculate MACD
        if calc_all or "macd" in requested_indicators:
            macd = self._calculate_macd(df_recent['Close'])
            calculated['macd'] = macd
            indicators_result['macd'] = {
                "macd_line": float(macd['macd_line'].iloc[-1]) if not pd.isna(macd['macd_line'].iloc[-1]) else None,
                "signal_line": float(macd['signal_line'].iloc[-1]) if not pd.isna(macd['signal_line'].iloc[-1]) else None,
                "histogram": float(macd['histogram'].iloc[-1]) if not pd.isna(macd['histogram'].iloc[-1]) else None,
                "interpretation": "Bullish when MACD > Signal, Bearish when MACD < Signal"
            }

        # Calculate Bollinger Bands
        if calc_all or "bollinger" in requested_indicators:
            bollinger = self._calculate_bollinger_bands(df_recent['Close'])
            calculated['bollinger'] = bollinger
            current_price = float(df_recent['Close'].iloc[-1])
            indicators_result['bollinger_bands'] = {
                "current_price": current_price,
                "upper_band": float(bollinger['upper_band'].iloc[-1]) if not pd.isna(bollinger['upper_band'].iloc[-1]) else None,
                "middle_band": float(bollinger['middle_band'].iloc[-1]) if not pd.isna(bollinger['middle_band'].iloc[-1]) else None,
                "lower_band": float(bollinger['lower_band'].iloc[-1]) if not pd.isna(bollinger['lower_band'].iloc[-1]) else None,
                "interpretation": "Price near upper band = overbought, near lower band = oversold"
            }

        # Calculate SMA
        if calc_all or "sma" in requested_indicators:
            sma = self._calculate_sma(df_recent['Close'])
            calculated['sma'] = sma
            indicators_result['sma'] = {
                f"sma_{period}": float(sma[f"sma_{period}"].iloc[-1]) if not pd.isna(sma[f"sma_{period}"].iloc[-1]) else None
                for period in [20, 50, 200]
                if f"sma_{period}" in sma and not pd.isna(sma[f"sma_{period}"].iloc[-1])
            }

        # Calculate EMA
        if calc_all or "ema" in requested_indicators:
            ema = self._calculate_ema(df_recent['Close'])
            calculated['ema'] = ema
            indicators_result['ema'] = {
                f"ema_{period}": float(ema[f"ema_{period}"].iloc[-1]) if not pd.isna(ema[f"ema_{period}"].iloc[-1]) else None
                for period in [12, 26, 50]
                if f"ema_{period}" in ema and not pd.isna(ema[f"ema_{period}"].iloc[-1])
            }

        # Generate trading signals
        signals = self._generate_signals(df_recent, calculated)

        # Get latest price info
        latest = df_recent.iloc[-1]

        return {
            "symbol": symbol,
            "date": latest['Date'].strftime('%Y-%m-%d'),
            "current_price": float(latest['Close']),
            "volume": int(latest['Volume']) if 'Volume' in latest else None,
            "indicators": indicators_result,
            "signals": signals,
            "summary": self._generate_summary(indicators_result, signals),
            "data_source": "Historical CSV data (5 years)"
        }

    def _generate_summary(self, indicators: Dict, signals: Dict) -> str:
        """Generate a human-readable summary"""
        summary_parts = []

        for signal_name, signal_value in signals.items():
            summary_parts.append(f"{signal_name}: {signal_value}")

        if not summary_parts:
            return "Insufficient data for signal generation"

        return " | ".join(summary_parts)


# Export for MCP server
__all__ = ['TechnicalAnalysisTool']
