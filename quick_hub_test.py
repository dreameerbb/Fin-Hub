# -*- coding: utf-8 -*-
import subprocess
import json
import sys

proc = subprocess.Popen(
    [sys.executable, "services/hub-server/mcp_server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Init
proc.stdin.write('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}\n')
proc.stdin.flush()
print("INIT:", proc.stdout.readline()[:100])

# Notification
proc.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}\n')
proc.stdin.flush()

# List tools
proc.stdin.write('{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n')
proc.stdin.flush()
tools = json.loads(proc.stdout.readline())
print(f"\nTools: {len(tools['result']['tools'])}")

# Call dashboard
proc.stdin.write('{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"hub_unified_dashboard","arguments":{}}}\n')
proc.stdin.flush()
resp = proc.stdout.readline()
print(f"\nRaw response: {resp[:200]}")

data = json.loads(resp)
print(f"\nResponse keys: {data.keys()}")
if "result" in data:
    print(f"Result type: {type(data['result'])}")
    print(f"Result: {data['result']}")

proc.terminate()
