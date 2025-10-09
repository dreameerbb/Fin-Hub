# -*- coding: utf-8 -*-
"""Test Hub Server system metrics"""
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

# Initialize
proc.stdin.write('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}\n')
proc.stdin.flush()
proc.stdout.readline()

# Initialized notification
proc.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}\n')
proc.stdin.flush()

# Call system metrics
proc.stdin.write('{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"hub_system_metrics","arguments":{}}}\n')
proc.stdin.flush()

response = proc.stdout.readline()
proc.terminate()

print("=" * 70)
print("HUB SYSTEM METRICS TEST")
print("=" * 70)
print()

if response:
    data = json.loads(response)
    print(f"[DEBUG] Full response: {json.dumps(data, indent=2)[:500]}\n")
    if "result" in data and "content" in data["result"]:
        text = data["result"]["content"][0]["text"]
        result = json.loads(text)
        print(f"[DEBUG] Parsed result keys: {result.keys()}\n")

        # Check if psutil is installed
        if "error" in result:
            print("[WARN] psutil not installed")
            print(f"Message: {result.get('message', '')}")
            if "basic_metrics" in result:
                print("\n[OK] Basic metrics fallback working")
                basic = result['basic_metrics']
                print(f"Timestamp: {basic.get('timestamp', 'N/A')}")
                spokes = basic.get('spokes', [])
                print(f"Spokes: {len(spokes)}")
                for spoke in spokes:
                    print(f"  - {spoke.get('name', 'unknown')}: {spoke.get('status', 'unknown')}")
        else:
            print("[OK] System Metrics Retrieved Successfully!")
            print()

            # System
            if "system" in result:
                sys_metrics = result["system"]
                print(f"[CPU] {sys_metrics.get('cpu_percent', 0)}% ({sys_metrics.get('cpu_count', 0)} cores)")
                mem = sys_metrics.get("memory", {})
                print(f"[Memory] {mem.get('percent', 0)}% used ({mem.get('used_gb', 0):.2f} / {mem.get('total_gb', 0):.2f} GB)")
                disk = sys_metrics.get("disk", {})
                print(f"[Disk] {disk.get('percent', 0)}% used ({disk.get('used_gb', 0):.1f} / {disk.get('total_gb', 0):.1f} GB)")

            # Hub Process
            if "hub_process" in result:
                hub = result["hub_process"]
                print(f"\n[Hub Process]")
                print(f"  Memory: {hub.get('memory_mb', 0):.2f} MB")
                print(f"  CPU: {hub.get('cpu_percent', 0):.1f}%")
                print(f"  Threads: {hub.get('threads', 0)}")

            # Spokes
            if "spokes" in result:
                print(f"\n[Spokes]")
                for spoke_name, spoke_data in result["spokes"].items():
                    status = spoke_data.get("status", "unknown")
                    if status == "healthy":
                        print(f"  {spoke_name}: OK ({spoke_data.get('response_time_ms', 0):.2f}ms)")
                    else:
                        print(f"  {spoke_name}: {status.upper()}")

            # Summary
            if "summary" in result:
                summary = result["summary"]
                print(f"\n[Summary]")
                print(f"  System Health: {summary.get('system_health', 'unknown').upper()}")
                print(f"  Spokes Online: {summary.get('spokes_online', 0)}/{summary.get('total_spokes', 0)}")
                print(f"  Avg Response Time: {summary.get('avg_response_time_ms', 0):.2f}ms")

        print("\n[SUCCESS] System Metrics test completed!")
    else:
        print("[FAIL] Invalid response format")
        print(f"Response: {data}")
else:
    print("[FAIL] No response received")
