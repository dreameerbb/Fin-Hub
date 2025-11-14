"""
Comprehensive test script for all Fin-Hub tools
Tests Market (13), Risk (8), and Portfolio (8) spoke tools
"""

import asyncio
import json
import sys
from pathlib import Path

# Add hub-server to path
sys.path.insert(0, str(Path(__file__).parent / "services" / "hub-server"))

from mcp.server.stdio import stdio_server
from mcp import types
import mcp_server_integrated


async def test_tool(tool_name: str, arguments: dict, description: str):
    """Test a single tool and return results"""
    print(f"\n{'='*80}")
    print(f"Testing: {description}")
    print(f"Tool: {tool_name}")
    print(f"Arguments: {json.dumps(arguments, indent=2)}")
    print(f"{'='*80}")

    try:
        # Call tool
        import time
        start = time.time()

        result = await mcp_server_integrated.handle_call_tool(
            tool_name, arguments
        )

        elapsed = time.time() - start

        # Check result - handle_call_tool returns list of TextContent objects
        if isinstance(result, list) and len(result) > 0:
            content = result[0]
            if hasattr(content, 'text'):
                data = json.loads(content.text)

                if 'error' in data:
                    print(f"[FAIL] ({elapsed:.1f}s): {data['error']}")
                    return False
                else:
                    print(f"[PASS] ({elapsed:.1f}s)")
                    # Print first few lines of result
                    result_str = json.dumps(data, indent=2)
                    lines = result_str.split('\n')
                    preview = '\n'.join(lines[:10])
                    if len(lines) > 10:
                        preview += f"\n... ({len(lines)-10} more lines)"
                    print(f"Result preview:\n{preview}")
                    return True

        print(f"[WARN] UNEXPECTED RESPONSE ({elapsed:.1f}s)")
        print(f"Result: {result}")
        return False

    except Exception as e:
        print(f"[ERROR] EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""

    print("""
================================================================================
                    FIN-HUB COMPREHENSIVE TOOL TEST

  Testing 29 tools across 3 spokes:
  - Market Spoke: 13 tools
  - Risk Spoke: 8 tools
  - Portfolio Spoke: 8 tools
================================================================================
""")

    results = {
        'market': {'passed': 0, 'failed': 0, 'total': 13},
        'risk': {'passed': 0, 'failed': 0, 'total': 8},
        'portfolio': {'passed': 0, 'failed': 0, 'total': 8}
    }

    # ========================================================================
    # MARKET SPOKE TESTS (13 tools)
    # ========================================================================

    print("\n" + "="*80)
    print("MARKET SPOKE TESTS (13 tools)")
    print("="*80)

    market_tests = [
        ("stock_quote", {"symbol": "AAPL"}, "1/13: Stock Quote"),
        ("crypto_price", {"symbol": "BTC"}, "2/13: Crypto Price"),
        ("financial_news", {"query": "AI stocks", "limit": 5}, "3/13: Financial News"),
        ("economic_indicator", {"series_id": "GDP"}, "4/13: Economic Indicator"),
        ("market_overview", {}, "5/13: Market Overview"),
        ("api_status", {}, "6/13: API Status"),
        ("technical_analysis", {"symbol": "AAPL", "indicators": ["rsi", "macd"], "period": 30}, "7/13: Technical Analysis"),
        ("pattern_recognition", {"symbol": "AAPL", "period": 60}, "8/13: Pattern Recognition"),
        ("anomaly_detection", {"symbol": "AAPL", "period": 30, "sensitivity": "medium"}, "9/13: Anomaly Detection"),
        ("stock_comparison", {"symbols": ["AAPL", "MSFT"], "period": 30}, "10/13: Stock Comparison"),
        ("sentiment_analysis", {"symbol": "AAPL", "days": 7}, "11/13: Sentiment Analysis"),
        ("alert_system", {"symbol": "AAPL", "alert_type": "price_target"}, "12/13: Alert System"),
        ("unified_market_data", {"query_type": "stock_quote", "symbol": "AAPL"}, "13/13: Unified Market Data"),
    ]

    for tool_name, args, desc in market_tests:
        success = await test_tool(tool_name, args, desc)
        if success:
            results['market']['passed'] += 1
        else:
            results['market']['failed'] += 1

    # ========================================================================
    # RISK SPOKE TESTS (8 tools)
    # ========================================================================

    print("\n\n" + "="*80)
    print("RISK SPOKE TESTS (8 tools)")
    print("="*80)

    risk_tests = [
        ("risk_calculate_var", {"symbol": "AAPL", "method": "historical"}, "1/8: VaR Calculator"),
        ("risk_calculate_metrics", {"symbol": "AAPL", "period": 252}, "2/8: Risk Metrics"),
        ("risk_analyze_portfolio", {"portfolio": [{"symbol": "AAPL", "weight": 0.5}, {"symbol": "MSFT", "weight": 0.5}]}, "3/8: Portfolio Risk"),
        ("risk_stress_test", {"portfolio": [{"symbol": "AAPL", "weight": 1.0}]}, "4/8: Stress Testing"),
        ("risk_analyze_tail_risk", {"symbol": "AAPL", "period": 252}, "5/8: Tail Risk Analysis"),
        ("risk_calculate_greeks", {"symbol": "AAPL", "option_type": "call"}, "6/8: Greeks Calculator"),
        ("risk_check_compliance", {"entity_name": "Test Corp"}, "7/8: Compliance Check"),
        ("risk_generate_dashboard", {"symbol": "AAPL"}, "8/8: Risk Dashboard"),
    ]

    for tool_name, args, desc in risk_tests:
        success = await test_tool(tool_name, args, desc)
        if success:
            results['risk']['passed'] += 1
        else:
            results['risk']['failed'] += 1

    # ========================================================================
    # PORTFOLIO SPOKE TESTS (8 tools)
    # ========================================================================

    print("\n\n" + "="*80)
    print("PORTFOLIO SPOKE TESTS (8 tools)")
    print("="*80)

    portfolio_tests = [
        ("portfolio_optimize", {"tickers": ["AAPL", "MSFT", "GOOGL"], "method": "max_sharpe"}, "1/8: Portfolio Optimizer"),
        ("portfolio_rebalance", {"current_holdings": {"AAPL": 1000, "MSFT": 500}, "target_allocation": {"AAPL": 0.6, "MSFT": 0.4}}, "2/8: Portfolio Rebalancer"),
        ("portfolio_analyze_performance", {"portfolio": [{"symbol": "AAPL", "shares": 10}]}, "3/8: Performance Analyzer"),
        ("portfolio_backtest", {"strategy": "momentum", "start_date": "2023-01-01", "end_date": "2024-01-01"}, "4/8: Backtester"),
        ("portfolio_analyze_factors", {"portfolio": [{"symbol": "AAPL", "weight": 0.5}]}, "5/8: Factor Analyzer"),
        ("portfolio_allocate_assets", {"risk_tolerance": "moderate", "investment_horizon": 10}, "6/8: Asset Allocator"),
        ("portfolio_optimize_tax", {"portfolio": [{"symbol": "AAPL", "shares": 100, "cost_basis": 150}]}, "7/8: Tax Optimizer"),
        ("portfolio_generate_dashboard", {"portfolio": [{"symbol": "AAPL", "shares": 10}]}, "8/8: Portfolio Dashboard"),
    ]

    for tool_name, args, desc in portfolio_tests:
        success = await test_tool(tool_name, args, desc)
        if success:
            results['portfolio']['passed'] += 1
        else:
            results['portfolio']['failed'] += 1

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print("\n\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    total_passed = sum(r['passed'] for r in results.values())
    total_failed = sum(r['failed'] for r in results.values())
    total_tests = sum(r['total'] for r in results.values())

    print(f"\nMarket Spoke:    {results['market']['passed']}/{results['market']['total']} passed")
    print(f"Risk Spoke:      {results['risk']['passed']}/{results['risk']['total']} passed")
    print(f"Portfolio Spoke: {results['portfolio']['passed']}/{results['portfolio']['total']} passed")
    print(f"\n{'='*80}")
    print(f"TOTAL:           {total_passed}/{total_tests} passed ({total_passed/total_tests*100:.1f}%)")
    print(f"                 {total_failed}/{total_tests} failed")
    print(f"{'='*80}\n")

    if total_failed == 0:
        print("[SUCCESS] All tests passed!")
    else:
        print(f"[WARNING] {total_failed} tests failed. Review logs above for details.")

    return total_failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
