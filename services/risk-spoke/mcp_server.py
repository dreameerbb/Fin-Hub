#!/usr/bin/env python3
"""
Risk Spoke MCP Server - Quantitative Risk Management
Provides 8 comprehensive risk analysis tools:
- VaR Calculator, Risk Metrics, Portfolio Risk
- Stress Testing, Tail Risk Analysis, Greeks Calculator
- Compliance Checker, Risk Dashboard
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
    dotenv_path = project_root.parent / '.env'
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
server = Server("fin-hub-risk")

# Lazy initialization - tools AND imports created on demand
_tool_instances = {}

def get_tool_instance(tool_name: str):
    """Get or create tool instance (lazy loading with imports)"""
    if tool_name not in _tool_instances:
        if tool_name == "var":
            from app.tools.var_calculator import VaRCalculatorTool
            _tool_instances[tool_name] = VaRCalculatorTool()
        elif tool_name == "metrics":
            from app.tools.risk_metrics import RiskMetricsTool
            _tool_instances[tool_name] = RiskMetricsTool()
        elif tool_name == "portfolio":
            from app.tools.portfolio_risk import PortfolioRiskTool
            _tool_instances[tool_name] = PortfolioRiskTool()
        elif tool_name == "stress":
            from app.tools.stress_testing import StressTestingTool
            _tool_instances[tool_name] = StressTestingTool()
        elif tool_name == "tail":
            from app.tools.tail_risk import TailRiskTool
            _tool_instances[tool_name] = TailRiskTool()
        elif tool_name == "greeks":
            from app.tools.greeks_calculator import GreeksCalculatorTool
            _tool_instances[tool_name] = GreeksCalculatorTool()
        elif tool_name == "compliance":
            from app.tools.compliance_checker import ComplianceCheckerTool
            _tool_instances[tool_name] = ComplianceCheckerTool()
        elif tool_name == "dashboard":
            from app.tools.risk_dashboard import RiskDashboardTool
            _tool_instances[tool_name] = RiskDashboardTool()
    return _tool_instances[tool_name]


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available risk management tools (8 tools) - optimized with hardcoded schemas"""
    # Use hardcoded schemas to avoid async calls during initialization
    return [
        types.Tool(
            name="risk_calculate_var",
            description="Calculate Value at Risk (VaR) using Historical, Parametric, or Monte Carlo methods",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol (e.g., AAPL, MSFT)"},
                    "method": {"type": "string", "enum": ["historical", "parametric", "monte_carlo", "all"], "description": "VaR calculation method (default: all)"},
                    "confidence_level": {"type": "number", "description": "Confidence level (e.g., 0.95, 0.99) - default: 0.95"},
                    "time_horizon": {"type": "integer", "description": "Time horizon in days (default: 1)"},
                    "portfolio_value": {"type": "number", "description": "Portfolio value in USD (default: 10000)"},
                    "period": {"type": "integer", "description": "Historical data period in days (default: 252 = 1 year)"},
                    "simulations": {"type": "integer", "description": "Number of Monte Carlo simulations (default: 10000)"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="risk_calculate_metrics",
            description="Calculate comprehensive risk metrics including Sharpe Ratio, Sortino Ratio, Maximum Drawdown, Volatility, Calmar Ratio, and more",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol (e.g., AAPL, TSLA)"},
                    "period": {"type": "integer", "description": "Analysis period in days (default: 252 = 1 year)"},
                    "risk_free_rate": {"type": "number", "description": "Annual risk-free rate (default: 0.04 = 4%)"},
                    "benchmark": {"type": "string", "description": "Benchmark symbol for beta/alpha (default: SPY)"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="risk_analyze_portfolio",
            description="Analyze portfolio risk including correlation, concentration, diversification, and Value at Risk",
            inputSchema={
                "type": "object",
                "properties": {
                    "portfolio": {"type": "array", "items": {"type": "object", "properties": {"symbol": {"type": "string"}, "weight": {"type": "number"}}}, "description": "Portfolio holdings with symbols and weights"},
                    "portfolio_value": {"type": "number", "description": "Total portfolio value in USD (default: 100000)"},
                    "period": {"type": "integer", "description": "Historical data period in days (default: 252)"},
                    "confidence_level": {"type": "number", "description": "VaR confidence level (default: 0.95)"},
                    "risk_free_rate": {"type": "number", "description": "Annual risk-free rate (default: 0.04)"}
                },
                "required": ["portfolio"]
            }
        ),
        types.Tool(
            name="risk_stress_test",
            description="Perform stress testing on a portfolio using historical crisis scenarios or custom scenarios",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol or portfolio identifier"},
                    "scenarios": {"type": "array", "items": {"type": "string"}, "description": "Scenarios to test: 2008_financial_crisis, 2020_covid_crash, 2011_european_debt, 2015_china_slowdown, 2022_inflation_shock, or 'all'"},
                    "custom_scenario": {"type": "object", "description": "Custom scenario with shock parameters"},
                    "period": {"type": "integer", "description": "Historical data period (default: 252)"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="risk_analyze_tail_risk",
            description="Analyze tail risk, black swan probability, and extreme value distributions",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol (e.g., AAPL, TSLA)"},
                    "period": {"type": "integer", "description": "Analysis period in days (default: 1000)"},
                    "threshold_percentile": {"type": "number", "description": "Percentile for extreme value threshold (default: 0.95)"},
                    "analysis": {"type": "array", "items": {"type": "string"}, "description": "Analyses to perform: extreme_value, fat_tail, skewness_kurtosis, black_swan, all"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="risk_calculate_greeks",
            description="Calculate option Greeks (Delta, Gamma, Vega, Theta, Rho) using Black-Scholes-Merton model",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Underlying stock symbol"},
                    "option_type": {"type": "string", "enum": ["call", "put", "both"], "description": "Option type (default: both)"},
                    "strike": {"type": "number", "description": "Strike price (default: current price)"},
                    "expiry_days": {"type": "integer", "description": "Days to expiration (default: 30)"},
                    "volatility": {"type": "number", "description": "Implied volatility (default: historical volatility)"},
                    "risk_free_rate": {"type": "number", "description": "Risk-free rate (default: 0.04)"},
                    "dividend_yield": {"type": "number", "description": "Dividend yield (default: 0)"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="risk_check_compliance",
            description="Check regulatory compliance including sanctions screening, KYC/AML, position limits, and concentration risk",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string", "description": "Entity name for sanctions screening"},
                    "portfolio": {"type": "array", "description": "Portfolio for compliance checks"},
                    "checks": {"type": "array", "items": {"type": "string"}, "description": "Checks to perform: sanctions, position_limits, concentration, all"}
                },
                "required": []
            }
        ),
        types.Tool(
            name="risk_generate_dashboard",
            description="Generate comprehensive risk dashboard with all risk metrics and analyses",
            inputSchema={
                "type": "object",
                "properties": {
                    "analysis_type": {"type": "string", "enum": ["single_asset", "portfolio"], "description": "Type of risk analysis (default: single_asset)"},
                    "symbol": {"type": "string", "description": "Stock symbol for single asset analysis"},
                    "portfolio": {"type": "array", "description": "Portfolio holdings for portfolio analysis"},
                    "portfolio_value": {"type": "number", "description": "Total portfolio value in USD (default: 100000)"},
                    "period": {"type": "integer", "description": "Analysis period in days (default: 252)"},
                    "confidence_level": {"type": "number", "description": "VaR confidence level (default: 0.95)"},
                    "risk_free_rate": {"type": "number", "description": "Risk-free rate (default: 0.04)"},
                    "benchmark": {"type": "string", "description": "Benchmark symbol for comparison (default: SPY)"},
                    "include_stress_test": {"type": "boolean", "description": "Include stress testing analysis (default: true)"},
                    "include_tail_risk": {"type": "boolean", "description": "Include tail risk analysis (default: true)"}
                },
                "required": []
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
        if name == "risk_calculate_var":
            result = await get_tool_instance("var").execute(arguments)
        elif name == "risk_calculate_metrics":
            result = await get_tool_instance("metrics").execute(arguments)
        elif name == "risk_analyze_portfolio":
            result = await get_tool_instance("portfolio").execute(arguments)
        elif name == "risk_stress_test":
            result = await get_tool_instance("stress").execute(arguments)
        elif name == "risk_analyze_tail_risk":
            result = await get_tool_instance("tail").execute(arguments)
        elif name == "risk_calculate_greeks":
            result = await get_tool_instance("greeks").execute(arguments)
        elif name == "risk_check_compliance":
            result = await get_tool_instance("compliance").execute(arguments)
        elif name == "risk_generate_dashboard":
            result = await get_tool_instance("dashboard").execute(arguments)
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
                server_name="fin-hub-risk",
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
