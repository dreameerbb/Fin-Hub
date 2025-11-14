#!/usr/bin/env python3
"""
Hub Server MCP Server - Integrated with All Spoke Tools (Lazy Loading)
Provides all Market, Risk, and Portfolio tools through a single Hub interface
"""
import sys
import os
from pathlib import Path

# Add project root to path - use relative path from this file
# This works in both local development and Docker deployment
# Environment variable FIN_HUB_ROOT can override if needed
project_root = Path(
    os.getenv('FIN_HUB_ROOT', Path(__file__).parent.parent.parent)
).resolve()

# Define spoke directories (but don't add to sys.path yet to avoid conflicts)
market_spoke = project_root / 'services' / 'market-spoke'
risk_spoke = project_root / 'services' / 'risk-spoke'
portfolio_spoke = project_root / 'services' / 'portfolio-spoke'

# Add only project root to sys.path initially
sys.path.insert(0, str(project_root))

# Verify paths exist
if not market_spoke.exists():
    sys.stderr.write(f"[ERROR] Market spoke path does not exist: {market_spoke}\n")
if not risk_spoke.exists():
    sys.stderr.write(f"[ERROR] Risk spoke path does not exist: {risk_spoke}\n")
if not portfolio_spoke.exists():
    sys.stderr.write(f"[ERROR] Portfolio spoke path does not exist: {portfolio_spoke}\n")

# Load environment variables
if not os.getenv('ENVIRONMENT'):
    from dotenv import load_dotenv
    load_dotenv(project_root / '.env')

# Enhanced logging for monitoring
import logging
from datetime import datetime

# Create detailed logger
logger = logging.getLogger("mcp_monitor")
logger.setLevel(logging.DEBUG)

# File handler
log_file = Path(__file__).parent.parent.parent / "mcp_monitor.log"
file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setLevel(logging.DEBUG)

# Console handler (stderr)
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Disable other logging
logging.getLogger().setLevel(logging.CRITICAL)

# Pre-import heavy libraries to reduce first tool call latency
# This adds ~240s to server startup but makes first tool calls instant
logger.info("Pre-loading heavy libraries (pandas, numpy)...")
import pandas as pd
import numpy as np
logger.info("Heavy libraries loaded successfully")

# MCP imports
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types

# Create MCP server
server = Server("fin-hub-integrated")

# ============================================================================
# Hub Management Tools
# ============================================================================

from typing import Dict, List, Any
from datetime import datetime
import asyncio

class HubTools:
    """Hub management and orchestration tools"""

    def __init__(self):
        # Built-in Spokes (always available)
        self.builtin_spokes = {
            "market": {"tool_count": 13, "type": "builtin", "description": "Market data and analysis"},
            "risk": {"tool_count": 8, "type": "builtin", "description": "Risk management"},
            "portfolio": {"tool_count": 8, "type": "builtin", "description": "Portfolio optimization"}
        }

        # External Spokes (dynamically registered via HTTP)
        self.external_spokes = {}

    async def hub_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive Hub status"""
        total_builtin = sum(s["tool_count"] for s in self.builtin_spokes.values())
        total_external = sum(s.get("tool_count", 0) for s in self.external_spokes.values())

        return {
            "hub": {
                "name": "fin-hub-integrated",
                "version": "1.0.0",
                "status": "operational",
                "mode": "hybrid"
            },
            "builtin_spokes": {
                "count": len(self.builtin_spokes),
                "tools": total_builtin,
                "spokes": list(self.builtin_spokes.keys())
            },
            "external_spokes": {
                "count": len(self.external_spokes),
                "tools": total_external,
                "spokes": list(self.external_spokes.keys())
            },
            "total_tools": total_builtin + total_external + 15,  # +15 for Hub tools
            "timestamp": datetime.now().isoformat()
        }

    async def register_spoke(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Register external Spoke service"""
        spoke_name = arguments.get("spoke_name")
        endpoint = arguments.get("endpoint")
        tool_count = arguments.get("tool_count", 0)
        description = arguments.get("description", "")

        if not spoke_name or not endpoint:
            return {"error": "spoke_name and endpoint required"}

        if spoke_name in self.builtin_spokes:
            return {"error": f"'{spoke_name}' is a builtin spoke, cannot register"}

        self.external_spokes[spoke_name] = {
            "endpoint": endpoint,
            "tool_count": tool_count,
            "description": description,
            "type": "external",
            "registered_at": datetime.now().isoformat()
        }

        return {
            "success": True,
            "message": f"Spoke '{spoke_name}' registered",
            "config": self.external_spokes[spoke_name]
        }

    async def unregister_spoke(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Unregister external Spoke"""
        spoke_name = arguments.get("spoke_name")

        if not spoke_name:
            return {"error": "spoke_name required"}

        if spoke_name in self.builtin_spokes:
            return {"error": "Cannot unregister builtin spokes"}

        if spoke_name not in self.external_spokes:
            return {"error": f"Spoke '{spoke_name}' not found"}

        removed = self.external_spokes.pop(spoke_name)
        return {
            "success": True,
            "message": f"Spoke '{spoke_name}' unregistered",
            "removed_config": removed
        }

    async def list_all_tools(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all available tools across all spokes"""
        tools_by_spoke = {}

        # Builtin tools
        for spoke_name, config in self.builtin_spokes.items():
            tools_by_spoke[spoke_name] = {
                "type": "builtin",
                "tool_count": config["tool_count"],
                "description": config["description"],
                "status": "available"
            }

        # External tools
        for spoke_name, config in self.external_spokes.items():
            tools_by_spoke[spoke_name] = {
                "type": "external",
                "tool_count": config["tool_count"],
                "endpoint": config["endpoint"],
                "status": "registered"
            }

        return {
            "hub_tools": 15,
            "spoke_tools": tools_by_spoke,
            "total_spokes": len(self.builtin_spokes) + len(self.external_spokes),
            "total_tools": sum(s["tool_count"] for s in tools_by_spoke.values()) + 15
        }

    async def search_tools(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for tools by keyword"""
        query = arguments.get("query", "").lower()
        category = arguments.get("category", "all")

        # Tool database (simplified)
        all_tools = {
            "market": ["stock_quote", "crypto_price", "financial_news", "technical_analysis",
                      "pattern_recognition", "sentiment_analysis"],
            "risk": ["risk_calculate_var", "risk_stress_test", "risk_calculate_greeks",
                    "risk_check_compliance"],
            "portfolio": ["portfolio_optimize", "portfolio_backtest", "portfolio_rebalance"]
        }

        results = []
        for spoke, tools in all_tools.items():
            if category != "all" and category != spoke:
                continue

            for tool in tools:
                if query in tool.lower():
                    results.append({
                        "tool": tool,
                        "spoke": spoke,
                        "type": "builtin"
                    })

        return {
            "query": query,
            "category": category,
            "results_count": len(results),
            "results": results
        }

# Initialize Hub tools
hub_tools = HubTools()

# ============================================================================
# Lazy Loading Tool Instances
# ============================================================================

_tool_instances = {}

def get_market_tool(tool_name: str):
    """Get market spoke tool instance (lazy loading)"""
    if tool_name not in _tool_instances:
        # Clean up other spokes from sys.path to avoid conflicts
        for spoke_path in [str(risk_spoke), str(portfolio_spoke)]:
            while spoke_path in sys.path:
                sys.path.remove(spoke_path)

        # Add market-spoke to sys.path[0] for import
        market_spoke_str = str(market_spoke)
        if market_spoke_str in sys.path:
            sys.path.remove(market_spoke_str)
        sys.path.insert(0, market_spoke_str)

        # DEBUG: Log sys.path to diagnose import issues
        logger.debug(f"sys.path at import time:")
        for i, path in enumerate(sys.path[:5]):  # First 5 paths
            logger.debug(f"  [{i}] {path}")

        if tool_name == "unified_market_data":
            from app.tools.unified_market_data import UnifiedMarketDataTool
            _tool_instances[tool_name] = UnifiedMarketDataTool()
        elif tool_name == "stock_quote":
            from app.tools.unified_market_data import StockQuoteTool
            _tool_instances[tool_name] = StockQuoteTool()
        elif tool_name == "crypto_price":
            from app.tools.unified_market_data import CryptoPriceTool
            _tool_instances[tool_name] = CryptoPriceTool()
        elif tool_name == "financial_news":
            from app.tools.unified_market_data import FinancialNewsTool
            _tool_instances[tool_name] = FinancialNewsTool()
        elif tool_name == "economic_indicator":
            from app.tools.unified_market_data import EconomicIndicatorTool
            _tool_instances[tool_name] = EconomicIndicatorTool()
        elif tool_name == "market_overview":
            from app.tools.unified_market_data import MarketOverviewTool
            _tool_instances[tool_name] = MarketOverviewTool()
        elif tool_name == "api_status":
            from app.tools.unified_market_data import APIStatusTool
            _tool_instances[tool_name] = APIStatusTool()
        elif tool_name == "technical_analysis":
            from app.tools.technical_analysis import TechnicalAnalysisTool
            _tool_instances[tool_name] = TechnicalAnalysisTool()
        elif tool_name == "pattern_recognition":
            from app.tools.pattern_recognition import PatternRecognitionTool
            _tool_instances[tool_name] = PatternRecognitionTool()
        elif tool_name == "anomaly_detection":
            from app.tools.anomaly_detection import AnomalyDetectionTool
            _tool_instances[tool_name] = AnomalyDetectionTool()
        elif tool_name == "stock_comparison":
            from app.tools.stock_comparison import StockComparisonTool
            _tool_instances[tool_name] = StockComparisonTool()
        elif tool_name == "sentiment_analysis":
            from app.tools.sentiment_analysis import SentimentAnalysisTool
            _tool_instances[tool_name] = SentimentAnalysisTool()
        elif tool_name == "alert_system":
            from app.tools.alert_system import AlertSystemTool
            _tool_instances[tool_name] = AlertSystemTool()
    return _tool_instances[tool_name]

def get_risk_tool(tool_name: str):
    """Get risk spoke tool instance (lazy loading)"""
    if tool_name not in _tool_instances:
        # Clean up other spokes from sys.path to avoid conflicts
        for spoke_path in [str(market_spoke), str(portfolio_spoke)]:
            while spoke_path in sys.path:
                sys.path.remove(spoke_path)

        # Add risk-spoke to sys.path[0] for import
        risk_spoke_str = str(risk_spoke)
        if risk_spoke_str in sys.path:
            sys.path.remove(risk_spoke_str)
        sys.path.insert(0, risk_spoke_str)

        if tool_name == "risk_calculate_var":
            from app.tools.var_calculator import VaRCalculatorTool
            _tool_instances[tool_name] = VaRCalculatorTool()
        elif tool_name == "risk_calculate_metrics":
            from app.tools.risk_metrics import RiskMetricsTool
            _tool_instances[tool_name] = RiskMetricsTool()
        elif tool_name == "risk_analyze_portfolio":
            from app.tools.portfolio_risk import PortfolioRiskTool
            _tool_instances[tool_name] = PortfolioRiskTool()
        elif tool_name == "risk_stress_test":
            from app.tools.stress_testing import StressTestingTool
            _tool_instances[tool_name] = StressTestingTool()
        elif tool_name == "risk_analyze_tail_risk":
            from app.tools.tail_risk import TailRiskTool
            _tool_instances[tool_name] = TailRiskTool()
        elif tool_name == "risk_calculate_greeks":
            from app.tools.greeks_calculator import GreeksCalculatorTool
            _tool_instances[tool_name] = GreeksCalculatorTool()
        elif tool_name == "risk_check_compliance":
            from app.tools.compliance_checker import ComplianceCheckerTool
            _tool_instances[tool_name] = ComplianceCheckerTool()
        elif tool_name == "risk_generate_dashboard":
            from app.tools.risk_dashboard import RiskDashboardTool
            _tool_instances[tool_name] = RiskDashboardTool()
    return _tool_instances[tool_name]

def get_portfolio_tool(tool_name: str):
    """Get portfolio spoke tool instance (lazy loading)"""
    if tool_name not in _tool_instances:
        # Clean up other spokes from sys.path to avoid conflicts
        for spoke_path in [str(market_spoke), str(risk_spoke)]:
            while spoke_path in sys.path:
                sys.path.remove(spoke_path)

        # Add portfolio-spoke to sys.path[0] for import
        portfolio_spoke_str = str(portfolio_spoke)
        if portfolio_spoke_str in sys.path:
            sys.path.remove(portfolio_spoke_str)
        sys.path.insert(0, portfolio_spoke_str)

        # DEBUG: Log sys.path
        logger.debug(f"[Portfolio] sys.path at import time:")
        for i, path in enumerate(sys.path[:5]):
            logger.debug(f"  [{i}] {path}")

        if tool_name == "portfolio_optimize":
            from app.tools.portfolio_optimizer import portfolio_optimizer
            _tool_instances[tool_name] = portfolio_optimizer
        elif tool_name == "portfolio_rebalance":
            from app.tools.portfolio_rebalancer import portfolio_rebalancer
            _tool_instances[tool_name] = portfolio_rebalancer
        elif tool_name == "portfolio_analyze_performance":
            from app.tools.performance_analyzer import performance_analyzer
            _tool_instances[tool_name] = performance_analyzer
        elif tool_name == "portfolio_backtest":
            from app.tools.backtester import backtester
            _tool_instances[tool_name] = backtester
        elif tool_name == "portfolio_analyze_factors":
            from app.tools.factor_analyzer import factor_analyzer
            _tool_instances[tool_name] = factor_analyzer
        elif tool_name == "portfolio_allocate_assets":
            from app.tools.asset_allocator import asset_allocator
            _tool_instances[tool_name] = asset_allocator
        elif tool_name == "portfolio_optimize_tax":
            from app.tools.tax_optimizer import tax_optimizer
            _tool_instances[tool_name] = tax_optimizer
        elif tool_name == "portfolio_generate_dashboard":
            from app.tools.portfolio_dashboard import portfolio_dashboard
            _tool_instances[tool_name] = portfolio_dashboard
    return _tool_instances[tool_name]

# ============================================================================
# MCP Server Handlers
# ============================================================================

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available tools (Market 13 + Risk 8 + Portfolio 8 + Hub 5 = 34 tools)"""
    return [
        # === MARKET SPOKE TOOLS (13) ===
        types.Tool(
            name="unified_market_data",
            description="[MARKET] Get comprehensive market data from multiple sources with automatic fallback",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["stock_quote", "crypto_price", "news", "economic", "overview"],
                        "description": "Type of market data"
                    },
                    "symbol": {"type": "string", "description": "Stock/crypto symbol"},
                    "query": {"type": "string", "description": "Search query for news"},
                    "indicator": {"type": "string", "description": "Economic indicator code"}
                },
                "required": ["query_type"]
            }
        ),
        types.Tool(
            name="stock_quote",
            description="[MARKET] Get real-time stock quote data",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker (e.g., AAPL)"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="crypto_price",
            description="[MARKET] Get cryptocurrency price data",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Crypto symbol (e.g., BTC)"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="financial_news",
            description="[MARKET] Get latest financial news",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "News search query"},
                    "limit": {"type": "integer", "description": "Number of articles (default: 10)"}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="economic_indicator",
            description="[MARKET] Get economic indicators from FRED",
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id": {"type": "string", "description": "FRED series ID (e.g., GDP)"},
                    "limit": {"type": "integer", "description": "Number of observations"}
                },
                "required": ["series_id"]
            }
        ),
        types.Tool(
            name="market_overview",
            description="[MARKET] Get comprehensive market overview",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="api_status",
            description="[MARKET] Get status of all configured financial APIs",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="technical_analysis",
            description="[MARKET] Technical analysis with indicators (SMA, RSI, MACD, Bollinger Bands)",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol"},
                    "period": {"type": "integer", "description": "Analysis period in days"},
                    "indicators": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Indicators to calculate"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="pattern_recognition",
            description="[MARKET] Recognize chart patterns (head and shoulders, double top/bottom, triangles)",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "period": {"type": "integer"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="anomaly_detection",
            description="[MARKET] Detect price/volume anomalies",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "period": {"type": "integer"},
                    "sensitivity": {"type": "string", "enum": ["low", "medium", "high"]}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="stock_comparison",
            description="[MARKET] Compare multiple stocks",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "period": {"type": "integer"},
                    "metrics": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["symbols"]
            }
        ),
        types.Tool(
            name="sentiment_analysis",
            description="[MARKET] Analyze news sentiment for stocks",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "days": {"type": "integer"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="alert_system",
            description="[MARKET] Monitor stocks and create alerts",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "alert_type": {
                        "type": "string",
                        "enum": ["price_target", "percent_change", "volume_spike", "breakout"]
                    }
                },
                "required": ["symbol", "alert_type"]
            }
        ),

        # === RISK SPOKE TOOLS (8) ===
        types.Tool(
            name="risk_calculate_var",
            description="[RISK] Calculate Value at Risk using Historical, Parametric, or Monte Carlo methods",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "method": {
                        "type": "string",
                        "enum": ["historical", "parametric", "monte_carlo", "all"]
                    },
                    "confidence_level": {"type": "number"},
                    "portfolio_value": {"type": "number"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="risk_calculate_metrics",
            description="[RISK] Calculate comprehensive risk metrics (volatility, beta, Sharpe ratio, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "period": {"type": "integer"},
                    "benchmark": {"type": "string"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="risk_analyze_portfolio",
            description="[RISK] Analyze portfolio risk and diversification",
            inputSchema={
                "type": "object",
                "properties": {
                    "portfolio": {
                        "type": "array",
                        "items": {"type": "object"}
                    }
                },
                "required": ["portfolio"]
            }
        ),
        types.Tool(
            name="risk_stress_test",
            description="[RISK] Perform stress testing on portfolio",
            inputSchema={
                "type": "object",
                "properties": {
                    "portfolio": {"type": "array"},
                    "scenarios": {"type": "array"}
                },
                "required": ["portfolio"]
            }
        ),
        types.Tool(
            name="risk_analyze_tail_risk",
            description="[RISK] Analyze tail risk and extreme events",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "period": {"type": "integer"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="risk_calculate_greeks",
            description="[RISK] Calculate option Greeks (Delta, Gamma, Vega, Theta, Rho)",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "option_type": {"type": "string", "enum": ["call", "put", "both"]},
                    "strike": {"type": "number"},
                    "expiry_days": {"type": "integer"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="risk_check_compliance",
            description="[RISK] Check regulatory compliance (sanctions, position limits)",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string"},
                    "portfolio": {"type": "array"}
                }
            }
        ),
        types.Tool(
            name="risk_generate_dashboard",
            description="[RISK] Generate comprehensive risk dashboard",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "portfolio": {"type": "array"}
                }
            }
        ),

        # === PORTFOLIO SPOKE TOOLS (8) ===
        types.Tool(
            name="portfolio_optimize",
            description="[PORTFOLIO] Optimize portfolio allocation (maximize Sharpe ratio, minimize variance)",
            inputSchema={
                "type": "object",
                "properties": {
                    "tickers": {"type": "array", "items": {"type": "string"}},
                    "method": {
                        "type": "string",
                        "enum": ["max_sharpe", "min_variance", "risk_parity", "equal_weight"]
                    }
                },
                "required": ["tickers"]
            }
        ),
        types.Tool(
            name="portfolio_rebalance",
            description="[PORTFOLIO] Generate portfolio rebalancing recommendations",
            inputSchema={
                "type": "object",
                "properties": {
                    "current_positions": {
                        "type": "object",
                        "description": "Current positions {symbol: {shares, price, value}}"
                    },
                    "target_weights": {
                        "type": "object",
                        "description": "Target weights {symbol: weight}"
                    },
                    "total_value": {
                        "type": "number",
                        "description": "Total portfolio value"
                    },
                    "cash_available": {
                        "type": "number",
                        "description": "Available cash (default: 0.0)"
                    },
                    "strategy": {
                        "type": "string",
                        "description": "Rebalancing strategy (default: threshold)"
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Rebalancing threshold (default: 0.05)"
                    }
                },
                "required": ["current_positions", "target_weights", "total_value"]
            }
        ),
        types.Tool(
            name="portfolio_analyze_performance",
            description="[PORTFOLIO] Analyze portfolio performance metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "positions": {
                        "type": "object",
                        "description": "Positions {symbol: {shares, cost_basis, current_price}}"
                    },
                    "transactions": {
                        "type": "array",
                        "description": "Transaction history (optional)"
                    },
                    "benchmark": {
                        "type": "string",
                        "description": "Benchmark symbol (default: SPY)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD (optional)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD (optional)"
                    }
                },
                "required": ["positions"]
            }
        ),
        types.Tool(
            name="portfolio_backtest",
            description="[PORTFOLIO] Backtest portfolio strategies",
            inputSchema={
                "type": "object",
                "properties": {
                    "strategy": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "initial_capital": {"type": "number"}
                },
                "required": ["strategy"]
            }
        ),
        types.Tool(
            name="portfolio_analyze_factors",
            description="[PORTFOLIO] Analyze factor exposures (Fama-French, momentum, value)",
            inputSchema={
                "type": "object",
                "properties": {
                    "positions": {
                        "type": "object",
                        "description": "Positions {symbol: weight}"
                    },
                    "factors": {
                        "type": "array",
                        "description": "Factors to analyze (default: market, size, value, momentum, quality)",
                        "items": {"type": "string"}
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD (optional)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD (optional)"
                    },
                    "benchmark": {
                        "type": "string",
                        "description": "Benchmark symbol (default: SPY)"
                    }
                },
                "required": ["positions"]
            }
        ),
        types.Tool(
            name="portfolio_allocate_assets",
            description="[PORTFOLIO] Strategic asset allocation",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_classes": {
                        "type": "object",
                        "description": "Asset classes {class_name: [symbols]}"
                    },
                    "allocation_type": {
                        "type": "string",
                        "description": "Allocation type: strategic or tactical (default: strategic)"
                    },
                    "risk_tolerance": {
                        "type": "string",
                        "enum": ["conservative", "moderate", "aggressive"],
                        "description": "Risk tolerance level (default: moderate)"
                    },
                    "constraints": {
                        "type": "object",
                        "description": "Allocation constraints (optional)"
                    },
                    "rebalancing_threshold": {
                        "type": "number",
                        "description": "Rebalancing threshold (default: 0.05)"
                    }
                },
                "required": ["asset_classes"]
            }
        ),
        types.Tool(
            name="portfolio_optimize_tax",
            description="[PORTFOLIO] Tax-loss harvesting and optimization",
            inputSchema={
                "type": "object",
                "properties": {
                    "positions": {
                        "type": "object",
                        "description": "Positions {symbol: {shares, cost_basis, purchase_date}}"
                    },
                    "transactions": {
                        "type": "array",
                        "description": "Transaction history",
                        "items": {"type": "object"}
                    },
                    "tax_bracket": {
                        "type": "number",
                        "description": "Tax bracket rate (default: 0.24)"
                    },
                    "ltcg_rate": {
                        "type": "number",
                        "description": "Long-term capital gains rate (default: 0.15)"
                    },
                    "current_date": {
                        "type": "string",
                        "description": "Current date YYYY-MM-DD (optional)"
                    }
                },
                "required": ["positions", "transactions"]
            }
        ),
        types.Tool(
            name="portfolio_generate_dashboard",
            description="[PORTFOLIO] Generate comprehensive portfolio dashboard",
            inputSchema={
                "type": "object",
                "properties": {
                    "portfolio": {"type": "array"}
                },
                "required": ["portfolio"]
            }
        ),

        # === HUB MANAGEMENT TOOLS (5) ===
        types.Tool(
            name="hub_status",
            description="[HUB] Get comprehensive Hub status including builtin and external spokes",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="hub_register_spoke",
            description="[HUB] Register a new external Spoke service to Hub (HTTP endpoint)",
            inputSchema={
                "type": "object",
                "properties": {
                    "spoke_name": {"type": "string", "description": "Unique spoke name"},
                    "endpoint": {"type": "string", "description": "HTTP endpoint (e.g., http://localhost:8004)"},
                    "tool_count": {"type": "integer", "description": "Number of tools"},
                    "description": {"type": "string", "description": "Spoke description"}
                },
                "required": ["spoke_name", "endpoint"]
            }
        ),
        types.Tool(
            name="hub_unregister_spoke",
            description="[HUB] Unregister an external Spoke service from Hub",
            inputSchema={
                "type": "object",
                "properties": {
                    "spoke_name": {"type": "string", "description": "Spoke name to unregister"}
                },
                "required": ["spoke_name"]
            }
        ),
        types.Tool(
            name="hub_list_all_tools",
            description="[HUB] List all available tools across all spokes (builtin + external)",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="hub_search_tools",
            description="[HUB] Search for tools by keyword across all spokes",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword"},
                    "category": {
                        "type": "string",
                        "enum": ["all", "market", "risk", "portfolio"],
                        "description": "Filter by category"
                    }
                },
                "required": ["query"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution - all 34 tools (29 Spoke + 5 Hub) with lazy loading"""
    import json
    import time

    arguments = arguments or {}

    # === START MONITORING ===
    start_time = time.time()
    logger.info(f"=" * 60)
    logger.info(f"TOOL CALL: {name}")
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")

    try:
        # Market Spoke Tools (13)
        if name in ["unified_market_data", "stock_quote", "crypto_price", "financial_news",
                    "economic_indicator", "market_overview", "api_status", "technical_analysis",
                    "pattern_recognition", "anomaly_detection", "stock_comparison",
                    "sentiment_analysis", "alert_system"]:
            logger.info(f"[1/3] Loading Market tool: {name}")
            load_start = time.time()
            tool = get_market_tool(name)
            load_time = time.time() - load_start
            logger.info(f"[2/3] Tool loaded in {load_time:.3f}s, executing...")
            exec_start = time.time()
            result = await tool.execute(arguments)
            exec_time = time.time() - exec_start
            logger.info(f"[3/3] Execution completed in {exec_time:.3f}s")

        # Risk Spoke Tools (8)
        elif name in ["risk_calculate_var", "risk_calculate_metrics", "risk_analyze_portfolio",
                      "risk_stress_test", "risk_analyze_tail_risk", "risk_calculate_greeks",
                      "risk_check_compliance", "risk_generate_dashboard"]:
            tool = get_risk_tool(name)
            result = await tool.execute(arguments)

        # Portfolio Spoke Tools (8)
        elif name in ["portfolio_optimize", "portfolio_rebalance", "portfolio_analyze_performance",
                      "portfolio_backtest", "portfolio_analyze_factors", "portfolio_allocate_assets",
                      "portfolio_optimize_tax", "portfolio_generate_dashboard"]:
            tool = get_portfolio_tool(name)
            # Portfolio tools are functions, not class instances
            if callable(tool):
                result = await tool(**arguments)  # Unpack dict as keyword arguments
            else:
                result = await tool.execute(arguments)

        # Hub Management Tools (5)
        elif name == "hub_status":
            result = await hub_tools.hub_status(arguments)
        elif name == "hub_register_spoke":
            result = await hub_tools.register_spoke(arguments)
        elif name == "hub_unregister_spoke":
            result = await hub_tools.unregister_spoke(arguments)
        elif name == "hub_list_all_tools":
            result = await hub_tools.list_all_tools(arguments)
        elif name == "hub_search_tools":
            result = await hub_tools.search_tools(arguments)

        else:
            raise ValueError(f"Unknown tool: {name}")

        # === END MONITORING (SUCCESS) ===
        total_time = time.time() - start_time
        result_preview = str(result)[:200] if result else "None"
        logger.info(f"SUCCESS: Total time {total_time:.3f}s")
        logger.info(f"Result preview: {result_preview}...")
        logger.info(f"=" * 60)

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    except Exception as e:
        # === END MONITORING (ERROR) ===
        total_time = time.time() - start_time
        import traceback

        logger.error(f"FAILED: Total time {total_time:.3f}s")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        logger.info(f"=" * 60)

        error_detail = {
            "error": f"Tool execution failed: {str(e)}",
            "tool_name": name,
            "error_type": type(e).__name__,
            "execution_time": f"{total_time:.3f}s",
            "traceback": traceback.format_exc()
        }

        return [types.TextContent(
            type="text",
            text=json.dumps(error_detail, indent=2)
        )]


async def main():
    """Run the integrated MCP server"""
    from mcp.server.models import InitializationOptions

    logger.info("="*60)
    logger.info("FIN-HUB INTEGRATED SERVER STARTING")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info(f"Project root: {project_root}")
    logger.info(f"Market spoke: {market_spoke} (exists: {market_spoke.exists()})")
    logger.info(f"Risk spoke: {risk_spoke} (exists: {risk_spoke.exists()})")
    logger.info(f"Portfolio spoke: {portfolio_spoke} (exists: {portfolio_spoke.exists()})")
    logger.info(f"Log file: {log_file}")
    logger.info(f"sys.path (first 5 entries):")
    for i, path in enumerate(sys.path[:5]):
        logger.info(f"  [{i}] {path}")
    logger.info("="*60)

    # Import original stdout/stdin for MCP communication
    original_stdin = sys.__stdin__
    original_stdout = sys.__stdout__

    sys.stdin = original_stdin
    sys.stdout = original_stdout

    logger.info("Starting MCP stdio server...")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("MCP server initialized, waiting for requests...")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="fin-hub-integrated",
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
