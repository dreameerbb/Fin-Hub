# -*- coding: utf-8 -*-
"""Debug integration_guide responses"""
import subprocess
import json
import sys

def test_workflow(workflow_name):
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
            "name": "hub_integration_guide",
            "arguments": {"use_case": workflow_name}
        }
    }
    proc.stdin.write(json.dumps(call_req) + "\n")
    proc.stdin.flush()

    response = proc.stdout.readline()
    stderr = proc.stderr.read()
    proc.terminate()

    print(f"=== Testing workflow: {workflow_name} ===")
    print(f"Response: {response[:500]}")
    if stderr:
        print(f"Stderr: {stderr[:500]}")
    print()

workflows = ["stock_analysis", "portfolio_management", "risk_assessment", "crypto_tracking"]
for w in workflows:
    test_workflow(w)
