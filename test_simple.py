"""
Simple direct test of each spoke's tools
Tests without MCP server overhead
"""

import asyncio
import sys
from pathlib import Path

# Test results
results = {"hub": 0, "market": 0, "risk": 0, "portfolio": 0}

async def test_market():
    """Test Market spoke tools directly"""
    print("\n=== Testing Market Spoke ===")
    sys.path.insert(0, str(Path(__file__).parent / "services" / "market-spoke"))

    try:
        from app.tools.unified_market_data import UnifiedMarketDataTool
        tool = UnifiedMarketDataTool()
        result = await tool.execute({"query_type": "stock_quote", "symbol": "AAPL"})
        if "error" not in result:
            print("[PASS] unified_market_data")
            results["market"] += 1
        else:
            print(f"[FAIL] unified_market_data: {result['error']}")
    except Exception as e:
        print(f"[ERROR] unified_market_data: {e}")

    print(f"\nMarket Spoke: {results['market']}/1 tools passed")


async def test_risk():
    """Test Risk spoke tools directly"""
    print("\n=== Testing Risk Spoke ===")

    # Clean sys.modules - remove all app.* modules from cache
    modules_to_remove = [k for k in sys.modules.keys() if k.startswith('app')]
    for module_name in modules_to_remove:
        del sys.modules[module_name]

    # Clean sys.path
    for p in list(sys.path):
        if "market-spoke" in p or "portfolio-spoke" in p:
            sys.path.remove(p)

    risk_spoke_path = str(Path(__file__).parent / "services" / "risk-spoke")
    if risk_spoke_path in sys.path:
        sys.path.remove(risk_spoke_path)
    sys.path.insert(0, risk_spoke_path)

    risk_tools = [
        ("var_calculator", "VaRCalculatorTool", {"symbol": "AAPL", "method": "historical"}),
        ("risk_metrics", "RiskMetricsTool", {"symbol": "AAPL", "period": 252}),
        ("portfolio_risk", "PortfolioRiskTool", {"portfolio": [{"symbol": "AAPL", "weight": 1.0}]}),
        ("stress_testing", "StressTestingTool", {"portfolio": [{"symbol": "AAPL", "weight": 1.0}]}),
        ("tail_risk", "TailRiskTool", {"symbol": "AAPL", "period": 252}),
        ("greeks_calculator", "GreeksCalculatorTool", {"symbol": "AAPL"}),
        ("compliance_checker", "ComplianceCheckerTool", {"entity_name": "Test"}),
        ("risk_dashboard", "RiskDashboardTool", {"symbol": "AAPL"}),
    ]

    for module_name, class_name, args in risk_tools:
        try:
            module = __import__(f"app.tools.{module_name}", fromlist=[class_name])
            tool_class = getattr(module, class_name)
            tool = tool_class()
            result = await tool.execute(args)
            if "error" not in result:
                print(f"[PASS] {module_name}")
                results["risk"] += 1
            else:
                print(f"[FAIL] {module_name}: {result['error']}")
        except Exception as e:
            print(f"[ERROR] {module_name}: {type(e).__name__}: {e}")

    print(f"\nRisk Spoke: {results['risk']}/8 tools passed")


async def test_portfolio():
    """Test Portfolio spoke tools directly"""
    print("\n=== Testing Portfolio Spoke ===")

    # Clean sys.modules - remove all app.* modules from cache
    modules_to_remove = [k for k in sys.modules.keys() if k.startswith('app')]
    for module_name in modules_to_remove:
        del sys.modules[module_name]

    # Clean sys.path
    for p in list(sys.path):
        if "risk-spoke" in p or "market-spoke" in p:
            sys.path.remove(p)

    portfolio_spoke_path = str(Path(__file__).parent / "services" / "portfolio-spoke")
    if portfolio_spoke_path in sys.path:
        sys.path.remove(portfolio_spoke_path)
    sys.path.insert(0, portfolio_spoke_path)

    portfolio_tools = [
        ("portfolio_optimizer", "portfolio_optimizer", {"tickers": ["AAPL", "MSFT"], "method": "max_sharpe"}),
        ("portfolio_rebalancer", "portfolio_rebalancer", {
            "current_positions": {"AAPL": {"shares": 10, "price": 150, "value": 1500}},
            "target_weights": {"AAPL": 1.0},
            "total_value": 1500
        }),
        ("performance_analyzer", "performance_analyzer", {
            "positions": {"AAPL": {"shares": 10, "cost_basis": 150, "current_price": 170}}
        }),
        ("backtester", "backtester", {"strategy": "momentum", "start_date": "2023-01-01", "end_date": "2024-01-01"}),
        ("factor_analyzer", "factor_analyzer", {
            "positions": {"AAPL": 0.6, "MSFT": 0.4}
        }),
        ("asset_allocator", "asset_allocator", {
            "asset_classes": {"stocks": ["AAPL", "MSFT"], "bonds": ["AGG"]},
            "risk_tolerance": "moderate"
        }),
        ("tax_optimizer", "tax_optimizer", {
            "positions": {"AAPL": {"shares": 100, "cost_basis": 150, "purchase_date": "2023-01-01"}},
            "transactions": []
        }),
        ("portfolio_dashboard", "portfolio_dashboard", {
            "positions": {"AAPL": {"shares": 10, "cost_basis": 150}}
        }),
    ]

    for module_name, func_name, args in portfolio_tools:
        try:
            module = __import__(f"app.tools.{module_name}", fromlist=[func_name])
            func = getattr(module, func_name)
            result = await func(**args)
            if "error" not in result:
                print(f"[PASS] {module_name}")
                results["portfolio"] += 1
            else:
                print(f"[FAIL] {module_name}: {result.get('error', result)}")
        except Exception as e:
            print(f"[ERROR] {module_name}: {type(e).__name__}: {str(e)[:100]}")

    print(f"\nPortfolio Spoke: {results['portfolio']}/8 tools passed")


async def test_hub():
    """Test Hub management tools"""
    print("\n=== Testing Hub Management ===")

    # Clean sys.modules
    modules_to_remove = [k for k in sys.modules.keys() if k.startswith('app')]
    for module_name in modules_to_remove:
        del sys.modules[module_name]

    # Clean sys.path
    for p in list(sys.path):
        if any(spoke in p for spoke in ["market-spoke", "risk-spoke", "portfolio-spoke"]):
            sys.path.remove(p)

    # Import hub server
    sys.path.insert(0, str(Path(__file__).parent / "services" / "hub-server"))
    import mcp_server_integrated

    hub_tests = [
        ("hub_status", {}),
        ("hub_list_all_tools", {}),
        ("hub_search_tools", {"query": "stock", "category": "all"}),
        ("hub_register_spoke", {"spoke_name": "test-spoke", "endpoint": "http://localhost:9999", "tool_count": 5, "description": "Test spoke"}),
        ("hub_unregister_spoke", {"spoke_name": "test-spoke"}),
    ]

    for tool_name, args in hub_tests:
        try:
            # Get hub instance
            hub = mcp_server_integrated.HubManager()

            # Call the appropriate method
            if tool_name == "hub_status":
                result = await hub.hub_status(args)
            elif tool_name == "hub_list_all_tools":
                result = await hub.list_all_tools(args)
            elif tool_name == "hub_search_tools":
                result = await hub.search_tools(args)
            elif tool_name == "hub_register_spoke":
                result = await hub.register_spoke(args)
            elif tool_name == "hub_unregister_spoke":
                result = await hub.unregister_spoke(args)

            if "error" not in result:
                print(f"[PASS] {tool_name}")
                results['hub'] += 1
            else:
                print(f"[FAIL] {tool_name}: {result.get('error', result)}")
        except Exception as e:
            print(f"[ERROR] {tool_name}: {type(e).__name__}: {str(e)[:100]}")

    print(f"\nHub Management: {results['hub']}/5 tools passed")


async def main():
    print("="*80)
    print("SIMPLE DIRECT SPOKE TESTS")
    print("="*80)

    await test_hub()
    await test_market()
    await test_risk()
    await test_portfolio()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    total = sum(results.values())
    print(f"Market:    {results['market']}/1")
    print(f"Risk:      {results['risk']}/8")
    print(f"Portfolio: {results['portfolio']}/8")
    print(f"\nTotal:     {total}/17 passed")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
