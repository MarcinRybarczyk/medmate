"""demo.py — illustrative routing walkthrough (NO API CALLS, no cost).

Shows which sub-agent MedMate would hand each example request to, plus the
emergency-escalation guardrail. Handy for narrating the demo video without
spending API quota.

IMPORTANT: the REAL routing is LLM-driven by the ADK root agent at runtime.
This script uses simple keyword heuristics ONLY — it is an offline illustration
of the intended behavior, not the actual model decision.

Run:  python demo.py
"""

# (input, the sub-agent we expect MedMate to route to)
SCENARIOS = [
    ("I take metformin at 8am and lisinopril at night - build me a reminder schedule.",
     "ScheduleAgent"),
    ("Is it safe to take aspirin together with warfarin?",
     "InteractionAgent"),
    ("I've been dizzy lately - help me prepare questions for my doctor visit.",
     "VisitPrepAgent"),
    ("I have crushing chest pain and can't breathe.",
     "EMERGENCY -> escalate to local emergency services"),
]


def route(text: str) -> str:
    """Illustrative keyword router (NOT the model). Emergency check comes first."""
    t = text.lower()
    if any(k in t for k in ("chest pain", "can't breathe", "cant breathe",
                            "overdose", "suicid", "stroke", "anaphyla")):
        return "EMERGENCY -> escalate to local emergency services (112 / 911)"
    if any(k in t for k in ("interact", "together with", "safe to take", "combine", "mix")):
        return "InteractionAgent (calls drug-info MCP tools)"
    if any(k in t for k in ("schedule", "reminder", "when to take", "times", "8am", "night")):
        return "ScheduleAgent"
    if any(k in t for k in ("doctor", "visit", "appointment", "question", "prep")):
        return "VisitPrepAgent"
    return "MedMate (asks the user to clarify intent)"


if __name__ == "__main__":
    print("MedMate — illustrative routing (offline, no API calls)\n" + "=" * 56)
    for text, expected in SCENARIOS:
        print(f"\nUSER: {text}\n  -> route: {route(text)}\n     (expected: {expected})")
    print("\nNote: real routing is decided by the ADK LLM at runtime; this is a heuristic preview.")
