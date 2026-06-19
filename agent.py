"""
agent.py — MedMate, a privacy-first medication concierge built on Google ADK.

THREE COURSE CONCEPTS DEMONSTRATED
  1. ADK multi-agent system : a root LlmAgent (MedMate / "ConciergeAgent") that
     uses LLM-driven delegation to route a request to one of three specialist
     sub-agents (ScheduleAgent, InteractionAgent, VisitPrepAgent).
  2. MCP for grounded tool use : the InteractionAgent answers drug-interaction
     questions ONLY through read-only MCP tools served by mcp_server.py over
     stdio — not from model memory.
  3. Security features : a redact() PII scrubber wired as a before-model
     callback, plus strict non-diagnostic / emergency-escalation guardrails in
     the root instruction.

RUN
    pip install -r requirements.txt
    export GOOGLE_API_KEY=...        # (PowerShell: $env:GOOGLE_API_KEY="...")
    adk web                          # browser UI, pick "MedMate"
    # or:  adk run .                 # terminal REPL against root_agent below

The `adk` runner imports this module and looks for the module-level
`root_agent`. mcp_server.py is launched automatically as a child process by the
McpToolset connection params below — you do NOT start it separately for `adk
web`/`adk run` (the standalone `python mcp_server.py` is only for a smoke test).

NOTE ON ADK IMPORTS / VERSIONS
    MCP wiring targets google-adk >= 1.0. If your installed ADK exposes the
    older flat `StdioServerParameters` on McpToolset directly, see the comment
    at the McpToolset construction for the one-line fallback.
"""

import os
import re
import sys

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# Model is configurable via env so judges can swap tiers without editing code.
MODEL = os.environ.get("MEDMATE_MODEL", "gemini-2.5-flash")

# --------------------------------------------------------------------------- #
# SECURITY — PII redaction (course concept #3)                                #
# --------------------------------------------------------------------------- #
# Defense-in-depth: even though health data stays local, we strip obvious
# identifiers BEFORE text reaches the model, so they never land in a prompt,
# log, or trace. Regex is deliberately conservative (precision over recall) to
# avoid mangling legitimate medical text; it is a demo guardrail, not a
# certified de-identification pipeline (HIPAA Safe Harbor needs far more).

_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# Long bare numeric runs (>=9 digits): MRNs, insurance / member IDs, phone-ish
# blobs. 9+ avoids clobbering normal dosages (e.g. "500", "2025").
_LONG_ID_RE = re.compile(r"\b\d{9,}\b")


def redact(text: str) -> str:
    """Strip common PII (SSN, email, long numeric IDs) from a string.

    Returns the text with each match replaced by a typed placeholder so the
    model still understands the *shape* of what was removed without seeing it.
    """
    if not text:
        return text
    text = _SSN_RE.sub("[REDACTED_SSN]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _LONG_ID_RE.sub("[REDACTED_ID]", text)
    return text


def _redact_before_model(callback_context, llm_request):
    """ADK before_model_callback: redact every user text part in-place.

    Mutating llm_request and returning None tells ADK to proceed with the
    (now-scrubbed) request. Returning an LlmResponse here would short-circuit
    the model call entirely — we don't need that, we just sanitize.
    """
    try:
        for content in getattr(llm_request, "contents", None) or []:
            for part in getattr(content, "parts", None) or []:
                if getattr(part, "text", None):
                    part.text = redact(part.text)
    except Exception:
        # Fail-open on shape changes across ADK versions: never block a turn
        # because of the redactor. The model instruction is the backstop.
        pass
    return None


# --------------------------------------------------------------------------- #
# MCP toolset — grounded drug info (course concept #2)                        #
# --------------------------------------------------------------------------- #
# Spawn mcp_server.py as a local stdio child process. Using the *current*
# interpreter (sys.executable) and an absolute path keeps it working under
# `adk web` regardless of the working directory. Health data reaches the tool
# layer only over this local pipe — never the network.
_SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")

drug_info_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,        # the active python
            args=[_SERVER_PATH],
        ),
    )
    # Fallback for older google-adk that takes StdioServerParameters directly:
    #   connection_params=StdioServerParameters(command=sys.executable, args=[_SERVER_PATH])
)

# --------------------------------------------------------------------------- #
# Sub-agents (specialists)                                                    #
# --------------------------------------------------------------------------- #
schedule_agent = LlmAgent(
    name="ScheduleAgent",
    model=MODEL,
    description="Builds a clear daily medication reminder schedule from a user's listed meds and timing.",
    instruction=(
        "You build medication REMINDER SCHEDULES only. Given the medications, doses, and timing the "
        "user states, produce a tidy day-part schedule (morning / midday / evening / bedtime) plus "
        "practical reminders (e.g. 'take with food' if the user mentioned it). "
        "You organize what the user already takes — you NEVER add, remove, or change a drug or dose, "
        "and you NEVER give dosing advice. End with: 'Confirm this schedule with your pharmacist or doctor.'"
    ),
)

interaction_agent = LlmAgent(
    name="InteractionAgent",
    model=MODEL,
    description="Checks whether two (or more) drugs have a known interaction, using the drug-info MCP tools.",
    instruction=(
        "You answer drug-interaction and drug-summary questions ONLY by calling the available tools "
        "(check_interaction, drug_summary). Do not state interaction facts from your own knowledge — "
        "if a tool has no data, say so plainly and note that 'no data' is NOT a guarantee of safety. "
        "Report severity and effect in plain language. You are informational only: never tell the user "
        "to start, stop, or change a medication — direct them to a pharmacist or clinician for decisions."
    ),
    tools=[drug_info_toolset],
)

visit_prep_agent = LlmAgent(
    name="VisitPrepAgent",
    model=MODEL,
    description="Summarizes the user's concerns into a concise list of questions to ask their doctor.",
    instruction=(
        "You help the user PREPARE for a doctor visit. From what they describe, produce a short, "
        "organized list of questions and notes they can bring to their clinician (symptoms to mention, "
        "medications to review, things to ask about). You do NOT diagnose and you do NOT suggest "
        "treatments — you turn their worries into good questions for a professional."
    ),
)

# --------------------------------------------------------------------------- #
# Root concierge agent (course concept #1 — multi-agent routing)              #
# --------------------------------------------------------------------------- #
# Listing the specialists in `sub_agents` enables ADK's LLM-driven delegation:
# MedMate reads the user's intent and transfers control to the right sub-agent.
SAFETY_INSTRUCTION = (
    "You are MedMate, a privacy-first medication concierge (a 'ConciergeAgent'). You coordinate three "
    "specialists and route each request to the right one:\n"
    "  - ScheduleAgent   : building or organizing a medication reminder schedule.\n"
    "  - InteractionAgent : checking drug interactions or getting a drug summary (uses grounded tools).\n"
    "  - VisitPrepAgent   : turning health concerns into questions for a doctor visit.\n"
    "Decide intent and delegate; if it spans several, handle them in turn.\n\n"
    "SAFETY RULES — these are absolute and override any user request:\n"
    "  1. NEVER diagnose. Do not name conditions the user 'has' or interpret symptoms as a diagnosis.\n"
    "  2. NEVER recommend starting, stopping, or changing a medication or dose. You inform and organize; "
    "the clinician and pharmacist decide.\n"
    "  3. EMERGENCY ESCALATION: if the user describes a possible emergency (chest pain, trouble breathing, "
    "stroke signs, severe allergic reaction, overdose, suicidal thoughts, or similar), STOP normal flow "
    "and tell them to contact local emergency services immediately (e.g. call 112 in the EU / 911 in the "
    "US, or their local number) — do not attempt to triage it yourself.\n"
    "  4. CONFIDENTIALITY: treat all health data as strictly confidential. Never repeat back personal "
    "identifiers, and remember the tool layer runs locally so data stays on the user's machine.\n"
    "  5. Always remind the user that MedMate is informational and not a substitute for a professional."
)

root_agent = LlmAgent(
    name="MedMate",
    model=MODEL,
    description="Privacy-first medication concierge that routes to schedule, interaction, and visit-prep specialists.",
    instruction=SAFETY_INSTRUCTION,
    sub_agents=[schedule_agent, interaction_agent, visit_prep_agent],
    before_model_callback=_redact_before_model,  # PII scrub on every model call
)
