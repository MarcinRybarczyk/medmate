"""gen_tts.py — generate the English voiceover with edge-tts (free, no API key).

Writes build/audio/seg1.mp3 .. seg5.mp3 using a natural en-US neural voice at a
calm rate. edge-tts uses Microsoft's online Edge TTS endpoint (needs network),
no key required.

NOTE (truth): the narration draft said "nine passing" tests; the suite actually
has 14 (9 unit + 5 integration) and the on-screen pytest frame shows "14 passed".
Narrating a different number than the screen would be inconsistent/false, so the
two mentions were changed to "fourteen".

Run:  python scripts/gen_tts.py
"""
import asyncio
import os

import edge_tts

VOICE = "en-US-AndrewNeural"   # fallback: en-US-AriaNeural / en-US-GuyNeural
RATE = "-5%"                    # calm pacing

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "build", "audio")

SEGMENTS = {
    "seg1": (
        "Millions of people take several medications every day. They must remember when "
        "to take each one, whether two drugs are safe together, and what to ask their doctor. "
        "The cognitive load is real, and mistakes are dangerous, especially for caregivers and "
        "older adults. MedMate is a privacy-first medication concierge that lifts this load "
        "without ever putting health data at risk."
    ),
    "seg2": (
        "Why agents, and not a single prompt? Because these are different tasks with different "
        "failure modes. A single prompt is brittle. MedMate uses a root concierge agent that "
        "detects intent and routes it to a focused specialist. Crucially, the interaction checker "
        "doesn't trust the model's memory. It calls a real tool, so its answers are grounded and "
        "checkable."
    ),
    "seg3": (
        "Here's the architecture. The MedMate concierge, an ADK agent, routes to three sub-agents: "
        "ScheduleAgent builds a daily reminder plan, InteractionAgent checks drug pairs, and "
        "VisitPrepAgent prepares questions for the doctor. Underneath is a local drug-info MCP "
        "server, exposing read-only tools over standard input and output, so personal data never "
        "leaves the machine. A security layer redacts personal information, blocks any diagnosis, "
        "and escalates real emergencies."
    ),
    "seg4": (
        "Let's see it work. First, MedMate turns a medication list into a clear daily schedule. "
        "Next, I ask whether two drugs are safe together. The InteractionAgent calls the MCP tool, "
        "returns a grounded warning, and always reminds me to confirm with a pharmacist. It never "
        "diagnoses and never tells me to start or stop a drug. Finally, it prepares a short "
        "checklist for my appointment. And here are the tests, fourteen passing."
    ),
    "seg5": (
        "MedMate is built on Google's Agent Development Kit, version two-point-three, with an MCP "
        "server, fourteen passing tests, and a public, documented repository. The boldest design "
        "choice was the safety line: MedMate deliberately refuses to diagnose or change "
        "prescriptions. The full code and setup are in the repo. Thanks for watching."
    ),
}


async def main():
    os.makedirs(OUT, exist_ok=True)
    for name, text in SEGMENTS.items():
        path = os.path.join(OUT, f"{name}.mp3")
        await edge_tts.Communicate(text, voice=VOICE, rate=RATE).save(path)
        print(f"wrote {path}  ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
