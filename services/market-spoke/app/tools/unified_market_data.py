"""
Unified Market Data Tool - MCP wrapper for UnifiedAPIManager
Provides comprehensive market data access through MCP protocol
"""

import json
from typing import Dict, Any, List
# Lazy import: UnifiedAPIManager imported on-demand to reduce startup time


class UnifiedMarketDataTool:
    """MCP Tool for unified market data access"""

    def __init__(self):
        self.api_manager = None

    async def get_tool_info(self) -> Dict:
        """Get tool information for MCP protocol"""
        return {
            "name": "get_unified_data",
            "description": "Get comprehensive market data from multiple sources with intelligent fallback",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "data_type": {
                        "type": "string",
                        "enum": ["stock", "crypto", "news", "economic", "sanctions", "batch", "overview"],
                        "description": "Type of data to retrieve"
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL) or crypto coin ID (e.g., bitcoin)"
                    },
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of symbols for batch operations"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query for news or sanctions check"
                    },
                    "series_id": {
                        "type": "string",
                        "description": "FRED series ID for economic indicators (e.g., GDP)"
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results to return (default: 10)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit for economic data points (default: 10)"
                    }
                },
                "required": ["data_type"]
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments"""
        # Lazy import to reduce module load time
        from app.clients.unified_api_manager import UnifiedAPIManager

        # Support both 'data_type' and 'query_type' for compatibility
        data_type = arguments.get("data_type") or arguments.get("query_type")

        # Map query_type values to data_type values
        type_mapping = {
            "stock_quote": "stock",
            "crypto_price": "crypto",
            "news": "news",
            "economic": "economic",
            "overview": "overview"
        }

        # Convert query_type format to data_type format
        if data_type in type_mapping:
            data_type = type_mapping[data_type]

        # Create API manager context
        async with UnifiedAPIManager() as api_manager:
            if data_type == "stock":
                symbol = arguments.get("symbol")
                if not symbol:
                    return {"error": "Symbol is required for stock data"}

                result = await api_manager.get_stock_quote(symbol)
                return result if result else {"error": f"Failed to get stock quote for {symbol}"}

            elif data_type == "crypto":
                coin_id = arguments.get("symbol", "bitcoin")
                result = await api_manager.get_crypto_price(coin_id)
                return result if result else {"error": f"Failed to get crypto price for {coin_id}"}

            elif data_type == "news":
                query = arguments.get("query", "stock market")
                page_size = arguments.get("page_size", 10)
                result = await api_manager.get_financial_news(query, page_size)
                return {"articles": result} if result else {"error": "Failed to get news"}

            elif data_type == "economic":
                # Support both 'series_id' and 'indicator' for compatibility
                series_id = arguments.get("series_id") or arguments.get("indicator", "GDP")
                limit = arguments.get("limit", 10)
                result = await api_manager.get_economic_indicator(series_id, limit)
                return result if result else {"error": f"Failed to get economic data for {series_id}"}

            elif data_type == "sanctions":
                query = arguments.get("query")
                if not query:
                    return {"error": "Query is required for sanctions check"}

                result = await api_manager.check_sanctions(query)
                return result if result else {"error": f"Failed to check sanctions for {query}"}

            elif data_type == "batch":
                symbols = arguments.get("symbols")
                if not symbols:
                    return {"error": "Symbols list is required for batch operations"}

                result = await api_manager.get_multiple_quotes(symbols)
                return {"quotes": result}

            elif data_type == "overview":
                result = await api_manager.get_market_overview()
                return result if result else {"error": "Failed to get market overview"}

            else:
                return {"error": f"Unknown data type: {data_type}"}


class StockQuoteTool:
    """Simplified tool for stock quotes"""

    async def get_tool_info(self) -> Dict:
        return {
            "name": "get_stock_quote",
            "description": "Get real-time stock quote with intelligent API fallback (Finnhub -> Alpha Vantage -> MarketStack)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, GOOGL, MSFT)"
                    }
                },
                "required": ["symbol"]
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Lazy import to reduce module load time
        from app.clients.unified_api_manager import UnifiedAPIManager

        symbol = arguments.get("symbol")
        if not symbol:
            return {"error": "Symbol is required"}

        async with UnifiedAPIManager() as api_manager:
            result = await api_manager.get_stock_quote(symbol)
            return result if result else {"error": f"Failed to get stock quote for {symbol}"}


class CryptoPriceTool:
    """Simplified tool for cryptocurrency prices"""

    async def get_tool_info(self) -> Dict:
        return {
            "name": "get_crypto_price",
            "description": "Get cryptocurrency price from CoinGecko with caching",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "coin_id": {
                        "type": "string",
                        "description": "CoinGecko coin ID (e.g., bitcoin, ethereum, ripple)"
                    }
                },
                "required": ["coin_id"]
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Lazy import to reduce module load time
        from app.clients.unified_api_manager import UnifiedAPIManager

        coin_id = arguments.get("coin_id", "bitcoin")

        async with UnifiedAPIManager() as api_manager:
            result = await api_manager.get_crypto_price(coin_id)
            return result if result else {"error": f"Failed to get crypto price for {coin_id}"}


class FinancialNewsTool:
    """Tool for financial news with sentiment analysis"""

    async def get_tool_info(self) -> Dict:
        return {
            "name": "get_financial_news",
            "description": "Get financial news with automatic sentiment analysis",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "News search query (e.g., 'tech stocks', 'Bitcoin', 'Federal Reserve')"
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of articles to return (default: 10, max: 100)"
                    }
                },
                "required": ["query"]
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Lazy import to reduce module load time
        from app.clients.unified_api_manager import UnifiedAPIManager

        query = arguments.get("query", "stock market")
        page_size = arguments.get("page_size", 10)

        async with UnifiedAPIManager() as api_manager:
            result = await api_manager.get_financial_news(query, page_size)
            return {"articles": result, "count": len(result)} if result else {"error": "Failed to get news"}


class EconomicIndicatorTool:
    """Tool for FRED economic indicators"""

    async def get_tool_info(self) -> Dict:
        return {
            "name": "get_economic_indicator",
            "description": "Get economic indicators from Federal Reserve Economic Data (FRED)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "string",
                        "description": "FRED series ID (e.g., GDP, UNRATE, CPIAUCSL, DFF)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of observations to return (default: 10)"
                    }
                },
                "required": ["series_id"]
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Lazy import to reduce module load time
        from app.clients.unified_api_manager import UnifiedAPIManager

        series_id = arguments.get("series_id", "GDP")
        limit = arguments.get("limit", 10)

        async with UnifiedAPIManager() as api_manager:
            result = await api_manager.get_economic_indicator(series_id, limit)
            return result if result else {"error": f"Failed to get economic data for {series_id}"}


class MarketOverviewTool:
    """Tool for comprehensive market overview"""

    async def get_tool_info(self) -> Dict:
        return {
            "name": "get_overview",
            "description": "Get comprehensive market overview including indices, crypto, news, and economic data",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Lazy import to reduce module load time
        from app.clients.unified_api_manager import UnifiedAPIManager

        async with UnifiedAPIManager() as api_manager:
            result = await api_manager.get_market_overview()
            return result if result else {"error": "Failed to get market overview"}


class APIStatusTool:
    """Tool for checking API health and status"""

    async def get_tool_info(self) -> Dict:
        return {
            "name": "get_api_status",
            "description": "Get status of all configured financial APIs",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Lazy import to reduce module load time
        from app.clients.unified_api_manager import UnifiedAPIManager

        async with UnifiedAPIManager() as api_manager:
            # Trigger a test call first
            await api_manager.get_stock_quote("AAPL")
            return api_manager.get_api_status()
