#!/usr/bin/env python3
"""
Hub Server MCP Server - Central Orchestration & Tool Gateway
Provides hub management tools and integrates all Spoke services
"""
import sys
import os
from pathlib import Path
import logging
import json
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path)

# Configure logging to stderr ONLY
logging.basicConfig(
    level=logging.CRITICAL,  # Only critical errors
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
    force=True
)

# Disable ALL loggers
logging.disable(logging.CRITICAL)

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types

# Create MCP server
server = Server("fin-hub")

# Import Hub tools
import httpx
import asyncio
from datetime import datetime


class HubTools:
    """Hub Server tools for service management and orchestration"""

    def __init__(self):
        self.spoke_endpoints = {
            "market": "http://localhost:8001",
            "risk": "http://localhost:8002",
            "portfolio": "http://localhost:8003"
        }

    async def list_spokes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all available Spoke services and their status"""
        spokes = []

        for spoke_name, endpoint in self.spoke_endpoints.items():
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{endpoint}/health")
                    is_healthy = response.status_code == 200

                    spoke_info = {
                        "name": spoke_name,
                        "endpoint": endpoint,
                        "status": "healthy" if is_healthy else "unhealthy",
                        "available": is_healthy
                    }

                    if is_healthy:
                        try:
                            health_data = response.json()
                            spoke_info["version"] = health_data.get("version", "unknown")
                            spoke_info["uptime"] = health_data.get("uptime", "unknown")
                        except:
                            pass

                    spokes.append(spoke_info)

            except Exception as e:
                spokes.append({
                    "name": spoke_name,
                    "endpoint": endpoint,
                    "status": "offline",
                    "available": False,
                    "error": str(e)
                })

        return {
            "total_spokes": len(spokes),
            "healthy_spokes": sum(1 for s in spokes if s.get("available", False)),
            "spokes": spokes,
            "timestamp": datetime.now().isoformat()
        }

    async def get_spoke_tools(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all available tools from all Spoke services"""
        spoke_name = arguments.get("spoke_name", "all")

        all_tools = {}

        spokes_to_query = [spoke_name] if spoke_name != "all" else list(self.spoke_endpoints.keys())

        for spoke in spokes_to_query:
            if spoke not in self.spoke_endpoints:
                continue

            try:
                # Return predefined tool counts (could be enhanced to query actual MCP)
                tools_count = {
                    "market": 13,
                    "risk": 8,
                    "portfolio": 8
                }.get(spoke, 0)

                all_tools[spoke] = {
                    "spoke": spoke,
                    "tool_count": tools_count,
                    "endpoint": self.spoke_endpoints[spoke],
                    "status": "available"
                }

            except Exception as e:
                all_tools[spoke] = {
                    "spoke": spoke,
                    "tool_count": 0,
                    "error": str(e),
                    "status": "unavailable"
                }

        return {
            "spokes_queried": len(all_tools),
            "total_tools": sum(t.get("tool_count", 0) for t in all_tools.values()),
            "tools_by_spoke": all_tools,
            "timestamp": datetime.now().isoformat()
        }

    async def hub_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive Hub status including all Spokes"""
        # Get spoke status
        spoke_status = await self.list_spokes({})

        # Get tool counts
        tools_info = await self.get_spoke_tools({"spoke_name": "all"})

        return {
            "hub": {
                "name": "fin-hub",
                "version": "1.0.0",
                "status": "operational",
                "role": "Central Orchestrator & Gateway",
                "timestamp": datetime.now().isoformat()
            },
            "spokes": spoke_status,
            "tools": tools_info,
            "summary": {
                "total_spokes": spoke_status["total_spokes"],
                "healthy_spokes": spoke_status["healthy_spokes"],
                "total_tools": tools_info["total_tools"],
                "hub_operational": True
            }
        }

    async def call_spoke_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on a specific Spoke service (proxy/routing)"""
        spoke_name = arguments.get("spoke_name")
        tool_name = arguments.get("tool_name")
        tool_arguments = arguments.get("tool_arguments", {})

        if not spoke_name or not tool_name:
            return {
                "success": False,
                "error": "spoke_name and tool_name are required"
            }

        if spoke_name not in self.spoke_endpoints:
            return {
                "success": False,
                "error": f"Unknown spoke: {spoke_name}",
                "available_spokes": list(self.spoke_endpoints.keys())
            }

        endpoint = self.spoke_endpoints[spoke_name]

        try:
            # This is a placeholder for actual MCP routing
            # In production, this would make an actual MCP call to the Spoke
            return {
                "success": True,
                "spoke": spoke_name,
                "tool": tool_name,
                "message": f"Routing to {spoke_name}.{tool_name}",
                "note": "For actual tool execution, connect to the Spoke directly via MCP",
                "recommendation": f"Use the fin-hub-{spoke_name} MCP server in Claude Desktop"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "spoke": spoke_name,
                "tool": tool_name
            }

    async def hub_health_check(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check on Hub and all connected Spokes"""
        spoke_status = await self.list_spokes({})

        all_healthy = spoke_status["healthy_spokes"] == spoke_status["total_spokes"]

        return {
            "hub_healthy": True,
            "all_spokes_healthy": all_healthy,
            "spokes": spoke_status["spokes"],
            "health_score": round((spoke_status["healthy_spokes"] / spoke_status["total_spokes"]) * 100, 1) if spoke_status["total_spokes"] > 0 else 0,
            "timestamp": datetime.now().isoformat(),
            "issues": [] if all_healthy else [
                f"{s['name']} is {s['status']}"
                for s in spoke_status["spokes"]
                if not s.get("available", False)
            ]
        }

    async def unified_dashboard(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Unified dashboard showing comprehensive overview of all Fin-Hub services"""
        status = await self.hub_status({})
        health = await self.hub_health_check({})

        return {
            "dashboard_type": "Fin-Hub Unified Overview",
            "generated_at": datetime.now().isoformat(),
            "system_health": {
                "hub_status": "operational",
                "overall_health_score": health["health_score"],
                "all_spokes_healthy": health["all_spokes_healthy"]
            },
            "services": {
                "market_spoke": {
                    "status": next((s["status"] for s in health["spokes"] if s["name"] == "market"), "unknown"),
                    "tools": 13,
                    "capabilities": ["Stock quotes", "Crypto prices", "News", "Sentiment analysis"]
                },
                "risk_spoke": {
                    "status": next((s["status"] for s in health["spokes"] if s["name"] == "risk"), "unknown"),
                    "tools": 8,
                    "capabilities": ["VaR", "Portfolio risk", "Correlation", "Scenario analysis"]
                },
                "portfolio_spoke": {
                    "status": next((s["status"] for s in health["spokes"] if s["name"] == "portfolio"), "unknown"),
                    "tools": 8,
                    "capabilities": ["Optimization", "Backtesting", "Rebalancing", "Performance"]
                }
            },
            "quick_stats": {
                "total_mcp_tools": 34,
                "total_spokes": 3,
                "healthy_spokes": health["health_score"] / 100 * 3,
                "hub_tools": 9
            },
            "recommendations": self._get_recommendations(health),
            "system_info": {
                "architecture": "Hub-and-Spoke",
                "mcp_protocol": "2024-11-05",
                "hub_version": "1.0.0"
            }
        }

    def _get_recommendations(self, health: Dict[str, Any]) -> List[str]:
        """Get system recommendations based on health status"""
        recommendations = []

        if not health["all_spokes_healthy"]:
            for issue in health.get("issues", []):
                recommendations.append(f"Check {issue}")

        if health["health_score"] < 100:
            recommendations.append("Some services are offline - check spoke endpoints")

        if not recommendations:
            recommendations.append("All systems operational - ready for financial analysis")

        return recommendations

    async def search_tools(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for tools across all spokes by keyword"""
        query = arguments.get("query", "").lower()

        if not query:
            return {
                "error": "Search query is required",
                "example": "Use query like 'stock', 'risk', 'portfolio', etc."
            }

        # Define all tools with keywords
        all_tools = {
            "market": [
                {"name": "stock_quote", "keywords": ["stock", "quote", "price", "ticker", "equity"], "description": "Get stock quote and price data"},
                {"name": "crypto_price", "keywords": ["crypto", "bitcoin", "ethereum", "cryptocurrency"], "description": "Get cryptocurrency prices"},
                {"name": "financial_news", "keywords": ["news", "article", "sentiment", "headlines"], "description": "Get financial news and sentiment"},
                {"name": "market_overview", "keywords": ["market", "overview", "summary", "indices"], "description": "Market overview and indices"},
                {"name": "technical_indicators", "keywords": ["technical", "indicator", "rsi", "macd", "sma"], "description": "Technical analysis indicators"},
                {"name": "company_fundamentals", "keywords": ["fundamental", "earnings", "revenue", "company"], "description": "Company fundamental data"},
                {"name": "economic_calendar", "keywords": ["economic", "calendar", "events", "fed"], "description": "Economic events calendar"},
                {"name": "forex_rates", "keywords": ["forex", "currency", "exchange", "fx"], "description": "Foreign exchange rates"},
                {"name": "commodities", "keywords": ["commodity", "gold", "oil", "silver"], "description": "Commodity prices"},
                {"name": "sector_performance", "keywords": ["sector", "industry", "performance"], "description": "Sector performance analysis"},
                {"name": "dividend_data", "keywords": ["dividend", "yield", "payout"], "description": "Dividend information"},
                {"name": "options_data", "keywords": ["option", "call", "put", "derivative"], "description": "Options chain data"},
                {"name": "analyst_ratings", "keywords": ["analyst", "rating", "recommendation"], "description": "Analyst ratings and targets"}
            ],
            "risk": [
                {"name": "calculate_var", "keywords": ["var", "value at risk", "risk", "downside"], "description": "Calculate Value at Risk"},
                {"name": "portfolio_risk", "keywords": ["portfolio", "risk", "volatility", "beta"], "description": "Portfolio risk metrics"},
                {"name": "correlation_matrix", "keywords": ["correlation", "covariance", "matrix"], "description": "Asset correlation analysis"},
                {"name": "stress_test", "keywords": ["stress", "test", "scenario", "crisis"], "description": "Stress testing scenarios"},
                {"name": "risk_attribution", "keywords": ["attribution", "factor", "risk source"], "description": "Risk factor attribution"},
                {"name": "drawdown_analysis", "keywords": ["drawdown", "maximum", "decline"], "description": "Drawdown analysis"},
                {"name": "sharpe_ratio", "keywords": ["sharpe", "ratio", "risk adjusted", "performance"], "description": "Risk-adjusted returns"},
                {"name": "monte_carlo", "keywords": ["monte carlo", "simulation", "probability"], "description": "Monte Carlo simulation"}
            ],
            "portfolio": [
                {"name": "optimize_portfolio", "keywords": ["optimize", "allocation", "efficient frontier"], "description": "Portfolio optimization"},
                {"name": "backtest_strategy", "keywords": ["backtest", "strategy", "historical", "test"], "description": "Strategy backtesting"},
                {"name": "rebalance", "keywords": ["rebalance", "adjust", "weights"], "description": "Portfolio rebalancing"},
                {"name": "performance_attribution", "keywords": ["performance", "attribution", "contribution"], "description": "Performance attribution"},
                {"name": "holdings_analysis", "keywords": ["holdings", "positions", "assets"], "description": "Holdings analysis"},
                {"name": "trade_execution", "keywords": ["trade", "execute", "order"], "description": "Trade execution simulation"},
                {"name": "tax_optimization", "keywords": ["tax", "loss", "harvest", "optimization"], "description": "Tax-loss harvesting"},
                {"name": "benchmark_comparison", "keywords": ["benchmark", "compare", "index"], "description": "Benchmark comparison"}
            ]
        }

        # Search and score matches
        matches = []
        for spoke, tools in all_tools.items():
            for tool in tools:
                relevance = self._calculate_relevance(query, tool)
                if relevance > 0:
                    matches.append({
                        "name": tool["name"],
                        "spoke": spoke,
                        "description": tool["description"],
                        "relevance": relevance
                    })

        # Sort by relevance
        matches.sort(key=lambda x: x["relevance"], reverse=True)

        return {
            "query": query,
            "total_matches": len(matches),
            "matching_tools": matches[:10],  # Top 10 results
            "spokes_searched": list(all_tools.keys())
        }

    def _calculate_relevance(self, query: str, tool: Dict[str, Any]) -> int:
        """Calculate relevance score for a tool based on query"""
        score = 0
        query_words = query.lower().split()

        for word in query_words:
            # Exact match in name
            if word in tool["name"].lower():
                score += 10

            # Match in keywords
            for keyword in tool["keywords"]:
                if word in keyword.lower():
                    score += 5
                    break

            # Match in description
            if word in tool["description"].lower():
                score += 2

        return score

    async def get_quick_actions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get ready-to-use quick actions and templates"""
        return {
            "quick_actions": [
                {
                    "name": "check_stock_price",
                    "description": "Quick stock price check",
                    "spoke": "market",
                    "tool": "stock_quote",
                    "example_args": {"symbol": "AAPL"}
                },
                {
                    "name": "analyze_portfolio",
                    "description": "Comprehensive portfolio analysis",
                    "spoke": "portfolio",
                    "tool": "holdings_analysis",
                    "example_args": {"portfolio_id": "default"}
                },
                {
                    "name": "check_crypto",
                    "description": "Cryptocurrency price check",
                    "spoke": "market",
                    "tool": "crypto_price",
                    "example_args": {"symbol": "BTC"}
                },
                {
                    "name": "market_overview",
                    "description": "Daily market summary",
                    "spoke": "market",
                    "tool": "market_overview",
                    "example_args": {}
                },
                {
                    "name": "calculate_risk",
                    "description": "Portfolio risk assessment",
                    "spoke": "risk",
                    "tool": "portfolio_risk",
                    "example_args": {"portfolio_id": "default"}
                },
                {
                    "name": "optimize_allocation",
                    "description": "Optimize portfolio allocation",
                    "spoke": "portfolio",
                    "tool": "optimize_portfolio",
                    "example_args": {"method": "efficient_frontier"}
                },
                {
                    "name": "backtest_strategy",
                    "description": "Test trading strategy",
                    "spoke": "portfolio",
                    "tool": "backtest_strategy",
                    "example_args": {"strategy": "buy_hold", "start_date": "2023-01-01"}
                },
                {
                    "name": "stress_test",
                    "description": "Stress test portfolio",
                    "spoke": "risk",
                    "tool": "stress_test",
                    "example_args": {"scenario": "market_crash"}
                }
            ],
            "usage_note": "Use hub_call_spoke_tool to execute these actions"
        }

    async def get_integration_guide(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get integration guides for common workflows"""
        use_case = arguments.get("use_case", "general")

        workflows = {
            "stock_analysis": {
                "name": "Stock Analysis Workflow",
                "description": "Complete stock research and analysis",
                "steps": [
                    {"step": 1, "tool": "stock_quote", "spoke": "market", "purpose": "Get current price"},
                    {"step": 2, "tool": "company_fundamentals", "spoke": "market", "purpose": "Review financials"},
                    {"step": 3, "tool": "technical_indicators", "spoke": "market", "purpose": "Technical analysis"},
                    {"step": 4, "tool": "analyst_ratings", "spoke": "market", "purpose": "Expert opinions"},
                    {"step": 5, "tool": "financial_news", "spoke": "market", "purpose": "Latest news"}
                ]
            },
            "portfolio_management": {
                "name": "Portfolio Management Workflow",
                "description": "Build and manage investment portfolio",
                "steps": [
                    {"step": 1, "tool": "holdings_analysis", "spoke": "portfolio", "purpose": "Review current holdings"},
                    {"step": 2, "tool": "portfolio_risk", "spoke": "risk", "purpose": "Assess risk exposure"},
                    {"step": 3, "tool": "optimize_portfolio", "spoke": "portfolio", "purpose": "Find optimal allocation"},
                    {"step": 4, "tool": "rebalance", "spoke": "portfolio", "purpose": "Rebalance if needed"},
                    {"step": 5, "tool": "performance_attribution", "spoke": "portfolio", "purpose": "Track performance"}
                ]
            },
            "risk_assessment": {
                "name": "Risk Assessment Workflow",
                "description": "Comprehensive risk analysis",
                "steps": [
                    {"step": 1, "tool": "portfolio_risk", "spoke": "risk", "purpose": "Calculate risk metrics"},
                    {"step": 2, "tool": "calculate_var", "spoke": "risk", "purpose": "Value at Risk"},
                    {"step": 3, "tool": "correlation_matrix", "spoke": "risk", "purpose": "Asset correlations"},
                    {"step": 4, "tool": "stress_test", "spoke": "risk", "purpose": "Stress scenarios"},
                    {"step": 5, "tool": "drawdown_analysis", "spoke": "risk", "purpose": "Historical drawdowns"}
                ]
            },
            "crypto_tracking": {
                "name": "Cryptocurrency Tracking",
                "description": "Monitor crypto investments",
                "steps": [
                    {"step": 1, "tool": "crypto_price", "spoke": "market", "purpose": "Current prices"},
                    {"step": 2, "tool": "market_overview", "spoke": "market", "purpose": "Market context"},
                    {"step": 3, "tool": "portfolio_risk", "spoke": "risk", "purpose": "Volatility assessment"},
                    {"step": 4, "tool": "holdings_analysis", "spoke": "portfolio", "purpose": "Position sizing"}
                ]
            }
        }

        if use_case in workflows:
            return {"workflow": workflows[use_case]}
        else:
            return {
                "available_workflows": list(workflows.keys()),
                "message": f"Workflow '{use_case}' not found. Available: {', '.join(workflows.keys())}"
            }


# Initialize Hub tools
hub_tools = HubTools()


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Hub management tools"""
    return [
        types.Tool(
            name="hub_status",
            description="Get comprehensive Hub status including all connected Spoke services (Market, Risk, Portfolio) and available tools. Shows operational state and health metrics.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="hub_list_spokes",
            description="List all Spoke services (Market, Risk, Portfolio) with their health status, endpoints, and availability. Useful for checking which services are online.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="hub_get_spoke_tools",
            description="Get list of all available tools from Spoke services. Can query all spokes or a specific one (market, risk, portfolio).",
            inputSchema={
                "type": "object",
                "properties": {
                    "spoke_name": {
                        "type": "string",
                        "enum": ["all", "market", "risk", "portfolio"],
                        "default": "all",
                        "description": "Spoke to query: 'all' for all spokes, or specific spoke name"
                    }
                }
            }
        ),
        types.Tool(
            name="hub_health_check",
            description="Perform comprehensive health check on Hub and all Spoke services. Returns health score and identifies any offline or unhealthy services.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="hub_call_spoke_tool",
            description="Route a tool call to a specific Spoke service. NOTE: For production use, connect directly to the Spoke's MCP server instead (fin-hub-market, fin-hub-risk, fin-hub-portfolio).",
            inputSchema={
                "type": "object",
                "properties": {
                    "spoke_name": {
                        "type": "string",
                        "enum": ["market", "risk", "portfolio"],
                        "description": "Target Spoke service (market, risk, or portfolio)"
                    },
                    "tool_name": {
                        "type": "string",
                        "description": "Name of the tool to execute on the Spoke"
                    },
                    "tool_arguments": {
                        "type": "object",
                        "description": "Arguments to pass to the tool",
                        "additionalProperties": True
                    }
                },
                "required": ["spoke_name", "tool_name"]
            }
        ),
        types.Tool(
            name="hub_unified_dashboard",
            description="Get unified dashboard with comprehensive overview of all Fin-Hub services, health status, and system recommendations",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="hub_search_tools",
            description="Search for tools across all spokes by keyword. Find relevant tools for stock analysis, risk assessment, portfolio management, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g. 'stock', 'risk', 'portfolio', 'backtest', 'crypto')"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="hub_quick_actions",
            description="Get ready-to-use quick actions and templates for common financial tasks",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="hub_integration_guide",
            description="Get step-by-step integration guides for common workflows (stock_analysis, portfolio_management, risk_assessment, crypto_tracking)",
            inputSchema={
                "type": "object",
                "properties": {
                    "use_case": {
                        "type": "string",
                        "enum": ["stock_analysis", "portfolio_management", "risk_assessment", "crypto_tracking"],
                        "description": "Type of workflow guide to retrieve"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution"""
    arguments = arguments or {}

    try:
        if name == "hub_status":
            result = await hub_tools.hub_status(arguments)
        elif name == "hub_list_spokes":
            result = await hub_tools.list_spokes(arguments)
        elif name == "hub_get_spoke_tools":
            result = await hub_tools.get_spoke_tools(arguments)
        elif name == "hub_health_check":
            result = await hub_tools.hub_health_check(arguments)
        elif name == "hub_call_spoke_tool":
            result = await hub_tools.call_spoke_tool(arguments)
        elif name == "hub_unified_dashboard":
            result = await hub_tools.unified_dashboard(arguments)
        elif name == "hub_search_tools":
            result = await hub_tools.search_tools(arguments)
        elif name == "hub_quick_actions":
            result = await hub_tools.get_quick_actions(arguments)
        elif name == "hub_integration_guide":
            result = await hub_tools.get_integration_guide(arguments)
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
                server_name="fin-hub",
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
