#!/usr/bin/env python3
"""
Portfolio Spoke MCP Server - Professional Portfolio Management
Provides 8 comprehensive portfolio tools:
- Portfolio Optimizer, Portfolio Rebalancer
- Performance Analyzer, Backtester, Factor Analyzer
- Asset Allocator, Tax Optimizer, Portfolio Dashboard
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables only if needed
if not os.getenv('ENVIRONMENT'):
    from dotenv import load_dotenv
    dotenv_path = project_root.parent.parent / '.env'
    if dotenv_path.exists():
        load_dotenv(dotenv_path)

# Minimal logging - disable all
import logging
logging.disable(logging.CRITICAL)

# MCP imports (InitializationOptions is lazy-loaded in main())
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types

# Create MCP server
server = Server("fin-hub-portfolio")

# Lazy initialization - tools AND imports created on demand
_tool_instances = {}

def get_tool_instance(tool_name: str):
    """Get or create tool instance (lazy loading with imports)"""
    if tool_name not in _tool_instances:
        if tool_name == "optimize":
            from app.tools.portfolio_optimizer import portfolio_optimizer
            _tool_instances[tool_name] = portfolio_optimizer
        elif tool_name == "rebalance":
            from app.tools.portfolio_rebalancer import portfolio_rebalancer
            _tool_instances[tool_name] = portfolio_rebalancer
        elif tool_name == "performance":
            from app.tools.performance_analyzer import performance_analyzer
            _tool_instances[tool_name] = performance_analyzer
        elif tool_name == "backtest":
            from app.tools.backtester import backtester
            _tool_instances[tool_name] = backtester
        elif tool_name == "factors":
            from app.tools.factor_analyzer import factor_analyzer
            _tool_instances[tool_name] = factor_analyzer
        elif tool_name == "allocate":
            from app.tools.asset_allocator import asset_allocator
            _tool_instances[tool_name] = asset_allocator
        elif tool_name == "tax":
            from app.tools.tax_optimizer import tax_optimizer
            _tool_instances[tool_name] = tax_optimizer
        elif tool_name == "dashboard":
            from app.tools.portfolio_dashboard import portfolio_dashboard
            _tool_instances[tool_name] = portfolio_dashboard
    return _tool_instances[tool_name]


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available portfolio management tools (8 tools)"""
    return [
        # 1. Portfolio Optimizer
        types.Tool(
            name="portfolio_optimize",
            description="Optimize portfolio weights using Mean-Variance, HRP, Black-Litterman, or Risk Parity. Supports multiple objectives: max Sharpe, min volatility, efficient return/risk.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of stock symbols (2-50 stocks)",
                        "minItems": 2,
                        "maxItems": 50
                    },
                    "method": {
                        "type": "string",
                        "enum": ["mean_variance", "hrp", "risk_parity", "max_sharpe", "min_volatility"],
                        "default": "mean_variance",
                        "description": "Optimization method"
                    },
                    "objective": {
                        "type": "string",
                        "enum": ["max_sharpe", "min_volatility", "efficient_return", "efficient_risk"],
                        "default": "max_sharpe",
                        "description": "Optimization objective (for mean_variance)"
                    },
                    "target_return": {
                        "type": "number",
                        "description": "Target annual return for efficient_return objective (e.g., 0.15 for 15%)"
                    },
                    "target_risk": {
                        "type": "number",
                        "description": "Target annual volatility for efficient_risk objective (e.g., 0.20 for 20%)"
                    },
                    "risk_free_rate": {
                        "type": "number",
                        "default": 0.03,
                        "description": "Risk-free rate (annualized, default: 3%)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date for historical data (YYYY-MM-DD, default: 1 year ago)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for historical data (YYYY-MM-DD, default: today)"
                    }
                },
                "required": ["tickers"]
            }
        ),

        # 2. Portfolio Rebalancer
        types.Tool(
            name="portfolio_rebalance",
            description="Generate rebalancing trades to align portfolio with target weights. Supports threshold-based, periodic, and tax-aware strategies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "current_positions": {
                        "type": "object",
                        "description": "Current holdings: {ticker: {shares, value, price}}",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "shares": {"type": "number"},
                                "value": {"type": "number"},
                                "price": {"type": "number"}
                            }
                        }
                    },
                    "target_weights": {
                        "type": "object",
                        "description": "Target allocation: {ticker: weight}",
                        "additionalProperties": {"type": "number"}
                    },
                    "total_value": {
                        "type": "number",
                        "description": "Total portfolio value"
                    },
                    "cash_available": {
                        "type": "number",
                        "default": 0,
                        "description": "Available cash for investing"
                    },
                    "strategy": {
                        "type": "string",
                        "enum": ["threshold", "periodic", "tax_aware"],
                        "default": "threshold",
                        "description": "Rebalancing strategy"
                    },
                    "threshold": {
                        "type": "number",
                        "default": 0.05,
                        "description": "Drift threshold (5% default)"
                    }
                },
                "required": ["current_positions", "target_weights", "total_value"]
            }
        ),

        # 3. Performance Analyzer
        types.Tool(
            name="portfolio_analyze_performance",
            description="Calculate comprehensive performance metrics: returns, Sharpe ratio, Sortino ratio, max drawdown, alpha/beta, and attribution analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "positions": {
                        "type": "object",
                        "description": "Current holdings: {ticker: {shares, avg_cost, current_price}}",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "shares": {"type": "number"},
                                "avg_cost": {"type": "number"},
                                "current_price": {"type": "number"}
                            }
                        }
                    },
                    "transactions": {
                        "type": "array",
                        "description": "Historical trades (optional): [{date, ticker, shares, price, action}]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string"},
                                "ticker": {"type": "string"},
                                "shares": {"type": "number"},
                                "price": {"type": "number"},
                                "action": {"type": "string", "enum": ["buy", "sell"]}
                            }
                        }
                    },
                    "benchmark": {
                        "type": "string",
                        "default": "SPY",
                        "description": "Benchmark symbol (default: SPY)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Analysis start date (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Analysis end date (YYYY-MM-DD)"
                    },
                    "risk_free_rate": {
                        "type": "number",
                        "default": 0.03,
                        "description": "Risk-free rate (annualized)"
                    }
                },
                "required": ["positions"]
            }
        ),

        # 4. Backtester
        types.Tool(
            name="portfolio_backtest",
            description="Backtest trading strategies with realistic transaction costs, slippage, and rebalancing. Supports buy-and-hold, momentum, mean-reversion strategies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "strategy": {
                        "type": "string",
                        "enum": ["buy_and_hold", "equal_weight", "momentum", "mean_reversion", "custom"],
                        "default": "equal_weight",
                        "description": "Trading strategy"
                    },
                    "universe": {
                        "type": "string",
                        "enum": ["sp500", "custom"],
                        "default": "sp500",
                        "description": "Stock universe - sp500 for all S&P 500 stocks, custom for specific tickers"
                    },
                    "custom_tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Custom ticker list (required if universe='custom')"
                    },
                    "initial_capital": {
                        "type": "number",
                        "default": 100000,
                        "description": "Initial capital (USD)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Backtest start date (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Backtest end date (YYYY-MM-DD)"
                    },
                    "rebalance_frequency": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"],
                        "default": "monthly",
                        "description": "Rebalancing frequency"
                    },
                    "transaction_cost": {
                        "type": "number",
                        "default": 0.001,
                        "description": "Transaction cost (0.001 = 0.1%)"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Strategy parameters (e.g., {'lookback': 60, 'top_n': 20} for momentum)"
                    }
                },
                "required": []
            }
        ),

        # 5. Factor Analyzer
        types.Tool(
            name="portfolio_analyze_factors",
            description="Perform multi-factor analysis (Fama-French 5-factor, momentum, quality). Explains portfolio returns through factor exposures.",
            inputSchema={
                "type": "object",
                "properties": {
                    "positions": {
                        "type": "object",
                        "description": "Portfolio weights: {ticker: weight} (e.g., {'AAPL': 0.30, 'MSFT': 0.40, 'GOOGL': 0.30})",
                        "additionalProperties": {"type": "number"}
                    },
                    "factors": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["market", "size", "value", "profitability", "investment", "momentum", "quality"]
                        },
                        "default": ["market", "size", "value", "momentum", "quality"],
                        "description": "Factor models to analyze"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Analysis start date (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Analysis end date (YYYY-MM-DD)"
                    },
                    "benchmark": {
                        "type": "string",
                        "default": "SPY",
                        "description": "Benchmark symbol (default: SPY)"
                    }
                },
                "required": ["positions"]
            }
        ),

        # 6. Asset Allocator
        types.Tool(
            name="portfolio_allocate_assets",
            description="Determine strategic/tactical asset allocation across asset classes. Analyzes diversification, correlations, and optimal weights based on risk tolerance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_classes": {
                        "type": "object",
                        "description": "Asset classes with representative tickers, e.g., {'US_Equity': ['AAPL', 'MSFT'], 'Fixed_Income': ['TLT', 'AGG']}",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "allocation_type": {
                        "type": "string",
                        "enum": ["strategic", "tactical"],
                        "default": "strategic",
                        "description": "Allocation type: strategic (long-term) or tactical (market-timing)"
                    },
                    "risk_tolerance": {
                        "type": "string",
                        "enum": ["conservative", "moderate", "aggressive"],
                        "default": "moderate",
                        "description": "Risk tolerance level"
                    },
                    "constraints": {
                        "type": "object",
                        "description": "Asset class constraints, e.g., {'US_Equity': {'min': 0.3, 'max': 0.6}}",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "min": {"type": "number"},
                                "max": {"type": "number"}
                            }
                        }
                    },
                    "rebalancing_threshold": {
                        "type": "number",
                        "default": 0.05,
                        "description": "Drift threshold for rebalancing (default: 5%)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Analysis start date (YYYY-MM-DD, default: 1 year ago)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Analysis end date (YYYY-MM-DD, default: today)"
                    },
                    "risk_free_rate": {
                        "type": "number",
                        "default": 0.03,
                        "description": "Risk-free rate (annualized, default: 3%)"
                    }
                },
                "required": ["asset_classes"]
            }
        ),

        # 7. Tax Optimizer
        types.Tool(
            name="portfolio_optimize_taxes",
            description="Tax-loss harvesting recommendations, wash sale detection, minimize capital gains tax. Analyzes long-term vs short-term holdings and tax benefits.",
            inputSchema={
                "type": "object",
                "properties": {
                    "positions": {
                        "type": "object",
                        "description": "Current holdings with cost basis: {ticker: {shares, cost_basis, purchase_date, current_price}}",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "shares": {"type": "number"},
                                "cost_basis": {"type": "number"},
                                "purchase_date": {"type": "string"},
                                "current_price": {"type": "number"}
                            }
                        }
                    },
                    "transactions": {
                        "type": "array",
                        "description": "Historical transactions: [{date, ticker, shares, price, action}]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string"},
                                "ticker": {"type": "string"},
                                "shares": {"type": "number"},
                                "price": {"type": "number"},
                                "action": {"type": "string", "enum": ["buy", "sell"]}
                            }
                        }
                    },
                    "tax_bracket": {
                        "type": "number",
                        "default": 0.24,
                        "description": "Ordinary income tax rate (default: 24%)"
                    },
                    "ltcg_rate": {
                        "type": "number",
                        "default": 0.15,
                        "description": "Long-term capital gains rate (default: 15%)"
                    },
                    "stcg_rate": {
                        "type": "number",
                        "description": "Short-term capital gains rate (default: same as tax_bracket)"
                    },
                    "current_date": {
                        "type": "string",
                        "description": "Current date for calculations (YYYY-MM-DD, default: today)"
                    },
                    "harvest_threshold": {
                        "type": "number",
                        "default": 0.03,
                        "description": "Minimum loss % to harvest (default: 3%)"
                    }
                },
                "required": ["positions", "transactions"]
            }
        ),

        # 8. Portfolio Dashboard
        types.Tool(
            name="portfolio_generate_dashboard",
            description="Generate comprehensive portfolio dashboard with health scoring, performance metrics, risk assessment, and recommendations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "positions": {
                        "type": "object",
                        "description": "Current holdings: {ticker: {shares, cost_basis, current_price, purchase_date}}",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "shares": {"type": "number"},
                                "cost_basis": {"type": "number"},
                                "current_price": {"type": "number"},
                                "purchase_date": {"type": "string"}
                            }
                        }
                    },
                    "target_weights": {
                        "type": "object",
                        "description": "Target allocation (optional): {ticker: weight}",
                        "additionalProperties": {"type": "number"}
                    },
                    "benchmark": {
                        "type": "string",
                        "default": "SPY",
                        "description": "Benchmark ticker (default: SPY)"
                    },
                    "risk_tolerance": {
                        "type": "string",
                        "enum": ["conservative", "moderate", "aggressive"],
                        "default": "moderate",
                        "description": "Risk tolerance level"
                    },
                    "tax_bracket": {
                        "type": "number",
                        "default": 0.24,
                        "description": "Tax rate for calculations (default: 24%)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Analysis start date (YYYY-MM-DD, default: 1 year ago)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Analysis end date (YYYY-MM-DD, default: today)"
                    }
                },
                "required": ["positions"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution (8 tools) - using lazy loading"""
    import json

    arguments = arguments or {}

    try:
        # Route to appropriate tool with lazy initialization
        if name == "portfolio_optimize":
            result = await get_tool_instance("optimize")(**arguments)
        elif name == "portfolio_rebalance":
            result = await get_tool_instance("rebalance")(**arguments)
        elif name == "portfolio_analyze_performance":
            result = await get_tool_instance("performance")(**arguments)
        elif name == "portfolio_backtest":
            result = await get_tool_instance("backtest")(**arguments)
        elif name == "portfolio_analyze_factors":
            result = await get_tool_instance("factors")(**arguments)
        elif name == "portfolio_allocate_assets":
            result = await get_tool_instance("allocate")(**arguments)
        elif name == "portfolio_optimize_taxes":
            result = await get_tool_instance("tax")(**arguments)
        elif name == "portfolio_generate_dashboard":
            result = await get_tool_instance("dashboard")(**arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    except Exception as e:
        logging.error(f"Error executing {name}: {str(e)}", exc_info=True)
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
                server_name="fin-hub-portfolio",
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
