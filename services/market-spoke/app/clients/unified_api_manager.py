#!/usr/bin/env python3
"""
Unified API Manager for Market Spoke
Integrates all financial data APIs with intelligent fallback and caching
"""

import os
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

# Load environment variables
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent.parent.parent.parent
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path)

logger = logging.getLogger(__name__)


class UnifiedAPIManager:
    """
    Unified manager for all financial APIs with intelligent routing and fallback
    """

    def __init__(self):
        """Initialize with all API keys from environment"""
        self.api_keys = {
            'finnhub': os.getenv('FINNHUB_API_KEY'),
            'alpha_vantage': os.getenv('ALPHA_VANTAGE_API_KEY'),
            'news_api': os.getenv('NEWS_API_KEY'),
            'coingecko': os.getenv('COINGECKO_API_KEY'),
            'fred': os.getenv('FRED_API_KEY'),
            'opensanctions': os.getenv('OPENSANCTIONS_API_KEY'),
            'marketstack': os.getenv('MARKETSTACK_API_KEY'),
        }

        self.session = None
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes default

        # API status tracking
        self.api_status = {
            api: {"available": True, "last_error": None, "rate_limit_reset": None}
            for api in self.api_keys.keys()
        }

    async def __aenter__(self):
        """Async context manager entry"""
        # Configure timeout for all requests (30 seconds total, 10 seconds connect)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        # Configure connector with DNS caching
        connector = aiohttp.TCPConnector(ttl_dns_cache=300)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    # ==================== Stock Data ====================

    async def get_stock_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get real-time stock quote with intelligent API selection
        Priority: Finnhub -> Alpha Vantage -> MarketStack
        """
        # Try Finnhub first
        if self.api_status['finnhub']['available']:
            try:
                return await self._get_finnhub_quote(symbol)
            except Exception as e:
                logger.warning(f"Finnhub failed: {e}")
                self.api_status['finnhub']['available'] = False

        # Fallback to Alpha Vantage
        if self.api_status['alpha_vantage']['available']:
            try:
                return await self._get_alpha_vantage_quote(symbol)
            except Exception as e:
                logger.warning(f"Alpha Vantage failed: {e}")

        # Last resort: MarketStack
        if self.api_status['marketstack']['available']:
            try:
                return await self._get_marketstack_quote(symbol)
            except Exception as e:
                logger.error(f"All stock APIs failed for {symbol}")

        return None

    async def _get_finnhub_quote(self, symbol: str) -> Dict:
        """Get quote from Finnhub"""
        url = "https://finnhub.io/api/v1/quote"
        params = {
            "symbol": symbol,
            "token": self.api_keys['finnhub']
        }

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()

            return {
                "symbol": symbol,
                "price": data.get("c"),  # current price
                "change": data.get("d"),  # change
                "change_percent": data.get("dp"),  # change percent
                "high": data.get("h"),
                "low": data.get("l"),
                "open": data.get("o"),
                "previous_close": data.get("pc"),
                "timestamp": datetime.now().isoformat(),
                "source": "finnhub"
            }

    async def _get_alpha_vantage_quote(self, symbol: str) -> Dict:
        """Get quote from Alpha Vantage"""
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.api_keys['alpha_vantage']
        }

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()

            quote = data.get("Global Quote", {})

            # Parse change percent (remove % sign and convert to float)
            change_percent_str = quote.get("10. change percent", "0%")
            change_percent = float(change_percent_str.rstrip('%'))

            return {
                "symbol": quote.get("01. symbol"),
                "price": float(quote.get("05. price", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_percent": change_percent,
                "high": float(quote.get("03. high", 0)),
                "low": float(quote.get("04. low", 0)),
                "open": float(quote.get("02. open", 0)),
                "volume": int(quote.get("06. volume", 0)),
                "timestamp": quote.get("07. latest trading day"),
                "source": "alpha_vantage"
            }

    async def _get_marketstack_quote(self, symbol: str) -> Dict:
        """Get quote from MarketStack"""
        url = "http://api.marketstack.com/v1/eod/latest"
        params = {
            "access_key": self.api_keys['marketstack'],
            "symbols": symbol,
            "limit": 1
        }

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()

            if not data.get("data"):
                raise ValueError("No data returned")

            stock = data["data"][0]
            return {
                "symbol": stock.get("symbol"),
                "price": stock.get("close"),
                "change": stock.get("close") - stock.get("open"),
                "high": stock.get("high"),
                "low": stock.get("low"),
                "open": stock.get("open"),
                "volume": stock.get("volume"),
                "timestamp": stock.get("date"),
                "source": "marketstack"
            }

    # ==================== Cryptocurrency Data ====================

    async def get_crypto_price(self, coin_id: str = "bitcoin") -> Optional[Dict]:
        """
        Get cryptocurrency price from CoinGecko
        """
        cache_key = f"crypto_{coin_id}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self.cache_ttl):
                return cached_data

        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
                "include_market_cap": "true"
            }
            headers = {}
            if self.api_keys['coingecko']:
                headers["x-cg-pro-api-key"] = self.api_keys['coingecko']

            async with self.session.get(url, params=params, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                result = {
                    "coin_id": coin_id,
                    "price": data[coin_id]["usd"],
                    "change_24h": data[coin_id].get("usd_24h_change", 0),
                    "volume_24h": data[coin_id].get("usd_24h_vol", 0),
                    "market_cap": data[coin_id].get("usd_market_cap", 0),
                    "timestamp": datetime.now().isoformat(),
                    "source": "coingecko"
                }

                # Cache result
                self.cache[cache_key] = (result, datetime.now())
                return result

        except Exception as e:
            logger.error(f"CoinGecko failed for {coin_id}: {e}")
            return None

    # ==================== News Data ====================

    async def get_financial_news(
        self,
        query: str = "stock market",
        page_size: int = 10
    ) -> Optional[List[Dict]]:
        """
        Get financial news from News API
        """
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "sortBy": "publishedAt",
                "pageSize": page_size,
                "apiKey": self.api_keys['news_api']
            }

            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                if data.get("status") != "ok":
                    return None

                articles = []
                for article in data.get("articles", []):
                    articles.append({
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "url": article.get("url"),
                        "source": article.get("source", {}).get("name"),
                        "published_at": article.get("publishedAt"),
                        "sentiment": self._analyze_sentiment(article.get("title", "")),
                    })

                return articles

        except Exception as e:
            logger.error(f"News API failed: {e}")
            return None

    def _analyze_sentiment(self, text: str) -> str:
        """Simple sentiment analysis"""
        positive_keywords = ["surge", "gain", "profit", "growth", "rise", "bullish", "strong"]
        negative_keywords = ["fall", "loss", "decline", "crash", "bearish", "weak", "drop"]

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_keywords if word in text_lower)
        negative_count = sum(1 for word in negative_keywords if word in text_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    # ==================== Economic Indicators ====================

    async def get_economic_indicator(
        self,
        series_id: str = "GDP",
        limit: int = 10
    ) -> Optional[Dict]:
        """
        Get economic indicators from FRED
        """
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": series_id,
                "api_key": self.api_keys['fred'],
                "file_type": "json",
                "sort_order": "desc",
                "limit": limit
            }

            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                observations = data.get("observations", [])
                if not observations:
                    return None

                return {
                    "series_id": series_id,
                    "observations": [
                        {
                            "date": obs.get("date"),
                            "value": obs.get("value")
                        }
                        for obs in observations
                    ],
                    "timestamp": datetime.now().isoformat(),
                    "source": "fred"
                }

        except Exception as e:
            logger.error(f"FRED API failed: {e}")
            return None

    # ==================== Compliance Check ====================

    async def check_sanctions(self, entity_name: str) -> Optional[Dict]:
        """
        Check sanctions list via OpenSanctions
        """
        try:
            url = "https://api.opensanctions.org/search/default"
            params = {"q": entity_name}
            headers = {"Authorization": f"ApiKey {self.api_keys['opensanctions']}"}

            async with self.session.get(url, params=params, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                return {
                    "query": entity_name,
                    "total_results": data.get("total", {}).get("value", 0),
                    "results": data.get("results", [])[:5],  # Top 5 matches
                    "timestamp": datetime.now().isoformat(),
                    "source": "opensanctions"
                }

        except Exception as e:
            logger.error(f"OpenSanctions failed: {e}")
            return None

    # ==================== Batch Operations ====================

    async def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get quotes for multiple symbols in parallel
        """
        tasks = [self.get_stock_quote(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            symbol: result if not isinstance(result, Exception) else None
            for symbol, result in zip(symbols, results)
        }

    async def get_market_overview(self) -> Dict:
        """
        Get comprehensive market overview
        """
        tasks = {
            "spy": self.get_stock_quote("SPY"),  # S&P 500 ETF
            "qqq": self.get_stock_quote("QQQ"),  # NASDAQ ETF
            "dia": self.get_stock_quote("DIA"),  # Dow Jones ETF
            "bitcoin": self.get_crypto_price("bitcoin"),
            "ethereum": self.get_crypto_price("ethereum"),
            "news": self.get_financial_news("stock market", 5),
            "gdp": self.get_economic_indicator("GDP", 1),
        }

        results = {}
        for key, task in tasks.items():
            try:
                results[key] = await task
            except Exception as e:
                logger.error(f"Failed to get {key}: {e}")
                results[key] = None

        return {
            "timestamp": datetime.now().isoformat(),
            "indices": {
                "sp500": results.get("spy"),
                "nasdaq": results.get("qqq"),
                "dow": results.get("dia"),
            },
            "crypto": {
                "bitcoin": results.get("bitcoin"),
                "ethereum": results.get("ethereum"),
            },
            "news": results.get("news"),
            "economic": {
                "gdp": results.get("gdp"),
            }
        }

    # ==================== Health Check ====================

    def get_api_status(self) -> Dict:
        """
        Get status of all APIs
        """
        return {
            "apis": self.api_status,
            "configured_keys": {
                api: bool(key) for api, key in self.api_keys.items()
            },
            "timestamp": datetime.now().isoformat()
        }


# ==================== Example Usage ====================

async def main():
    """Example usage"""
    async with UnifiedAPIManager() as api_manager:
        # Test stock quote
        print("Testing stock quote...")
        quote = await api_manager.get_stock_quote("AAPL")
        print(f"AAPL: ${quote['price']} ({quote['change_percent']})")

        # Test crypto
        print("\nTesting crypto...")
        btc = await api_manager.get_crypto_price("bitcoin")
        print(f"Bitcoin: ${btc['price']:,.2f} ({btc['change_24h']:.2f}%)")

        # Test market overview
        print("\nTesting market overview...")
        overview = await api_manager.get_market_overview()
        print(json.dumps(overview, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
