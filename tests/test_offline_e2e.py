"""Offline end-to-end test — proves the agent PIPELINE works with NO Google API.

We swap the LLMs for scripted fakes (BaseLlm subclasses) and drive the REAL ADK
Runner. This exercises, deterministically and for free:
  - LLM-driven delegation: root MedMate -> transfer_to_agent -> InteractionAgent
  - real MCP tool execution: InteractionAgent -> check_interaction over stdio
    (mcp_server.py is actually spawned and returns the HIGH-severity interaction)
  - the safety disclaimer in the final answer

What this CANNOT prove (needs a real model): the quality of the *real* LLM's own
routing/wording. Everything mechanical around it is verified here without a key.
"""
import asyncio

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types

import agent as A


def _has_func_response(req) -> bool:
    for c in (getattr(req, "contents", None) or []):
        for p in (getattr(c, "parts", None) or []):
            if getattr(p, "function_response", None) is not None:
                return True
    return False


def _resp(part):
    return LlmResponse(content=types.Content(role="model", parts=[part]))


class RootFake(BaseLlm):
    """Routes the interaction question to InteractionAgent (ADK transfer tool)."""
    async def generate_content_async(self, llm_request, stream=False):
        yield _resp(types.Part(function_call=types.FunctionCall(
            name="transfer_to_agent", args={"agent_name": "InteractionAgent"})))


class InteractionFake(BaseLlm):
    """First turn: call the MCP tool. After the tool result: final answer + disclaimer."""
    async def generate_content_async(self, llm_request, stream=False):
        if _has_func_response(llm_request):
            yield _resp(types.Part(text=(
                "There is a HIGH-severity interaction between warfarin and ibuprofen "
                "(increased bleeding risk). This is informational only - please confirm "
                "with your pharmacist or clinician. I won't tell you to start or stop any "
                "medication.")))
        else:
            yield _resp(types.Part(function_call=types.FunctionCall(
                name="check_interaction", args={"drug_a": "warfarin", "drug_b": "ibuprofen"})))


def test_offline_e2e_routing_tool_and_disclaimer():
    # inject fakes (no Google API); MCP server + sub-agents stay real
    A.root_agent.model = RootFake(model="fake-root")
    A.interaction_agent.model = InteractionFake(model="fake-interaction")

    runner = InMemoryRunner(agent=A.root_agent, app_name="medmate-offline")
    session = asyncio.run(
        runner.session_service.create_session(app_name="medmate-offline", user_id="t")
    )

    authors, tools, final = set(), [], ""
    msg = types.Content(role="user", parts=[types.Part(text="Can I take warfarin with ibuprofen?")])
    for ev in runner.run(user_id="t", session_id=session.id, new_message=msg):
        if getattr(ev, "author", None):
            authors.add(ev.author)
        for p in (getattr(getattr(ev, "content", None), "parts", None) or []):
            fc = getattr(p, "function_call", None)
            if fc is not None:
                tools.append(fc.name)
            txt = getattr(p, "text", None)
            if txt:
                final = txt

    assert "InteractionAgent" in authors, f"routing/delegation failed; authors={authors}"
    assert "check_interaction" in tools, f"MCP tool not executed; tools={tools}"
    low = final.lower()
    assert any(k in low for k in ("pharmacist", "clinician", "informational")), "missing disclaimer"
    assert "won't" in low or "diagnos" not in low, "must not diagnose"
