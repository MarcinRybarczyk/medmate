"""
make_cover.py — render MedMate's diagram-style artwork with Pillow.

Outputs (run: `python make_cover.py`):
  - cover.png        560x280  : Kaggle writeup thumbnail
  - architecture.png 1280x720 : larger arch image for the video / gallery

One scalable renderer draws both: title + subtitle, a "Security layer" band,
the MedMate ConciergeAgent routing to three sub-agents, and all of them backed
by the drug-info MCP server. Everything is positioned as a fraction of the
canvas and scaled by S = width / 560, so the small and large images stay
visually identical and readable at thumbnail size.
"""

from PIL import Image, ImageDraw, ImageFont

# ---- palette ---------------------------------------------------------------
BG = (247, 249, 252)
INK = (17, 24, 39)
MUTED = (71, 85, 105)
ARROW = (100, 116, 139)
CONCIERGE = ((219, 234, 254), (37, 99, 235))      # (fill, border) blue
SUBAGENT = ((224, 242, 254), (59, 130, 246))       # light blue
MCP = ((220, 252, 231), (22, 163, 74))             # green
SECURITY = ((254, 243, 199), (217, 119, 6), (146, 64, 14))  # fill, border, text


def _font(size, bold=False):
    """Load a readable TrueType font, falling back to Pillow's default."""
    candidates = (
        ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
        if bold
        else ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _center_text(d, cx, cy, text, font, fill):
    """Draw `text` centered on (cx, cy)."""
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    d.text((cx - (r - l) / 2, cy - (b - t) / 2), text, font=font, fill=fill)


def _box(d, x, y, w, h, fill, border, radius, lw):
    d.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill, outline=border, width=lw)


def _arrow(d, x1, y1, x2, y2, width, head):
    """A simple vertical-ish arrow from (x1,y1) to (x2,y2)."""
    d.line([x1, y1, x2, y2], fill=ARROW, width=width)
    # arrowhead (pointing down toward the target)
    d.polygon(
        [(x2 - head, y2 - head), (x2 + head, y2 - head), (x2, y2)],
        fill=ARROW,
    )


def render(width, height, path):
    S = width / 560.0  # scale factor (1.0 at thumbnail, ~2.29 at 1280)
    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)

    f_title = _font(int(34 * S), bold=True)
    f_sub = _font(int(15 * S), bold=False)
    f_box = _font(int(12 * S), bold=True)
    f_small = _font(int(9 * S), bold=False)
    lw = max(1, int(2 * S))
    rad = int(8 * S)

    # --- title + subtitle (top band) ---
    _center_text(d, width / 2, 26 * S, "MedMate", f_title, INK)
    _center_text(d, width / 2, 52 * S, "Privacy-First Medication Concierge", f_sub, MUTED)

    # --- security layer band ---
    sb_x, sb_y, sb_w, sb_h = 18 * S, 70 * S, width - 36 * S, 22 * S
    _box(d, sb_x, sb_y, sb_w, sb_h, SECURITY[0], SECURITY[1], rad, lw)
    _center_text(
        d, width / 2, sb_y + sb_h / 2,
        "Security layer  -  PII redaction  -  non-diagnostic guardrails  -  emergency escalation",
        f_small, SECURITY[2],
    )

    # --- concierge box (centered) ---
    cw, ch = 188 * S, 30 * S
    cx, cy = (width - cw) / 2, 104 * S
    _box(d, cx, cy, cw, ch, CONCIERGE[0], CONCIERGE[1], rad, lw)
    _center_text(d, width / 2, cy + ch / 2, "MedMate (ConciergeAgent)", f_box, INK)

    # --- three sub-agent boxes ---
    labels = ["ScheduleAgent", "InteractionAgent", "VisitPrepAgent"]
    bw, bh = 150 * S, 30 * S
    gap = (width - 36 * S - 3 * bw) / 2
    row_y = 162 * S
    centers = []
    x = 18 * S
    for lab in labels:
        _box(d, x, row_y, bw, bh, SUBAGENT[0], SUBAGENT[1], rad, lw)
        _center_text(d, x + bw / 2, row_y + bh / 2, lab, f_box, INK)
        centers.append(x + bw / 2)
        x += bw + gap

    # arrows: concierge -> each sub-agent
    for c in centers:
        _arrow(d, width / 2, cy + ch, c, row_y - 2 * S, lw, int(4 * S))

    # --- MCP server box (bottom, centered) ---
    mw, mh = 230 * S, 32 * S
    mx, my = (width - mw) / 2, 224 * S
    _box(d, mx, my, mw, mh, MCP[0], MCP[1], rad, lw)
    _center_text(d, width / 2, my + mh / 2 - 6 * S, "drug-info MCP server", f_box, INK)
    _center_text(
        d, width / 2, my + mh / 2 + 7 * S,
        "check_interaction()  -  drug_summary()  (local stdio)", f_small, MUTED,
    )

    # arrows: each sub-agent -> MCP server (InteractionAgent is the live caller)
    for c in centers:
        _arrow(d, c, row_y + bh, width / 2, my - 2 * S, lw, int(4 * S))

    img.save(path)
    print(f"wrote {path} ({width}x{height})")


if __name__ == "__main__":
    render(560, 280, "cover.png")
    render(1280, 720, "architecture.png")
