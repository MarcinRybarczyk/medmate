"""assemble_av.py — time the video frames to the voiceover + write concat list + .srt.

Reads the 5 narration mp3 durations (ffprobe), maps the 5 narration segments onto
the 9 rendered frames, gives each frame group a duration equal to its narration
length + 0.5 s of buffer, and writes:
  - build/concat.txt          (ffmpeg image concat with per-frame durations)
  - medmate_demo.srt          (subtitles, same text as the voiceover)

The audio side (voiceover.mp3 = each segment + 0.5 s trailing silence, concatenated)
is built by ffmpeg in the shell so the two stay aligned to the same group lengths.

Run:  python scripts/assemble_av.py
"""
import os
import subprocess

from gen_tts import SEGMENTS  # same texts as the voiceover (single source)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "build")
GAP = 0.5  # buffer after each narration segment

# narration order -> the frames it plays over, with a fixed split where a segment
# spans several frames (title+problem; the 3 terminal panes; build+outro).
SEG_ORDER = ["seg1", "seg2", "seg3", "seg4", "seg5"]


def dur(mp3):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", mp3], text=True
    )
    return float(out.strip())


def split(group_total, parts):
    """Distribute group_total over fixed parts; last part absorbs the remainder."""
    used = sum(p[1] for p in parts[:-1])
    out = [(p[0], p[1]) for p in parts[:-1]]
    out.append((parts[-1][0], round(group_total - used, 3)))
    return out


def srt_ts(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60); ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    d = {k: dur(os.path.join(BUILD, "audio", f"{k}.mp3")) for k in SEG_ORDER}
    g = {k: d[k] + GAP for k in SEG_ORDER}  # group (visual) duration per segment

    # frame layout per group (frame file -> seconds; last frame of a group absorbs remainder)
    groups = [
        split(g["seg1"], [("frames/s01.png", 5.0), ("frames/s02.png", 0)]),
        split(g["seg2"], [("frames/s03.png", 0)]),
        split(g["seg3"], [("frames/s04.png", 0)]),
        split(g["seg4"], [("frames/s05.png", 9.0), ("frames/s06.png", 12.0), ("frames/s07.png", 0)]),
        split(g["seg5"], [("frames/s08.png", 0), ("frames/s09.png", 7.0)]),  # build absorbs, outro 7s
    ]
    # fix group5 so outro is the remainder instead (build first absorbs): recompute explicitly
    groups[4] = split(g["seg5"], [("frames/s08.png", g["seg5"] - 7.0), ("frames/s09.png", 7.0)])

    frames = [f for grp in groups for f in grp]

    # concat.txt (repeat last frame so its duration is honored by the demuxer)
    lines = []
    for path, sec in frames:
        lines.append(f"file '{path}'")
        lines.append(f"duration {sec}")
    lines.append(f"file '{frames[-1][0]}'")
    with open(os.path.join(BUILD, "concat.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # .srt — one cue per narration segment, spanning its speech (not the 0.5s gap)
    srt = []
    t = 0.0
    for i, k in enumerate(SEG_ORDER, 1):
        start, end = t, t + d[k]
        srt.append(f"{i}\n{srt_ts(start)} --> {srt_ts(end)}\n{SEGMENTS[k]}\n")
        t += g[k]
    with open(os.path.join(ROOT, "medmate_demo.srt"), "w", encoding="utf-8") as f:
        f.write("\n".join(srt))

    total = sum(g.values())
    print("frame durations:")
    for path, sec in frames:
        print(f"  {path}: {sec}s")
    print(f"TOTAL: {total:.2f}s  ({int(total)//60}:{int(total)%60:02d})  -> limit 300s OK: {total <= 300}")
    print(f"wrote {os.path.join(BUILD, 'concat.txt')} + medmate_demo.srt")


if __name__ == "__main__":
    main()
