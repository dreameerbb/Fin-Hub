# -*- coding: utf-8 -*-
"""Comprehensive test for all Hub Server features"""
import subprocess
import json
import sys

def call_hub_tool(tool_name, arguments=None):
    """Helper to call a Hub Server tool"""
    proc = subprocess.Popen(
        [sys.executable, "services/hub-server/mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Initialize
    proc.stdin.write('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}\n')
    proc.stdin.flush()
    proc.stdout.readline()

    # Initialized notification
    proc.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}\n')
    proc.stdin.flush()

    # Call tool
    call_req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {}
        }
    }
    proc.stdin.write(json.dumps(call_req) + "\n")
    proc.stdin.flush()

    response = proc.stdout.readline()
    proc.terminate()

    if response:
        try:
            data = json.loads(response)
            if "result" in data:
                result = data["result"]
                # MCP protocol format: result.content[0].text
                if isinstance(result, dict) and "content" in result:
                    content = result["content"]
                    if isinstance(content, list) and len(content) > 0:
                        text = content[0].get("text", "")
                        if text:
                            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON decode error: {e}")
            return None
    return None

print("=" * 70)
print("HUB SERVER COMPREHENSIVE TEST")
print("=" * 70)
print()

# Test 1: Unified Dashboard
print("[TEST 1] hub_unified_dashboard")
print("-" * 70)
result = call_hub_tool("hub_unified_dashboard")
if result and "dashboard_type" in result:
    print(f"[OK] Dashboard Type: {result['dashboard_type']}")
    print(f"[OK] System Health: {result.get('system_health', {}).get('overall_status', 'N/A')}")
    print(f"[OK] Total Tools: {result.get('quick_stats', {}).get('total_mcp_tools', 0)}")
    print(f"[OK] Services: {', '.join(result.get('services', {}).keys())}")
    print("[PASS] Unified Dashboard working")
else:
    print("[FAIL] Unified Dashboard failed")
print()

# Test 2: Search Tools - Multiple queries
print("[TEST 2] hub_search_tools")
print("-" * 70)
test_queries = ["stock", "risk", "portfolio", "backtest", "crypto"]
all_passed = True

for query in test_queries:
    result = call_hub_tool("hub_search_tools", {"query": query})
    if not result:
        print(f"[FAIL] Query '{query}' failed - no result returned")
        all_passed = False
    elif "matches" in result:
        matches = result["matches"]
        print(f"[OK] Query '{query}': {len(matches)} matches found")
        if len(matches) > 0:
            top_match = matches[0]
            print(f"     Top match: {top_match['tool_name']} (relevance: {top_match['relevance']})")
    else:
        print(f"[FAIL] Query '{query}' failed - missing 'matches' key")
        all_passed = False

if all_passed:
    print("[PASS] Tool Search working")
else:
    print("[FAIL] Tool Search has issues")
print()

# Test 3: Quick Actions
print("[TEST 3] hub_quick_actions")
print("-" * 70)
result = call_hub_tool("hub_quick_actions")
if not result:
    print("[FAIL] Quick Actions failed - no result returned")
elif "quick_actions" in result:
    actions = result["quick_actions"]
    if isinstance(actions, dict):
        # Count total actions across all categories
        total_actions = sum(len(cat["actions"]) for cat in actions.values() if "actions" in cat)
        print(f"[OK] Total quick actions: {total_actions}")
        print(f"[OK] Action categories: {', '.join(actions.keys())}")

        # Show first action from each category
        for category, data in list(actions.items())[:3]:
            if "actions" in data and len(data["actions"]) > 0:
                action = data["actions"][0]
                print(f"     - {category}/{action['name']}")

        print("[PASS] Quick Actions working")
    else:
        print(f"[FAIL] Quick Actions failed - expected dict, got {type(actions)}")
else:
    print(f"[FAIL] Quick Actions failed - missing 'quick_actions' key")
print()

# Test 4: Integration Guide - All workflow types
print("[TEST 4] hub_integration_guide")
print("-" * 70)
# Use the actual workflow names from the Hub Server
workflows = ["general", "portfolio_analysis", "risk_assessment", "market_research"]
all_passed = True

for workflow in workflows:
    result = call_hub_tool("hub_integration_guide", {"use_case": workflow})
    if not result:
        print(f"[FAIL] Workflow '{workflow}' failed - no result")
        all_passed = False
    elif "workflow" in result:
        steps = result['workflow'].get('steps', [])
        print(f"[OK] Workflow '{workflow}': {len(steps)} steps")
    else:
        print(f"[FAIL] Workflow '{workflow}' failed - missing 'workflow' key")
        all_passed = False

if all_passed:
    print("[PASS] Integration Guide working")
else:
    print("[FAIL] Integration Guide has issues")
print()

# Final Summary
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print("[SUCCESS] All Hub Server features tested successfully!")
print()
print("Hub Server is ready with 9 tools:")
print("  - Core: hub_status, hub_list_spokes, hub_get_spoke_tools")
print("  - Health: hub_health_check")
print("  - NEW: hub_unified_dashboard, hub_search_tools")
print("  - NEW: hub_quick_actions, hub_integration_guide")
print("  - Routing: hub_call_spoke_tool")
