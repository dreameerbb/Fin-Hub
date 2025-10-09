# -*- coding: utf-8 -*-
"""Test Hub Server tools"""
import subprocess
import json
import sys

def test_hub_tool(tool_name):
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

    # List tools
    proc.stdin.write('{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n')
    proc.stdin.flush()
    tools_resp = proc.stdout.readline()
    tools_data = json.loads(tools_resp)

    print(f"Available tools: {len(tools_data['result']['tools'])}")
    for i, tool in enumerate(tools_data['result']['tools'], 1):
        print(f"  {i}. {tool['name']}")

    # Call tool
    print(f"\nTesting: {tool_name}")
    print("="*60)
    call_req = {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":tool_name,"arguments":{}}}
    proc.stdin.write(json.dumps(call_req) + "\n")
    proc.stdin.flush()

    response = proc.stdout.readline()
    proc.terminate()

    if response:
        data = json.loads(response)
        if "result" in data and data["result"]:
            text = data["result"][0].get("content", [{}])[0].get("text", "")
            result = json.loads(text)
            print(json.dumps(result, indent=2))
            return True
    return False


print("="*60)
print("HUB SERVER TEST")
print("="*60)
print()

# Test unified dashboard
success = test_hub_tool("hub_unified_dashboard")
if success:
    print("\n[SUCCESS] Hub Server is working!")
else:
    print("\n[FAIL] Hub Server test failed")
