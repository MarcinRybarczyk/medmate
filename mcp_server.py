"""
mcp_server.py — MedMate "drug-info" MCP server (Model Context Protocol).

WHY AN MCP SERVER (course concept #2 — grounded tool use):
    The InteractionAgent must NOT free-associate drug facts from the LLM's
    weights (that is how hallucinated medical claims happen). Instead it calls
    *named, read-only tools* whose answers come from a controlled data source.
    MCP gives us a clean, model-agnostic tool contract for exactly that.

PRIVACY POSTURE:
    This server speaks MCP over **stdio** and is spawned as a local child
    process by the agent (see agent.py). No network listener, no cloud call —
    the patient's drug list and questions never leave the host machine to reach
    the tool layer. That is the "privacy-first" claim, made concrete.

DEMO DATA — NOT FOR CLINICAL USE:
    The dataset below is a tiny, hand-written demo so the project runs offline
    with zero credentials. In production you would swap _DRUGS / _INTERACTIONS
    for a *licensed* source — e.g. NLM RxNorm / RxNav for normalization and the
    openFDA drug label + adverse-event APIs for interactions — behind the same
    two tool signatures. The agent code would not change.

Run standalone for a quick smoke test:
    python mcp_server.py        # starts the stdio server (no output until a client connects)
"""

from mcp.server.fastmcp import FastMCP

# The server NAME is part of the MCP contract; the agent references "drug-info".
mcp = FastMCP("drug-info")

# --------------------------------------------------------------------------- #
# Demo dataset (in-memory). Keys are lowercased generic names.                #
# Replace with RxNorm/openFDA lookups for real use — see module docstring.    #
# --------------------------------------------------------------------------- #
_DRUGS = {
    "ibuprofen": {
        "class": "NSAID (nonsteroidal anti-inflammatory drug)",
        "common_use": "pain, inflammation, fever",
        "notes": "Take with food. Can affect kidneys and raise blood pressure.",
    },
    "warfarin": {
        "class": "Anticoagulant (blood thinner)",
        "common_use": "prevents and treats blood clots",
        "notes": "Narrow therapeutic range; many food and drug interactions.",
    },
    "lisinopril": {
        "class": "ACE inhibitor",
        "common_use": "high blood pressure, heart failure",
        "notes": "Monitor potassium and kidney function.",
    },
    "metformin": {
        "class": "Biguanide",
        "common_use": "type 2 diabetes",
        "notes": "Usually taken with meals to reduce stomach upset.",
    },
    "aspirin": {
        "class": "NSAID / antiplatelet",
        "common_use": "pain, fever, low-dose clot prevention",
        "notes": "Increases bleeding risk, especially with other blood thinners.",
    },
}

# Interaction pairs keyed by a sorted (drug_a, drug_b) tuple so order does not matter.
_INTERACTIONS = {
    ("aspirin", "warfarin"): {
        "severity": "high",
        "effect": "Additive bleeding risk; combination markedly raises chance of bleeding.",
    },
    ("ibuprofen", "warfarin"): {
        "severity": "high",
        "effect": "NSAID + anticoagulant — increased bleeding and GI risk.",
    },
    ("ibuprofen", "lisinopril"): {
        "severity": "moderate",
        "effect": "NSAIDs can blunt blood-pressure control and stress the kidneys.",
    },
    ("aspirin", "ibuprofen"): {
        "severity": "moderate",
        "effect": "Ibuprofen can block aspirin's antiplatelet (heart-protective) effect.",
    },
}


def _norm(name: str) -> str:
    """Normalize a drug name for lookup (lowercase, trimmed)."""
    return (name or "").strip().lower()


@mcp.tool()
def check_interaction(drug_a: str, drug_b: str) -> dict:
    """Check for a known interaction between two drugs (read-only).

    Args:
        drug_a: First drug name (generic preferred), e.g. "warfarin".
        drug_b: Second drug name, e.g. "aspirin".

    Returns:
        A dict with `found` (bool), and when found `severity` + `effect`.
        Always includes a `disclaimer`. This is informational only — it never
        tells the user to start or stop a medication.
    """
    a, b = _norm(drug_a), _norm(drug_b)
    key = (a, b) if a <= b else (b, a)  # order-independent 2-tuple lookup key
    hit = _INTERACTIONS.get(key)
    base = {
        "drug_a": a,
        "drug_b": b,
        "disclaimer": (
            "Informational only, from a demo dataset. Not medical advice. "
            "Confirm with a pharmacist or clinician before changing anything."
        ),
    }
    if hit:
        return {**base, "found": True, "severity": hit["severity"], "effect": hit["effect"]}
    known = a in _DRUGS and b in _DRUGS
    return {
        **base,
        "found": False,
        "note": (
            "No interaction in the demo dataset."
            if known
            else "One or both drugs are not in the demo dataset; absence is NOT a safety guarantee."
        ),
    }


@mcp.tool()
def drug_summary(name: str) -> dict:
    """Return a plain-language summary for a single drug (read-only).

    Args:
        name: Drug name (generic preferred), e.g. "metformin".

    Returns:
        A dict with `found` (bool) and, when found, `class` / `common_use` /
        `notes`, plus a `disclaimer`. Descriptive only — no dosing advice.
    """
    n = _norm(name)
    info = _DRUGS.get(n)
    disclaimer = (
        "Informational only, from a demo dataset. Not medical advice and not dosing guidance."
    )
    if info:
        return {"found": True, "name": n, **info, "disclaimer": disclaimer}
    return {
        "found": False,
        "name": n,
        "note": "Not in the demo dataset. In production this would query RxNorm/openFDA.",
        "disclaimer": disclaimer,
    }


if __name__ == "__main__":
    # Default transport is stdio: the process reads MCP requests on stdin and
    # writes responses on stdout. agent.py launches this exact command as a
    # child process, so the tool layer stays entirely on the local host.
    mcp.run()
