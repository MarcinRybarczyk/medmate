"""Lightweight tests for the drug-info MCP tools and the PII redactor.

No network and no model calls — these exercise the pure tool functions in
mcp_server.py and the redact() helper from agent.py. See conftest.py for the
sys.path + dummy-key setup that lets `import agent` succeed offline.
"""
import mcp_server as srv
from agent import redact


# --- check_interaction --------------------------------------------------- #
def test_check_interaction_known_pair():
    r = srv.check_interaction("aspirin", "warfarin")
    assert r["found"] is True
    assert r["severity"] == "high"
    assert "disclaimer" in r


def test_check_interaction_order_independent():
    # same pair, reversed argument order -> same result
    assert srv.check_interaction("warfarin", "aspirin")["found"] is True


def test_check_interaction_no_interaction_for_known_pair():
    # both drugs are in the demo dataset but have no listed interaction
    r = srv.check_interaction("metformin", "lisinopril")
    assert r["found"] is False
    assert "no interaction" in r["note"].lower()


def test_check_interaction_unknown_drug():
    r = srv.check_interaction("aspirin", "totally-made-up-drug")
    assert r["found"] is False
    assert "not in the demo dataset" in r["note"].lower()


# --- drug_summary -------------------------------------------------------- #
def test_drug_summary_known():
    r = srv.drug_summary("metformin")
    assert r["found"] is True
    assert r["name"] == "metformin"
    assert "class" in r and "common_use" in r


def test_drug_summary_unknown():
    r = srv.drug_summary("made-up-drug")
    assert r["found"] is False
    assert "disclaimer" in r


# --- redact() PII scrubber ----------------------------------------------- #
def test_redact_masks_pii():
    text = "SSN 123-45-6789, email john.doe@example.com, member id 123456789012"
    out = redact(text)
    assert "123-45-6789" not in out and "[REDACTED_SSN]" in out
    assert "john.doe@example.com" not in out and "[REDACTED_EMAIL]" in out
    assert "123456789012" not in out and "[REDACTED_ID]" in out


def test_redact_keeps_normal_medical_text():
    # doses and years (short digit runs) must NOT be redacted
    assert redact("take 500 mg twice daily since 2025") == "take 500 mg twice daily since 2025"


def test_redact_empty_input():
    assert redact("") == ""
