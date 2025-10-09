#!/usr/bin/env python3
"""
Risk Spoke MCP Server - Simplified Version
"""
import sys
import asyncio
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Create server
server = Server("fin-hub-risk")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="var_calculator",
            description="Calculate Value at Risk (VaR) using multiple methods",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "portfolio_value": {"type": "number"},
                    "confidence_level": {"type": "number"}
                },
                "required": ["symbol", "portfolio_value"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    if name == "var_calculator":
        return [types.TextContent(
            type="text",
            text="VaR calculation: simplified version working!"
        )]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="fin-hub-risk",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=mcp.server.NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
