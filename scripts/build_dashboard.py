"""Build the animated lakshya.exe dashboard from scripts/dashboard_source.svg.

Edit the text in the source file, then run: python scripts/build_dashboard.py

Everything loops, so there is always motion on screen whenever someone scrolls
to it. Animations use SMIL, which runs inside an <img>. Every element's plain
attributes hold its finished state, so a viewer without animation support
still sees the complete dashboard.
"""

import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(__file__).resolve().parent / "dashboard_source.svg"
TARGETS = ("profile_dark.svg", "profile_light.svg")

W, H = 1180, 530
CYCLE = 30.0  # boot, run, power off
ART_END = 1.5
LINE_START, LINE_GAP, LINE_DUR = 0.5, 0.13, 0.26
LINE_W = 640
CHAR = 8.25
PROMPT = "lakshya@binary:~$ "
COMMANDS = [
    "./cortexorbit --launch",
    "./onyx-os --sync",
    "./datavault --unlock",
    "./atmos --offline",
    "./unigrant --audit",
    "./lakshyagram --send",
]
BURSTS = [8.0, 8.4, 14.5, 20.0, 20.3, 26.0]


def key(value):
    return f"{value:.5f}".rstrip("0").rstrip(".") or "0"


def timeline(attribute, points, discrete=False, tag="animate"):
    """Loop an attribute through (seconds, value) points across the cycle."""
    times = ";".join(key(t / CYCLE) for t, _ in points)
    values = ";".join(str(v) for _, v in points)
    mode = ' calcMode="discrete"' if discrete else ""
    return (
        f'<{tag} attributeName="{attribute}" values="{values}" keyTimes="{times}"{mode} '
        f'dur="{CYCLE:g}s" repeatCount="indefinite"/>'
    )


def pulses(moments, length, on="1", off="0"):
    points = [(0.0, off)]
    for start in moments:
        points += [(start, on), (start + length, off)]
    return points


def holo_defs():
    stops = [(0, "#7DF9FF"), (0.38, "#5EEAD4"), (0.46, "#b48bff"), (0.5, "#ffffff"), (0.54, "#FF5F87"), (0.62, "#7DF9FF"), (1, "#7DF9FF")]
    body = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return (
        '<linearGradient id="holo" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="160" y2="320" spreadMethod="repeat">'
        '<animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="160 320" dur="5s" repeatCount="indefinite"/>'
        f"{body}</linearGradient>"
        '<linearGradient id="meter" gradientUnits="userSpaceOnUse" x1="0" y1="515" x2="0" y2="470">'
        '<stop offset="0" stop-color="#5EEAD4"/><stop offset="1" stop-color="#FF5F87"/></linearGradient>'
        '<linearGradient id="sweep" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7DF9FF" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#7DF9FF" stop-opacity=".09"/></linearGradient>'
        '<pattern id="crt" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" opacity=".12"/></pattern>'
    )


def rain(rng):
    """Binary columns behind the specs. Each string repeats, so the loop is seamless."""
    length = 64
    pitch = 10
    defs, columns = [], []
    for i in range(3):
        half = "".join(rng.choice("01") for _ in range(length))
        defs.append(
            f'<text id="rain{i}" transform="rotate(90)" font-size="13" textLength="{length * pitch * 2}" '
            f'lengthAdjust="spacing" fill="#00ff9c">{half * 2}</text>'
        )
    for x in range(525, W - 10, 28):
        speed = rng.uniform(9, 22)
        opacity = rng.uniform(0.1, 0.24)
        start = rng.uniform(0, length * pitch)
        columns.append(
            f'<g transform="translate({x} 0)" opacity="{opacity:.2f}"><use href="#rain{rng.randrange(3)}" y="0">'
            f'<animateTransform attributeName="transform" type="translate" from="0 {-length * pitch - start:.0f}" '
            f'to="0 {-start:.0f}" dur="{speed:.1f}s" repeatCount="indefinite"/></use></g>'
        )
    return "".join(defs), "".join(columns)


def glitch(rng):
    """Slices of the portrait that jump sideways during each burst."""
    moments = [start + i * 0.09 for start in BURSTS for i in range(4)]
    defs, bands = [], []
    for i in range(8):
        top = rng.randrange(0, H - 70)
        height = rng.randrange(12, 62)
        defs.append(f'<clipPath id="slice{i}"><rect x="0" y="{top}" width="530" height="{height}"/></clipPath>')
        hits = [m for m in moments if rng.random() < 0.6]
        shifts = [(0.0, "0 0")]
        for moment in hits:
            shifts.append((moment, f"{rng.randrange(-46, 46)} 0"))
        bands.append(
            f'<g clip-path="url(#slice{i})" opacity="0">{timeline("opacity", pulses(hits, 0.07), True)}'
            f'<rect y="{top}" width="530" height="{height}" fill="#000"/>'
            f'<g>{timeline("transform", shifts, True, "animateTransform").replace(" attributeName", " type=\"translate\" attributeName", 1)}'
            f'<use href="#portrait" fill="#FF5F87"/></g></g>'
        )
    split = (
        f'<g opacity="0">{timeline("opacity", pulses(moments, 0.07, ".55"), True)}'
        '<use href="#portrait" x="-5" fill="#ff2d6f"/><use href="#portrait" x="5" fill="#00e5ff"/></g>'
    )
    return "".join(defs), split + "".join(bands)


def prompt_block(y):
    """The prompt keeps launching real projects, then idles on a blinking cursor."""
    defs, rows = [], []
    start = LINE_START + 20 * LINE_GAP + 0.3
    slot = (CYCLE - 2.0 - start) / len(COMMANDS)
    prefix = len(PROMPT) * CHAR  # the text itself is aligned by the hidden prompt below
    rows.append(
        f'<text x="540" y="{y}"><tspan class="title">lakshya@binary</tspan><tspan class="value">:~$ </tspan></text>'
    )
    for i, command in enumerate(COMMANDS):
        begin = start + i * slot
        typed = begin + len(command) * 0.05
        end = begin + slot - 0.05
        width = (len(command) + 2) * 9.2
        defs.append(
            f'<clipPath id="cmd{i}"><rect x="{540 + prefix:.0f}" y="{y - 18}" height="26" '
            f'width="{width if i == len(COMMANDS) - 1 else 0:.0f}">'
            + timeline("width", [(0, 0), (begin, 0), (typed, f"{width:.0f}"), (end, f"{width:.0f}"), (end, 0), (CYCLE, 0)])
            + "</rect></clipPath>"
        )
        rows.append(
            f'<g clip-path="url(#cmd{i})"><text x="540" y="{y}"><tspan class="title" fill-opacity="0">lakshya@binary</tspan><tspan fill-opacity="0">:~$ </tspan>'
            f'<tspan class="value">{command} </tspan><tspan class="ascii">█'
            '<animate attributeName="fill-opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.06s" repeatCount="indefinite"/>'
            "</tspan></text></g>"
        )
    return "".join(defs), "".join(rows)


def meter(rng, top):
    bars = []
    for i in range(46):
        x = 540 + i * 13
        base = 512
        levels = [rng.randrange(4, 42) for _ in range(6)]
        levels.append(levels[0])
        heights = ";".join(str(v) for v in levels)
        tops = ";".join(str(base - v) for v in levels)
        duration = rng.uniform(1.3, 2.6)
        bars.append(
            f'<rect x="{x}" y="{base - levels[0]}" width="8" height="{levels[0]}" rx="1" fill="url(#meter)">'
            f'<animate attributeName="height" values="{heights}" dur="{duration:.2f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="{tops}" dur="{duration:.2f}s" repeatCount="indefinite"/></rect>'
        )
    return f'<g opacity=".85">{"".join(bars)}</g>'


def build():
    rng = random.Random(3012)
    source = SOURCE.read_text(encoding="utf8")
    style = source[source.index("<svg"):source.index("</style>") + len("</style>")]
    art = re.search(r'<text x="0" y="0" class="ascii">(.*?)</text>', source, re.S).group(1)
    # Consolas has no braille, so browsers fall back per glyph and rows end up
    # different widths. Pinning every row to one length keeps the edges straight.
    art = "".join(
        f'<text x="0" y="{y}" textLength="780" lengthAdjust="spacingAndGlyphs">{row}</text>'
        for y, row in re.findall(r'<tspan x="0" y="(\d+)">(.*?)</tspan>', art)
    )
    lines = re.findall(r'^\s*(<tspan x="540" y="(\d+)".*)$', source, re.M)
    prompt_y = int(lines[-1][1]) + 36

    clips, rows = [], []
    for i, (markup, y) in enumerate(lines):
        y = int(y)
        begin = LINE_START + i * LINE_GAP
        clips.append(
            f'<clipPath id="line{i}"><rect x="536" y="{y - 16}" height="22" width="{LINE_W}">'
            + timeline("width", [(0, 0), (begin, 0), (begin + LINE_DUR, LINE_W), (CYCLE, LINE_W)])
            + "</rect></clipPath>"
        )
        rows.append(f'<g clip-path="url(#line{i})"><text>{markup.strip()}</text></g>')

    rain_defs, rain_columns = rain(rng)
    glitch_defs, glitch_layer = glitch(rng)
    prompt_defs, prompt_rows = prompt_block(prompt_y)

    art_clip = (
        f'<clipPath id="art"><rect width="530" height="{H}">'
        + timeline("height", [(0, 0), (ART_END, H), (CYCLE, H)])
        + "</rect></clipPath>"
    )
    screen_clip = (
        f'<clipPath id="screen"><rect width="{W}" height="{H}">'
        + timeline("y", [(0, 0), (CYCLE - 0.45, 0), (CYCLE - 0.15, H / 2 - 1), (CYCLE, H / 2 - 1)])
        + timeline("height", [(0, H), (CYCLE - 0.45, H), (CYCLE - 0.15, 2), (CYCLE, 2)])
        + "</rect></clipPath>"
    )
    scan_line = (
        '<rect x="10" width="510" height="2" fill="#7DF9FF" opacity="0">'
        + timeline("y", [(0, 0), (ART_END, H), (CYCLE, H)])
        + timeline("opacity", [(0, 1), (ART_END - 0.05, 1), (ART_END, 0), (CYCLE, 0)])
        + "</rect>"
    )
    portrait = (
        f'<g id="portrait" transform="translate(22, 20) scale(0.48, 1.25)">{art}</g>'
    )
    sweep = (
        f'<rect width="{W}" height="110" y="-110" fill="url(#sweep)">'
        f'<animate attributeName="y" values="-110;{H}" dur="6.5s" repeatCount="indefinite"/></rect>'
    )
    border = (
        f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="15" fill="none" stroke="#123039" stroke-width="2"/>'
        + "".join(
            f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="15" fill="none" stroke="{colour}" '
            f'stroke-width="2.5" stroke-linecap="round" pathLength="1000" stroke-dasharray="110 390" stroke-dashoffset="{offset}">'
            f'<animate attributeName="stroke-dashoffset" from="{offset}" to="{offset - 500}" dur="3.5s" repeatCount="indefinite"/></rect>'
            for colour, offset in (("#7DF9FF", 0), ("#FF5F87", -250))
        )
    )

    return (
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        + style
        + f'\n<title>lakshya.exe</title>\n<defs>{holo_defs()}{portrait}{rain_defs}{art_clip}{screen_clip}'
        + "".join(clips)
        + prompt_defs
        + glitch_defs
        + f'</defs>\n<rect width="{W}" height="{H}" fill="#000000" rx="15"/>\n'
        + f"<!-- Binary rain -->\n{rain_columns}\n"
        + '<g clip-path="url(#screen)">\n'
        + f'<g clip-path="url(#art)"><use href="#portrait" fill="url(#holo)"/>{glitch_layer}</g>\n{scan_line}\n'
        + "<!-- Specs -->\n"
        + "\n".join(rows)
        + f"\n{prompt_rows}\n{meter(rng, prompt_y)}\n</g>\n"
        + f'<rect width="{W}" height="{H}" rx="15" fill="url(#crt)"/>\n{sweep}\n{border}\n</svg>\n'
    )


def main():
    output = build()
    for name in TARGETS:
        (ROOT / name).write_text(output, encoding="utf8", newline="\n")
    print(f"{TARGETS}: {len(output.encode()) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
