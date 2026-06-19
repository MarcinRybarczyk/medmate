# MedMate — demo video script (medmate_demo.mp4)

Target: <= 5:00, 1280x720, captions burned in (silent build — no offline TTS
available). Segments are rendered to frames by `make_video.py` and assembled
with ffmpeg. Each caption below is what appears on-screen for that segment.

| # | Segment | ~sec | On-screen caption (narration) |
|---|---------|-----:|-------------------------------|
| 1 | Title | 7 | MedMate — a privacy-first medication concierge agent, built on Google's ADK. |
| 2 | Problem | 9 | People on several medications struggle to track timing, spot drug interactions, and prepare for short doctor visits. General chatbots hallucinate drug facts, drift into diagnosis, and leak personal health data. |
| 3 | Why agents | 9 | MedMate splits the job across specialists, grounds drug facts in real tools instead of model memory, and enforces hard safety rules: never diagnose, never change a medication, escalate emergencies. |
| 4 | Architecture | 10 | A root ConciergeAgent routes intent to three sub-agents. The InteractionAgent reaches a local "drug-info" MCP server over stdio. A security layer redacts PII before any model call — so health data stays on the host. |
| 5 | Terminal: routing | 11 | demo.py — offline routing preview: each request goes to the right specialist, and a described emergency is escalated to local emergency services. |
| 6 | Terminal: MCP call | 11 | Real MCP round-trip over stdio: the InteractionAgent calls check_interaction(warfarin, ibuprofen) — the tool returns a HIGH-severity interaction and a safety warning. Facts come from the tool, not the model. |
| 7 | Terminal: tests | 9 | pytest — 14 tests pass: tool logic, the PII redactor, and a real MCP-protocol integration test. No API key needed. |
| 8 | The Build | 9 | The Build: Google ADK 2.3.0 + MCP 1.28.0. Multi-agent routing, grounded MCP tools, PII redaction + non-diagnostic guardrails. 14 tests passing. Public repo, MIT. |
| 9 | Outro | 7 | MedMate — privacy-first medication concierge. github.com/MarcinRybarczyk/medmate |

Total ~82 s (well under the 5:00 limit).

Note on test count: the original plan mentioned "9 passed"; the suite has since
grown to **14** (9 unit + 5 integration). The video shows the real `pytest`
output (14 passed) — we do not fake a number.
