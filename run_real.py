"""run_real.py — REAL end-to-end agent run against the live LLM (3 queries).

Loads GOOGLE_API_KEY from .env via python-dotenv (never printed; aborts if
missing). Runs MedMate through the ADK InMemoryRunner for three prompts that
should exercise each sub-agent, captures the events (which agent answered, any
MCP tool calls, the final text), redacts PII with agent.redact(), and writes a
transcript to logs/real_run.txt. Prints a routing / MCP / disclaimer summary.

Uses the cheap gemini-2.5-flash default (set in agent.py) and only 3 prompts to
keep cost minimal.

Run:  python run_real.py
"""
import asyncio
import os
import sys
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

if not os.environ.get("GOOGLE_API_KEY"):
    print("ABORT: GOOGLE_API_KEY is not set. Put it in .env (GOOGLE_API_KEY=...) "
          "or your environment. Never commit it.")
    sys.exit(2)

from google.adk.runners import InMemoryRunner          # noqa: E402
from google.genai import types                          # noqa: E402
from agent import root_agent, redact                    # noqa: E402

QUERIES = [
    ("schedule",
     "I take metformin 500mg at 8am and lisinopril 10mg at night. "
     "Build me a simple daily reminder schedule."),
    ("interaction",
     "Can I take warfarin with ibuprofen?"),
    ("visit_prep",
     "Help me prepare questions for my doctor about my blood pressure."),
]

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "real_run.txt")
DISCLAIMER_HINTS = ("pharmacist", "clinician", "doctor", "not medical advice",
                    "informational", "professional", "emergency")


def run():
    runner = InMemoryRunner(agent=root_agent, app_name="medmate")
    session = asyncio.run(
        runner.session_service.create_session(app_name="medmate", user_id="demo")
    )
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    out = ["MedMate — real end-to-end run (live LLM). PII redacted.\n" + "=" * 60]
    summary = []

    for tag, q in QUERIES:
        authors, tool_calls, final = [], [], ""
        out.append(f"\n### [{tag}] USER: {redact(q)}")
        try:
            msg = types.Content(role="user", parts=[types.Part(text=q)])
            for ev in runner.run(user_id="demo", session_id=session.id, new_message=msg):
                a = getattr(ev, "author", None)
                if a and a not in authors:
                    authors.append(a)
                content = getattr(ev, "content", None)
                for part in (getattr(content, "parts", None) or []):
                    fc = getattr(part, "function_call", None)
                    if fc is not None:
                        tool_calls.append(getattr(fc, "name", "?"))
                        out.append(f"  [tool call] {getattr(fc, 'name', '?')}({dict(getattr(fc, 'args', {}) or {})})")
                    fr = getattr(part, "function_response", None)
                    if fr is not None:
                        out.append(f"  [tool result] {getattr(fr, 'name', '?')} -> (received)")
                    txt = getattr(part, "text", None)
                    if txt:
                        final = txt
            out.append(f"  AGENTS: {', '.join(authors)}")
            out.append(f"  TOOLS : {', '.join(tool_calls) or '(none)'}")
            out.append("  FINAL : " + redact(final).strip())
            disc = any(h in final.lower() for h in DISCLAIMER_HINTS)
            summary.append((tag, authors, tool_calls, disc))
        except Exception as e:
            out.append(f"  ERROR: {type(e).__name__}")
            summary.append((tag, authors, tool_calls, False))

    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")

    print("=== REAL RUN SUMMARY ===")
    for tag, authors, tools, disc in summary:
        print(f"[{tag}] agents={authors} tools={tools or '(none)'} disclaimer={'YES' if disc else 'no'}")
    print(f"transcript -> {LOG}")


if __name__ == "__main__":
    t0 = time.time()
    run()
    print(f"done in {time.time() - t0:.1f}s")
