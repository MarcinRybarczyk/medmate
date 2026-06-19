"""Real MCP tool call over stdio (NO API key) — used in the demo video.

Spawns mcp_server.py as a stdio child (exactly as the agent does), lists the
tools, then calls check_interaction(warfarin, ibuprofen) and prints a readable
transcript including the interaction severity and the safety warning. This is
the genuine MCP protocol round-trip, not a mock.

Run:  python scripts/demo_mcp_call.py
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_HERE = os.path.dirname(os.path.abspath(__file__))
_SERVER = os.path.join(os.path.dirname(_HERE), "mcp_server.py")  # repo root


async def main():
    print("$ python mcp_server.py            # drug-info MCP server over stdio")
    params = StdioServerParameters(command=sys.executable, args=[_SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [t.name for t in (await session.list_tools()).tools]
            print(f"[agent]  connected to 'drug-info'; tools: {', '.join(tools)}")
            print("[agent]  InteractionAgent -> check_interaction(warfarin, ibuprofen)")
            res = await session.call_tool(
                "check_interaction", {"drug_a": "warfarin", "drug_b": "ibuprofen"}
            )
            data = json.loads(res.content[0].text)
            print(f"  found    : {data['found']}")
            print(f"  severity : {str(data.get('severity', '-')).upper()}")
            print(f"  effect   : {data.get('effect', '-')}")
            print(f"  WARNING  : {data['disclaimer']}")


if __name__ == "__main__":
    asyncio.run(main())
