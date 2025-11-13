#!/usr/bin/env python3
"""
Market Spoke MCP Server - MCP SDK Implementation (Optimized with Lazy Loading)
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables only if needed
if not os.getenv('ALPHA_VANTAGE_API_KEY'):
    from dotenv import load_dotenv
    load_dotenv(project_root / '.env')

# Minimal logging - disable all
import logging
logging.disable(logging.CRITICAL)

# MCP imports (InitializationOptions is lazy-loaded in main())
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types

# Add services directory to path
sys.path.insert(0, str(project_root / 'services' / 'market-spoke'))

# Create MCP server
server = Server("fin-hub-market")

# Lazy initialization - tools AND imports created on demand
_tool_instances = {}

def get_tool_instance(tool_name: str):
    """Get or create tool instance (lazy loading with imports)"""
    if tool_name not in _tool_instances:
        if tool_name == "unified":
            from app.tools.unified_market_data import UnifiedMarketDataTool
            _tool_instances[tool_name] = UnifiedMarketDataTool()
        elif tool_name == "stock_quote":
            from app.tools.unified_market_data import StockQuoteTool
            _tool_instances[tool_name] = StockQuoteTool()
        elif tool_name == "crypto":
            from app.tools.unified_market_data import CryptoPriceTool
            _tool_instances[tool_name] = CryptoPriceTool()
        elif tool_name == "news":
            from app.tools.unified_market_data import FinancialNewsTool
            _tool_instances[tool_name] = FinancialNewsTool()
        elif tool_name == "economic":
            from app.tools.unified_market_data import EconomicIndicatorTool
            _tool_instances[tool_name] = EconomicIndicatorTool()
        elif tool_name == "overview":
            from app.tools.unified_market_data import MarketOverviewTool
            _tool_instances[tool_name] = MarketOverviewTool()
        elif tool_name == "status":
            from app.tools.unified_market_data import APIStatusTool
            _tool_instances[tool_name] = APIStatusTool()
        elif tool_name == "technical":
            from app.tools.technical_analysis import TechnicalAnalysisTool
            _tool_instances[tool_name] = TechnicalAnalysisTool()
        elif tool_name == "pattern":
            from app.tools.pattern_recognition import PatternRecognitionTool
            _tool_instances[tool_name] = PatternRecognitionTool()
        elif tool_name == "anomaly":
            from app.tools.anomaly_detection import AnomalyDetectionTool
            _tool_instances[tool_name] = AnomalyDetectionTool()
        elif tool_name == "comparison":
            from app.tools.stock_comparison import StockComparisonTool
            _tool_instances[tool_name] = StockComparisonTool()
        elif tool_name == "sentiment":
            from app.tools.sentiment_analysis import SentimentAnalysisTool
            _tool_instances[tool_name] = SentimentAnalysisTool()
        elif tool_name == "alert":
            from app.tools.alert_system import AlertSystemTool
            _tool_instances[tool_name] = AlertSystemTool()
    return _tool_instances[tool_name]


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available market data tools (13 tools) - optimized with hardcoded schemas"""
    return [
        types.Tool(
            name="unified_market_data",
            description="Get comprehensive market data from multiple sources with automatic fallback",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "description": "Type of market data",
                        "enum": ["stock_quote", "crypto_price", "news", "economic", "overview"]
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Stock/crypto symbol (e.g., AAPL, BTC)"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query for news"
                    },
                    "indicator": {
                        "type": "string",
                        "description": "Economic indicator code (e.g., GDP, CPI)"
                    }
                },
                "required": ["query_type"]
            }
        ),
        types.Tool(
            name="stock_quote",
            description="Get real-time stock quote data",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="crypto_price",
            description="Get cryptocurrency price data",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Cryptocurrency symbol (e.g., BTC, ETH)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="financial_news",
            description="Get latest financial news",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "News search query (e.g., 'Tesla earnings', 'Fed interest rates')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of news articles to return (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="economic_indicator",
            description="Get economic indicator data",
            inputSchema={
                "type": "object",
                "properties": {
                    "indicator": {
                        "type": "string",
                        "description": "Economic indicator code (e.g., GDP, CPI, UNRATE)"
                    }
                },
                "required": ["indicator"]
            }
        ),
        types.Tool(
            name="market_overview",
            description="Get comprehensive market overview including major indices",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="api_status",
            description="Check status and availability of all data provider APIs",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="technical_analysis",
            description="Perform comprehensive technical analysis with indicators like RSI, MACD, Bollinger Bands, and Moving Averages",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)"
                    },
                    "indicators": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["rsi", "macd", "bollinger", "sma", "ema", "all"]
                        },
                        "description": "List of indicators to calculate (default: all)"
                    },
                    "period": {
                        "type": "integer",
                        "description": "Number of days for analysis (default: 30)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="pattern_recognition",
            description="Detect chart patterns, support/resistance levels, and trend analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, MSFT)"
                    },
                    "period": {
                        "type": "integer",
                        "description": "Number of days for analysis (default: 60)"
                    },
                    "patterns": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["trend", "support_resistance", "head_shoulders", "double_top_bottom", "triangle", "all"]
                        },
                        "description": "Patterns to detect (default: all)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="anomaly_detection",
            description="Detect price and volume anomalies using statistical methods (Z-Score, IQR, Volatility)",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, MSFT)"
                    },
                    "period": {
                        "type": "integer",
                        "description": "Number of days for analysis (default: 90)"
                    },
                    "sensitivity": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Detection sensitivity (default: medium)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="stock_comparison",
            description="Compare multiple stocks for correlation, performance, and relative analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of stock symbols to compare (2-10 stocks)"
                    },
                    "period": {
                        "type": "integer",
                        "description": "Number of days for analysis (default: 90)"
                    },
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["correlation", "performance", "volatility", "risk_return", "all"]
                        },
                        "description": "Metrics to compare (default: all)"
                    }
                },
                "required": ["symbols"]
            }
        ),
        types.Tool(
            name="sentiment_analysis",
            description="Enhanced sentiment analysis combining news sentiment with market data scoring (1-5 scale)",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, MSFT)"
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional search query (default: company name from symbol)"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to analyze (default: 7)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="alert_system",
            description="Monitor stocks and create alerts for price movements, breakouts, and pattern detection",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, MSFT)"
                    },
                    "alert_type": {
                        "type": "string",
                        "enum": ["price_target", "percent_change", "volume_spike", "breakout", "support_resistance", "volatility", "all"],
                        "description": "Type of alert to check"
                    },
                    "thresholds": {
                        "type": "object",
                        "description": "Alert thresholds"
                    }
                },
                "required": ["symbol", "alert_type"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution (13 tools) - using lazy loading"""
    import json

    arguments = arguments or {}

    try:
        # Route to appropriate tool with lazy initialization
        if name == "unified_market_data":
            result = await get_tool_instance("unified").execute(arguments)
        elif name == "stock_quote":
            result = await get_tool_instance("stock_quote").execute(arguments)
        elif name == "crypto_price":
            result = await get_tool_instance("crypto").execute(arguments)
        elif name == "financial_news":
            result = await get_tool_instance("news").execute(arguments)
        elif name == "economic_indicator":
            result = await get_tool_instance("economic").execute(arguments)
        elif name == "market_overview":
            result = await get_tool_instance("overview").execute(arguments)
        elif name == "api_status":
            result = await get_tool_instance("status").execute(arguments)
        elif name == "technical_analysis":
            result = await get_tool_instance("technical").execute(arguments)
        elif name == "pattern_recognition":
            result = await get_tool_instance("pattern").execute(arguments)
        elif name == "anomaly_detection":
            result = await get_tool_instance("anomaly").execute(arguments)
        elif name == "stock_comparison":
            result = await get_tool_instance("comparison").execute(arguments)
        elif name == "sentiment_analysis":
            result = await get_tool_instance("sentiment").execute(arguments)
        elif name == "alert_system":
            result = await get_tool_instance("alert").execute(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": f"Tool execution failed: {str(e)}"}, indent=2)
        )]


async def main():
    """Run the MCP server"""
    # Lazy import of InitializationOptions (saves 6 seconds on startup)
    from mcp.server.models import InitializationOptions

    # Import original stdout/stdin for MCP communication
    import sys
    original_stdin = sys.__stdin__
    original_stdout = sys.__stdout__

    # Temporarily restore stdout for MCP SDK
    sys.stdin = original_stdin
    sys.stdout = original_stdout

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="fin-hub-market",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
