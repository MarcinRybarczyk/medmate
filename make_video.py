"""make_video.py — render the medmate demo video frames + ffmpeg concat list.

Pipeline (offline, no API key, no TTS — captions burned in):
  1. read the REAL captured outputs in build/ (demo.py, MCP call, pytest)
  2. render 9 frames (1280x720) to build/frames/: title, problem, why-agents,
     architecture, 3 terminal panes (real output), build, outro
  3. write build/concat.txt (per-frame durations) for ffmpeg to assemble

Run with a Python that has Pillow:  python make_video.py
Then assemble:  ffmpeg -f concat -safe 0 -i build/concat.txt ... medmate_demo.mp4
"""
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
CAP_H = 150                      # bottom caption band height
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
FRAMES = os.path.join(BUILD, "frames")
FONTS = "C:/Windows/Fonts/"

# palette
LIGHT_BG = (245, 248, 252)
INK = (17, 24, 39)
BODY = (40, 52, 70)
BLUE = (37, 99, 235)
GREEN = (22, 163, 74)
AMBER = (217, 119, 6)
TERM_BG = (11, 18, 32)
CAP_BG = (13, 21, 38)


def font(name, size):
    return ImageFont.truetype(FONTS + name, size)


def SEG(s):  return font("segoeui.ttf", s)
def SEGB(s): return font("segoeuib.ttf", s)
def MONO(s): return font("consola.ttf", s)


_SUBS = [("—", "-"), ("–", "-"), ("’", "'"), ("‘", "'"), ("“", '"'),
         ("”", '"'), ("→", "->"), ("•", "-"), ("…", "...")]


def san(t: str) -> str:
    for a, b in _SUBS:
        t = t.replace(a, b)
    return t


def wrap(draw, text, fnt, maxw):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            if cur:
                out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def caption(img, text):
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - CAP_H, W, H], fill=CAP_BG)
    d.rectangle([0, H - CAP_H, W, H - CAP_H + 4], fill=BLUE)
    fnt = SEG(23)
    lines = wrap(d, san(text), fnt, W - 120)[:4]
    y = H - CAP_H + (CAP_H - len(lines) * 31) // 2 + 4
    for ln in lines:
        w = d.textlength(ln, font=fnt)
        d.text(((W - w) // 2, y), ln, font=fnt, fill=(225, 232, 240))
        y += 31
    return img


def slide(title, body_lines, accent=BLUE, big=False):
    img = Image.new("RGB", (W, H), LIGHT_BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=accent)
    tf = SEGB(64 if big else 46)
    tw = d.textlength(title, font=tf)
    ty = 120 if big else 64
    d.text(((W - tw) // 2, ty), title, font=tf, fill=INK)
    y = ty + (120 if big else 96)
    bf = SEG(31)
    for ln in body_lines:
        wrapped = wrap(d, san(ln), bf, W - 220)
        for wl in wrapped:
            if big:
                w = d.textlength(wl, font=bf)
                d.text(((W - w) // 2, y), wl, font=bf, fill=BODY)
            else:
                d.text((150, y), wl, font=bf, fill=BODY)
            y += 48
        y += 12
    return img


def terminal(text, title="Terminal — MedMate (offline, no API key)"):
    img = Image.new("RGB", (W, H), TERM_BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 42], fill=(30, 41, 59))
    for i, col in enumerate([(239, 68, 68), (245, 191, 7), (34, 197, 94)]):
        d.ellipse([16 + i * 22, 15, 28 + i * 22, 27], fill=col)
    d.text((92, 12), title, font=SEG(18), fill=(180, 195, 215))
    mf = MONO(20)
    y = 66
    for raw in text.splitlines():
        ln = san(raw.rstrip())
        s = ln.strip()
        col = (214, 226, 240)
        if s.startswith("$"):
            col = (126, 231, 135)
        elif s.startswith("USER:"):
            col = (147, 197, 253)
        elif s.startswith("[agent]"):
            col = (125, 211, 252)
        elif "passed" in ln:
            col = (126, 231, 135)
        elif "WARNING" in ln or s.startswith("severity") or "HIGH" in ln or "EMERGENCY" in ln:
            col = (252, 211, 77)
        elif "-> route" in ln:
            col = (190, 227, 248)
        while ln and d.textlength(ln, font=mf) > W - 80:
            ln = ln[:-2]
        d.text((40, y), ln, font=mf, fill=col)
        y += 27
        if y > H - CAP_H - 18:
            break
    return img


def architecture():
    img = Image.new("RGB", (W, H), LIGHT_BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=BLUE)
    title = "Architecture"
    tf = SEGB(40)
    d.text(((W - d.textlength(title, font=tf)) // 2, 26), title, font=tf, fill=INK)
    a = Image.open(os.path.join(HERE, "architecture.png")).convert("RGB")
    a.thumbnail((W - 120, (H - CAP_H) - 110))
    img.paste(a, ((W - a.width) // 2, 96))
    return img


def read(name):
    with open(os.path.join(BUILD, name), encoding="utf-8") as f:
        return f.read()


# ---- segment definitions (frame, duration sec, caption) -------------------
CAP = {
    "title": "MedMate - a privacy-first medication concierge agent, built on Google's ADK.",
    "problem": "People on several medications struggle to track timing, spot drug interactions, and prepare for short doctor visits. General chatbots hallucinate drug facts, drift into diagnosis, and leak personal health data.",
    "why": "MedMate splits the job across specialists, grounds drug facts in real tools instead of model memory, and enforces hard safety rules: never diagnose, never change a medication, escalate emergencies.",
    "arch": "A root ConciergeAgent routes intent to three sub-agents. The InteractionAgent reaches a local 'drug-info' MCP server over stdio. A security layer redacts PII before any model call.",
    "demo": "demo.py - offline routing preview: each request goes to the right specialist, and a described emergency is escalated to local emergency services.",
    "mcp": "Real MCP round-trip over stdio: check_interaction(warfarin, ibuprofen) returns a HIGH-severity interaction and a safety warning. Facts come from the tool, not the model.",
    "tests": "pytest - 14 tests pass: tool logic, the PII redactor, and a real MCP-protocol integration test. No API key needed.",
    "build": "The Build: Google ADK 2.3.0 + MCP 1.28.0. Multi-agent routing, grounded MCP tools, PII redaction + non-diagnostic guardrails. 14 tests passing.",
    "outro": "MedMate - privacy-first medication concierge. github.com/MarcinRybarczyk/medmate",
}


def build_frames():
    os.makedirs(FRAMES, exist_ok=True)
    segs = []

    def add(idx, img, key, dur):
        caption(img, CAP[key])
        p = os.path.join(FRAMES, f"s{idx:02d}.png")
        img.save(p)
        segs.append((f"frames/s{idx:02d}.png", dur))

    add(1, slide("MedMate", ["Privacy-First Medication Concierge", "Google ADK - multi-agent - MCP"], big=True), "title", 7)
    add(2, slide("Problem", [
        "- Many meds: hard to track WHEN to take WHAT.",
        "- Drug interactions are easy to miss.",
        "- Short doctor visits - little time to ask the right questions.",
        "- General chatbots hallucinate, diagnose, and leak health data.",
    ], accent=AMBER), "problem", 9)
    add(3, slide("Why agents", [
        "- Separation of duties: a specialist per task, tight + auditable.",
        "- Grounded tools over recall: drug facts come from an MCP tool.",
        "- Routing = intent triage, easy to extend safely.",
    ], accent=GREEN), "why", 9)
    add(4, architecture(), "arch", 10)
    add(5, terminal(read("cap_demo.txt")), "demo", 11)
    add(6, terminal(read("cap_mcp.txt")), "mcp", 11)
    add(7, terminal(read("cap_pytest.txt")), "tests", 9)
    add(8, slide("The Build", [
        "- Google ADK 2.3.0  +  MCP 1.28.0  (import-verified, pinned)",
        "- Multi-agent routing  -  grounded MCP tools  -  PII redaction",
        "- Non-diagnostic guardrails  +  emergency escalation",
        "- 14 tests passing  -  public repo  -  MIT license",
    ], accent=BLUE), "build", 9)
    add(9, slide("MedMate", ["github.com/MarcinRybarczyk/medmate", "Privacy-first medication concierge - MIT"], big=True), "outro", 7)

    # ffmpeg concat list (repeat last frame so its duration is honored)
    lines = []
    for path, dur in segs:
        lines.append(f"file '{path}'")
        lines.append(f"duration {dur}")
    lines.append(f"file '{segs[-1][0]}'")
    with open(os.path.join(BUILD, "concat.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    total = sum(d for _, d in segs)
    print(f"rendered {len(segs)} frames -> {FRAMES}")
    print(f"total duration: {total}s ({total // 60}:{total % 60:02d})")
    print(f"concat list: {os.path.join(BUILD, 'concat.txt')}")


if __name__ == "__main__":
    build_frames()
