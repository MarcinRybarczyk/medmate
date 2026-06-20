# Real-API verification — status (PARKED)

**State:** PARKED — waiting for Google Gemini paid quota to activate. The project
is complete and verified WITHOUT the API; only the live-LLM run remains, blocked
by a quota issue on the key/project (not by the code).

## What is verified (no API key needed) — 15 tests pass

| Area | How verified |
|------|--------------|
| Imports / agent graph (root MedMate + 3 sub-agents) | import-verified on google-adk 2.3.0 |
| MCP protocol over stdio (list + call both tools) | `tests/test_integration.py` |
| ADK `McpToolset` connects to the server | `tests/test_integration.py` |
| **Routing/delegation + real MCP tool execution + disclaimer** | `tests/test_offline_e2e.py` (fake LLMs drive the real ADK Runner; `mcp_server.py` actually spawned, `check_interaction` executed) |
| `redact()` PII scrubber (SSN/email/long IDs) | unit + integration |
| Tool logic (interactions / summaries) | 9 unit tests |

Run: `pip install -r requirements-dev.txt && pytest -q`  ->  **15 passed**.

## The blocker (live LLM only)

- `smoke_test.py` reaches Google and authenticates, but returns
  **`429 RESOURCE_EXHAUSTED`** with **`free_tier ... limit: 0`** for gemini-2.0-flash.
- Polled hourly across 6 retries overnight (Marcin added a billing card) — still `limit: 0`.
- Key prefix is `AQ.` (atypical — standard Gemini Developer API keys are `AIza...`);
  key's project = `403589364420`.
- Interpretation: paid tier is NOT active for this key's project (billing may be on
  a different project, propagation still pending, or the `AQ.` key type doesn't carry
  Gemini Developer free/paid quota).

## How to resume (when quota is live)

1. Ensure billing is enabled on project **403589364420** (the key's project), OR
   generate a standard `AIza...` key in a billed project at
   https://aistudio.google.com/apikey
2. Put it in `.env` (gitignored): `GOOGLE_API_KEY=...`  (never commit it)
3. `python smoke_test.py`  -> expect `OK  model=gemini-2.0-flash ...`
4. `python run_real.py`  -> real e2e (3 prompts: Schedule / Interaction+MCP / VisitPrep)
   -> transcript in `logs/real_run.txt` (PII redacted); prints routing/MCP/disclaimer summary
5. (optional) regenerate the demo video with real LLM frames and bump the on-screen
   test count 14 -> 15: `python make_video.py && python scripts/assemble_av.py` then re-mux.

## Security

- `.env` is gitignored and NOT committed; `git grep` for `AIza`/`AQ.`/`sk-` is clean.
- The key value is never printed in logs/terminal by the scripts (status only).
- Note: the key was pasted in a chat once — rotate it when convenient.

## Deliverables already usable (no quota needed)

- Public repo: https://github.com/MarcinRybarczyk/medmate (MIT, 15 tests).
- Demo video: `medmate_demo.mp4` (1280x720, ~2:12, H.264 + AAC voiceover, captions) —
  gitignored/local, uploadable as-is (says "14 tests"; true, now 15).
- Cover/architecture images, README with Verification section.
