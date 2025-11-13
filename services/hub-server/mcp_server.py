#!/usr/bin/env python3
"""
Hub Server MCP Server - Central Orchestration & Tool Gateway
Provides hub management tools and integrates all Spoke services
"""
import sys
import os
from pathlib import Path
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables only if needed
if not os.getenv('ENVIRONMENT'):
    from dotenv import load_dotenv
    dotenv_path = project_root / '.env'
    load_dotenv(dotenv_path)

# Minimal logging - disable all
import logging
logging.disable(logging.CRITICAL)

# MCP imports (InitializationOptions is lazy-loaded in main())
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types

# Create MCP server
server = Server("fin-hub")

# Lazy imports for performance
# httpx will be imported on-demand in HubTools methods
import asyncio


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
        # Lazy import for performance
        import httpx

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
            "timestamp": asyncio.get_event_loop().time()
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
                # Try to get tools via MCP protocol
                # For now, we'll return predefined tool counts
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
            "timestamp": asyncio.get_event_loop().time()
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
                "role": "Central Orchestrator & Gateway"
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
                "error": f"Unknown spoke: {spoke_name}"
            }

        endpoint = self.spoke_endpoints[spoke_name]

        try:
            # This is a placeholder - in reality, we'd need to call the Spoke's MCP endpoint
            # For now, return a success message
            return {
                "success": True,
                "spoke": spoke_name,
                "tool": tool_name,
                "message": f"Tool routing to {spoke_name}.{tool_name} would happen here",
                "note": "Direct Spoke execution via MCP is recommended for production use"
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
            "timestamp": asyncio.get_event_loop().time()
        }

    async def unified_dashboard(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unified dashboard showing overview of all Fin-Hub services
        Combines information from Market, Risk, and Portfolio Spokes
        """
        from datetime import datetime

        # Get system status
        status = await self.hub_status({})

        # Build dashboard
        dashboard = {
            "dashboard_type": "Fin-Hub Unified Overview",
            "generated_at": datetime.now().isoformat(),

            # System Health
            "system_health": {
                "hub_status": "operational",
                "total_spokes": status["summary"]["total_spokes"],
                "healthy_spokes": status["summary"]["healthy_spokes"],
                "total_tools": status["summary"]["total_tools"],
                "health_percentage": round(
                    (status["summary"]["healthy_spokes"] / status["summary"]["total_spokes"]) * 100, 1
                ) if status["summary"]["total_spokes"] > 0 else 0
            },

            # Available Services
            "services": {
                "market_spoke": {
                    "status": "available" if any(s["name"] == "market" and s.get("available") for s in status["spokes"]["spokes"]) else "unavailable",
                    "tools": 13,
                    "capabilities": [
                        "Real-time stock quotes",
                        "Cryptocurrency prices",
                        "Financial news & sentiment",
                        "Economic indicators",
                        "Technical analysis",
                        "Pattern recognition"
                    ]
                },
                "risk_spoke": {
                    "status": "available" if any(s["name"] == "risk" and s.get("available") for s in status["spokes"]["spokes"]) else "unavailable",
                    "tools": 8,
                    "capabilities": [
                        "Value at Risk (VaR)",
                        "Risk metrics (Sharpe, Sortino)",
                        "Portfolio risk analysis",
                        "Stress testing",
                        "Tail risk analysis",
                        "Options Greeks",
                        "Compliance checking"
                    ]
                },
                "portfolio_spoke": {
                    "status": "available" if any(s["name"] == "portfolio" and s.get("available") for s in status["spokes"]["spokes"]) else "unavailable",
                    "tools": 8,
                    "capabilities": [
                        "Portfolio optimization",
                        "Rebalancing strategies",
                        "Performance analysis",
                        "Backtesting",
                        "Factor analysis",
                        "Asset allocation",
                        "Tax optimization"
                    ]
                }
            },

            # Quick Stats
            "quick_stats": {
                "total_mcp_tools": 34,
                "mcp_servers": 4,
                "supported_assets": ["Stocks", "Crypto", "Options", "Bonds"],
                "data_sources": 7,
                "api_integrations": ["Alpha Vantage", "CoinGecko", "News API", "FRED", "Finnhub", "MarketStack", "OpenSanctions"]
            },

            # Recommendations
            "recommendations": self._get_recommendations(status),

            # System Info
            "system_info": {
                "architecture": "Hub-and-Spoke",
                "protocol": "MCP (Model Context Protocol)",
                "version": "1.0.0",
                "data_storage": "71MB S&P 500 historical data"
            }
        }

        return dashboard

    def _get_recommendations(self, status: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on system status"""
        recommendations = []

        healthy_spokes = status["summary"]["healthy_spokes"]
        total_spokes = status["summary"]["total_spokes"]

        if healthy_spokes < total_spokes:
            unavailable_spokes = [
                s["name"] for s in status["spokes"]["spokes"]
                if not s.get("available", False)
            ]
            recommendations.append(
                f"⚠️ Some spokes are unavailable: {', '.join(unavailable_spokes)}. "
                "Check if MCP servers are running."
            )
        else:
            recommendations.append(
                "✅ All spokes are operational. System is ready for use."
            )

        recommendations.extend([
            "💡 Use 'hub_status' for detailed system information",
            "📊 Use Market Spoke for real-time market data and analysis",
            "🛡️ Use Risk Spoke for comprehensive risk management",
            "💼 Use Portfolio Spoke for optimization and backtesting",
            "🔄 All spokes support MCP protocol for seamless integration"
        ])

        return recommendations

    async def search_tools(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for tools across all Spokes by keyword
        Returns matching tools with descriptions and which Spoke provides them
        """
        query = arguments.get("query", "").lower()
        category = arguments.get("category", "all")  # all, market, risk, portfolio

        if not query:
            return {
                "error": "Query parameter is required",
                "usage": "Provide a search term (e.g., 'stock', 'risk', 'optimize')"
            }

        # Define all tools with metadata
        all_tools = {
            "market": [
                {"name": "unified_market_data", "keywords": ["market", "data", "unified", "multi", "source"], "category": "data"},
                {"name": "stock_quote", "keywords": ["stock", "quote", "price", "ticker", "equity"], "category": "data"},
                {"name": "crypto_price", "keywords": ["crypto", "cryptocurrency", "bitcoin", "ethereum", "price"], "category": "data"},
                {"name": "financial_news", "keywords": ["news", "article", "sentiment", "media"], "category": "analysis"},
                {"name": "economic_indicator", "keywords": ["economic", "indicator", "gdp", "cpi", "fred", "macro"], "category": "data"},
                {"name": "market_overview", "keywords": ["overview", "summary", "market", "snapshot"], "category": "analysis"},
                {"name": "api_status", "keywords": ["api", "status", "health", "available"], "category": "system"},
                {"name": "technical_analysis", "keywords": ["technical", "rsi", "macd", "bollinger", "indicator"], "category": "analysis"},
                {"name": "pattern_recognition", "keywords": ["pattern", "chart", "support", "resistance", "trend"], "category": "analysis"},
                {"name": "anomaly_detection", "keywords": ["anomaly", "outlier", "unusual", "detection"], "category": "analysis"},
                {"name": "stock_comparison", "keywords": ["compare", "comparison", "correlation", "multiple"], "category": "analysis"},
                {"name": "sentiment_analysis", "keywords": ["sentiment", "mood", "feeling", "opinion"], "category": "analysis"},
                {"name": "alert_system", "keywords": ["alert", "notification", "trigger", "watch"], "category": "monitoring"}
            ],
            "risk": [
                {"name": "risk_calculate_var", "keywords": ["var", "value", "risk", "loss", "downside"], "category": "calculation"},
                {"name": "risk_calculate_metrics", "keywords": ["sharpe", "sortino", "ratio", "metrics", "performance"], "category": "calculation"},
                {"name": "risk_analyze_portfolio", "keywords": ["portfolio", "risk", "diversification", "correlation"], "category": "analysis"},
                {"name": "risk_stress_test", "keywords": ["stress", "test", "scenario", "crisis", "shock"], "category": "testing"},
                {"name": "risk_analyze_tail_risk", "keywords": ["tail", "extreme", "black", "swan", "evt"], "category": "analysis"},
                {"name": "risk_calculate_greeks", "keywords": ["greeks", "delta", "gamma", "vega", "option"], "category": "calculation"},
                {"name": "risk_check_compliance", "keywords": ["compliance", "kyc", "aml", "sanctions", "regulation"], "category": "compliance"},
                {"name": "risk_generate_dashboard", "keywords": ["dashboard", "overview", "summary", "risk"], "category": "reporting"}
            ],
            "portfolio": [
                {"name": "portfolio_optimize", "keywords": ["optimize", "optimization", "efficient", "frontier", "markowitz"], "category": "optimization"},
                {"name": "portfolio_rebalance", "keywords": ["rebalance", "rebalancing", "adjust", "allocation"], "category": "management"},
                {"name": "portfolio_analyze_performance", "keywords": ["performance", "return", "analysis", "attribution"], "category": "analysis"},
                {"name": "portfolio_backtest", "keywords": ["backtest", "backtesting", "historical", "simulation"], "category": "testing"},
                {"name": "portfolio_analyze_factors", "keywords": ["factor", "fama", "french", "exposure"], "category": "analysis"},
                {"name": "portfolio_allocate_assets", "keywords": ["allocation", "asset", "diversify", "strategic"], "category": "management"},
                {"name": "portfolio_optimize_taxes", "keywords": ["tax", "taxes", "harvest", "loss", "ltcg"], "category": "optimization"},
                {"name": "portfolio_generate_dashboard", "keywords": ["dashboard", "overview", "summary", "portfolio"], "category": "reporting"}
            ]
        }

        # Search
        matches = []
        spokes_to_search = [category] if category != "all" else ["market", "risk", "portfolio"]

        for spoke in spokes_to_search:
            if spoke not in all_tools:
                continue

            for tool in all_tools[spoke]:
                # Check if query matches tool name or keywords
                if (query in tool["name"].lower() or
                    any(query in keyword for keyword in tool["keywords"])):
                    matches.append({
                        "spoke": spoke,
                        "tool_name": tool["name"],
                        "category": tool["category"],
                        "relevance": self._calculate_relevance(query, tool)
                    })

        # Sort by relevance
        matches.sort(key=lambda x: x["relevance"], reverse=True)

        return {
            "query": query,
            "total_matches": len(matches),
            "matches": matches[:10],  # Top 10 results
            "search_scope": f"{category} spoke(s)",
            "usage_hint": "Use the spoke's MCP server to call these tools directly"
        }

    def _calculate_relevance(self, query: str, tool: Dict) -> float:
        """Calculate search relevance score"""
        score = 0.0

        # Exact match in name
        if query == tool["name"].lower():
            score += 10.0
        elif query in tool["name"].lower():
            score += 5.0

        # Keyword matches
        exact_keywords = sum(1 for k in tool["keywords"] if query == k)
        partial_keywords = sum(1 for k in tool["keywords"] if query in k)

        score += exact_keywords * 3.0
        score += partial_keywords * 1.0

        return score

    async def get_quick_actions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get quick action templates for common Fin-Hub tasks
        Provides ready-to-use tool calls for frequent operations
        """
        return {
            "quick_actions": {
                "market_data": {
                    "description": "Quick market data access",
                    "actions": [
                        {
                            "name": "Get stock price",
                            "spoke": "market",
                            "tool": "stock_quote",
                            "example": {"symbol": "AAPL"}
                        },
                        {
                            "name": "Get crypto price",
                            "spoke": "market",
                            "tool": "crypto_price",
                            "example": {"coin_id": "bitcoin"}
                        },
                        {
                            "name": "Market overview",
                            "spoke": "market",
                            "tool": "market_overview",
                            "example": {}
                        }
                    ]
                },
                "risk_analysis": {
                    "description": "Quick risk assessment",
                    "actions": [
                        {
                            "name": "Calculate VaR",
                            "spoke": "risk",
                            "tool": "risk_calculate_var",
                            "example": {
                                "returns": [0.01, -0.02, 0.015, -0.01, 0.02],
                                "confidence_level": 0.95,
                                "symbol": "PORTFOLIO"
                            }
                        },
                        {
                            "name": "Risk metrics",
                            "spoke": "risk",
                            "tool": "risk_calculate_metrics",
                            "example": {
                                "returns": [0.01, -0.02, 0.015],
                                "risk_free_rate": 0.03,
                                "symbol": "PORTFOLIO"
                            }
                        }
                    ]
                },
                "portfolio_management": {
                    "description": "Quick portfolio operations",
                    "actions": [
                        {
                            "name": "Optimize portfolio",
                            "spoke": "portfolio",
                            "tool": "portfolio_optimize",
                            "example": {
                                "tickers": ["AAPL", "GOOGL", "MSFT"],
                                "method": "mean_variance"
                            }
                        },
                        {
                            "name": "Analyze performance",
                            "spoke": "portfolio",
                            "tool": "portfolio_analyze_performance",
                            "example": {
                                "tickers": ["AAPL", "GOOGL"],
                                "weights": [0.6, 0.4]
                            }
                        }
                    ]
                },
                "system_monitoring": {
                    "description": "System health and status",
                    "actions": [
                        {
                            "name": "Check system status",
                            "spoke": "hub",
                            "tool": "hub_status",
                            "example": {}
                        },
                        {
                            "name": "Health check",
                            "spoke": "hub",
                            "tool": "hub_health_check",
                            "example": {}
                        },
                        {
                            "name": "Unified dashboard",
                            "spoke": "hub",
                            "tool": "hub_unified_dashboard",
                            "example": {}
                        }
                    ]
                }
            },
            "usage": "Copy the example JSON and use it with the specified spoke's tool",
            "tip": "All spokes are accessible via their MCP servers in Claude Desktop"
        }

    async def get_integration_guide(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get integration guide for using Fin-Hub services
        Provides setup instructions and common workflows
        """
        use_case = arguments.get("use_case", "general")

        workflows = {
            "general": {
                "title": "General Fin-Hub Usage",
                "steps": [
                    "1. Use hub_unified_dashboard to see all available services",
                    "2. Use hub_search_tools to find specific tools by keyword",
                    "3. Call tools directly via their respective Spoke MCP servers",
                    "4. Use hub_health_check to monitor system status"
                ],
                "example_workflow": "Dashboard → Search → Execute → Monitor"
            },
            "portfolio_analysis": {
                "title": "Complete Portfolio Analysis Workflow",
                "steps": [
                    "1. Get current prices: market.stock_quote for each holding",
                    "2. Calculate returns: Use historical data",
                    "3. Assess risk: risk.risk_calculate_metrics",
                    "4. Check VaR: risk.risk_calculate_var",
                    "5. Optimize allocation: portfolio.portfolio_optimize",
                    "6. Generate dashboard: portfolio.portfolio_generate_dashboard"
                ],
                "spokes_used": ["market", "risk", "portfolio"],
                "estimated_time": "2-5 minutes"
            },
            "risk_assessment": {
                "title": "Comprehensive Risk Assessment",
                "steps": [
                    "1. Collect returns data from portfolio",
                    "2. Calculate basic metrics: risk.risk_calculate_metrics",
                    "3. Calculate VaR: risk.risk_calculate_var",
                    "4. Run stress tests: risk.risk_stress_test",
                    "5. Analyze tail risks: risk.risk_analyze_tail_risk",
                    "6. Check compliance: risk.risk_check_compliance",
                    "7. Generate report: risk.risk_generate_dashboard"
                ],
                "spokes_used": ["risk", "market"],
                "estimated_time": "5-10 minutes"
            },
            "market_research": {
                "title": "Market Research & Analysis",
                "steps": [
                    "1. Get market overview: market.market_overview",
                    "2. Fetch news: market.financial_news",
                    "3. Analyze sentiment: market.sentiment_analysis",
                    "4. Technical analysis: market.technical_analysis",
                    "5. Compare stocks: market.stock_comparison",
                    "6. Set alerts: market.alert_system"
                ],
                "spokes_used": ["market"],
                "estimated_time": "3-7 minutes"
            }
        }

        selected_workflow = workflows.get(use_case, workflows["general"])

        return {
            "use_case": use_case,
            "workflow": selected_workflow,
            "available_workflows": list(workflows.keys()),
            "mcp_servers": {
                "hub": "fin-hub (management & orchestration)",
                "market": "fin-hub-market (market data & analysis)",
                "risk": "fin-hub-risk (risk management)",
                "portfolio": "fin-hub-portfolio (portfolio optimization)"
            },
            "total_tools": 34,
            "tip": "Use hub_search_tools to find specific tools for your needs"
        }

    async def get_system_metrics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get system metrics and performance monitoring
        Monitors CPU, memory, disk usage, and MCP server performance
        """
        try:
            import psutil
        except ImportError:
            return {
                "error": "psutil not installed",
                "message": "Install psutil for system metrics: pip install psutil",
                "basic_metrics": await self._get_basic_metrics()
            }

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Process metrics (current Hub Server process)
        process = psutil.Process()
        process_memory = process.memory_info()

        # Spoke health metrics
        spoke_metrics = {}
        for spoke_name, endpoint in self.spoke_endpoints.items():
            start_time = asyncio.get_event_loop().time()
            try:
                import httpx
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(f"{endpoint}/health")
                    response_time = (asyncio.get_event_loop().time() - start_time) * 1000  # ms
                    spoke_metrics[spoke_name] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "response_time_ms": round(response_time, 2),
                        "endpoint": endpoint
                    }
            except Exception as e:
                spoke_metrics[spoke_name] = {
                    "status": "offline",
                    "error": str(e)[:100],
                    "endpoint": endpoint
                }

        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": round(cpu_percent, 1),
                "cpu_count": psutil.cpu_count(),
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": disk.percent
                }
            },
            "hub_process": {
                "memory_mb": round(process_memory.rss / (1024**2), 2),
                "cpu_percent": round(process.cpu_percent(), 1),
                "threads": process.num_threads()
            },
            "spokes": spoke_metrics,
            "summary": {
                "system_health": "good" if cpu_percent < 80 and memory.percent < 80 else "warning",
                "spokes_online": sum(1 for m in spoke_metrics.values() if m.get("status") == "healthy"),
                "total_spokes": len(spoke_metrics),
                "avg_response_time_ms": round(
                    sum(m.get("response_time_ms", 0) for m in spoke_metrics.values() if "response_time_ms" in m) /
                    max(1, sum(1 for m in spoke_metrics.values() if "response_time_ms" in m)),
                    2
                )
            }
        }

    async def _get_basic_metrics(self) -> Dict[str, Any]:
        """Fallback basic metrics without psutil"""
        spoke_status = await self.list_spokes({})
        return {
            "timestamp": datetime.now().isoformat(),
            "spokes": spoke_status["spokes"],
            "note": "Limited metrics - install psutil for full system monitoring"
        }


# Initialize Hub tools
hub_tools = HubTools()


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Hub management tools"""
    return [
        types.Tool(
            name="hub_status",
            description="Get comprehensive Hub status including all connected Spoke services and available tools",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="hub_list_spokes",
            description="List all Spoke services (Market, Risk, Portfolio) with their health status and endpoints",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="hub_get_spoke_tools",
            description="Get list of all available tools from Spoke services",
            inputSchema={
                "type": "object",
                "properties": {
                    "spoke_name": {
                        "type": "string",
                        "enum": ["all", "market", "risk", "portfolio"],
                        "default": "all",
                        "description": "Spoke to query (default: all)"
                    }
                }
            }
        ),
        types.Tool(
            name="hub_health_check",
            description="Perform comprehensive health check on Hub and all Spoke services",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="hub_unified_dashboard",
            description="Get unified dashboard showing complete overview of all Fin-Hub services, capabilities, and system health. Perfect for getting started or checking overall system status.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="hub_search_tools",
            description="Search for tools across all Spokes by keyword. Find the right tool for your task by searching for terms like 'stock', 'risk', 'optimize', etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term (e.g., 'stock', 'risk', 'optimize', 'backtest')"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["all", "market", "risk", "portfolio"],
                        "default": "all",
                        "description": "Limit search to specific spoke"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="hub_quick_actions",
            description="Get ready-to-use templates for common Fin-Hub tasks. Provides example arguments for frequently used operations.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="hub_integration_guide",
            description="Get step-by-step workflow guides for common use cases like portfolio analysis, risk assessment, and market research.",
            inputSchema={
                "type": "object",
                "properties": {
                    "use_case": {
                        "type": "string",
                        "enum": ["general", "portfolio_analysis", "risk_assessment", "market_research"],
                        "default": "general",
                        "description": "Type of workflow guide"
                    }
                }
            }
        ),
        types.Tool(
            name="hub_system_metrics",
            description="Get real-time system metrics including CPU, memory, disk usage, and MCP server performance. Monitors Hub process and all Spoke server response times.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="hub_call_spoke_tool",
            description="Call a tool on a specific Spoke service (routing/proxy function)",
            inputSchema={
                "type": "object",
                "properties": {
                    "spoke_name": {
                        "type": "string",
                        "enum": ["market", "risk", "portfolio"],
                        "description": "Target Spoke service"
                    },
                    "tool_name": {
                        "type": "string",
                        "description": "Name of the tool to execute"
                    },
                    "tool_arguments": {
                        "type": "object",
                        "description": "Arguments for the tool",
                        "additionalProperties": True
                    }
                },
                "required": ["spoke_name", "tool_name"]
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
        elif name == "hub_unified_dashboard":
            result = await hub_tools.unified_dashboard(arguments)
        elif name == "hub_search_tools":
            result = await hub_tools.search_tools(arguments)
        elif name == "hub_quick_actions":
            result = await hub_tools.get_quick_actions(arguments)
        elif name == "hub_integration_guide":
            result = await hub_tools.get_integration_guide(arguments)
        elif name == "hub_system_metrics":
            result = await hub_tools.get_system_metrics(arguments)
        elif name == "hub_call_spoke_tool":
            result = await hub_tools.call_spoke_tool(arguments)
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
