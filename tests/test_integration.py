"""Integration tests — exercise the REAL wiring, not just pure functions.

These spawn mcp_server.py as a stdio child process and talk to it over the
actual MCP protocol, then verify the ADK McpToolset connects and lists the same
tools, and that the redact() before-model callback mutates a request in place.

No model / API key is used (a dummy key from conftest lets `import agent`
succeed). The ONLY thing not covered here is the live-LLM routing inside
`adk web` / `adk run`, which needs a real GOOGLE_API_KEY and paid quota — see
README "Verification".

Sync tests wrap async calls with asyncio.run() so no pytest-asyncio is needed.
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SERVER = os.path.join(_REPO, "mcp_server.py")


async def _list_tool_names():
    params = StdioServerParameters(command=sys.executable, args=[_SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            res = await session.list_tools()
            return sorted(t.name for t in res.tools)


async def _call(tool, args):
    params = StdioServerParameters(command=sys.executable, args=[_SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            res = await session.call_tool(tool, args)
            # FastMCP serializes the dict return into the text content block.
            return json.loads(res.content[0].text)


# --- real MCP protocol over stdio ---------------------------------------- #
def test_mcp_server_lists_tools_over_stdio():
    assert _run(_list_tool_names()) == ["check_interaction", "drug_summary"]


def test_mcp_check_interaction_over_stdio():
    out = _run(_call("check_interaction", {"drug_a": "aspirin", "drug_b": "warfarin"}))
    assert out["found"] is True and out["severity"] == "high"


def test_mcp_drug_summary_over_stdio():
    out = _run(_call("drug_summary", {"name": "metformin"}))
    assert out["found"] is True and out["name"] == "metformin"


# --- ADK McpToolset actually connects to the server ---------------------- #
def test_adk_toolset_connects_and_lists_tools():
    import agent
    tools = _run(agent.drug_info_toolset.get_tools())
    names = sorted(t.name for t in tools)
    assert names == ["check_interaction", "drug_summary"]


# --- redact before-model callback mutates the request in place ----------- #
def test_redact_before_model_callback_scrubs_request():
    import agent

    class _Part:
        def __init__(self, text):
            self.text = text

    class _Content:
        def __init__(self, parts):
            self.parts = parts

    class _Req:
        def __init__(self, contents):
            self.contents = contents

    req = _Req([_Content([_Part("SSN 123-45-6789, mail a@b.com, id 123456789012")])])
    ret = agent._redact_before_model(None, req)  # None => proceed with mutated request
    assert ret is None
    scrubbed = req.contents[0].parts[0].text
    assert "[REDACTED_SSN]" in scrubbed
    assert "[REDACTED_EMAIL]" in scrubbed
    assert "[REDACTED_ID]" in scrubbed
    assert "123-45-6789" not in scrubbed and "a@b.com" not in scrubbed


# --- helper: run an async coroutine from a sync test --------------------- #
def _run(coro):
    return asyncio.run(coro)
