"""Build the README project cards from the portfolio's screenshots.

Run locally after editing PROJECTS: python scripts/build_project_cards.py
Uses Windows fonts, so the cards are committed rather than built in CI.
"""

import io
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SHOTS = "https://lakshyasachdevaportfolio.vercel.app/shots/{}.webp"
OUTPUT = Path(__file__).resolve().parent.parent / "assets" / "projects"
FONTS = Path("C:/Windows/Fonts")
SS = 2

# shot, name, kicker, tagline, stack, background, accent A, accent B
PROJECTS = [
    ("cortexorbit", "CortexOrbit", "FLAGSHIP", "A living sky of everything you learn.",
     ["React 19", "TypeScript", "Three.js", "SQLite"], "#0b0712", "#ffb547", "#ff6a1a"),
    ("datavault", "DataVault", "FLAGSHIP", "A credential vault with a real SQL console.",
     ["Node.js", "Express", "MySQL 8", "Docker"], "#020a12", "#7df9ff", "#1f6bff"),
    ("onyx-os", "Onyx OS", "FLAGSHIP", "Your progress, set in stone.",
     ["Next.js 16", "R3F", "GSAP", "Tailwind 4"], "#0d0806", "#f3eadb", "#b0442c"),
    ("lakshyagram", "LakshyaGram", "REAL-TIME MESSENGER", "A real-time messenger, with an AI one message away.",
     ["Vanilla JS", "Firebase", "Three.js", "Gemini"], "#030716", "#2f7bff", "#ffd23f"),
    ("atmos", "ATMOS", "ON-DEVICE AI", "Face authentication that works with no signal.",
     ["React Native", "TypeScript", "TFLite", "MMKV"], "#010d0a", "#5dff9e", "#00b3ff"),
    ("unigrant", "UniGrant", "DATABASE SYSTEMS", "A research grant, from proposal to final report.",
     ["MySQL", "Express", "React", "SQL triggers"], "#09041a", "#c38bff", "#5a2dff"),
    ("saul-goodman", "Saul Goodman Courtroom", "COURSE PROJECT", "Two AI lawyers. One rulebook judge.",
     ["Python", "FastAPI", "Pydantic", "Vanilla JS"], "#120405", "#ff4f4f", "#ffd23f"),
    ("antarbodh", "AntarBodh", "SMART INDIA HACKATHON", "The ocean beneath the surface, read from satellites.",
     ["Deep learning", "CNN", "GLORYS", "ARGO"], "#021626", "#5ff6ff", "#0b5cab"),
]
WORK = [
    ("adaptnxt", "AdaptNXT", "AI INTERN", "Search video in plain language.", "#120a04", "#ff8a2a", "#ff4f1a"),
    ("sibidelve", "SibiDelve AI", "AI ENGINEER", "An AI workspace for manufacturing engineers.", "#0d0b09", "#f3eadb", "#a08a6a"),
    ("vidyarthe", "VidyarthE", "TECH LEAD (ENACTUS BPHC)", "Hands-on STEM for under-resourced schools.", "#060818", "#7d8bff", "#3f4bff"),
]


def rgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size * SS)


def fetch(shot):
    request = urllib.request.Request(SHOTS.format(shot), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return Image.open(io.BytesIO(response.read())).convert("RGB")


def cover(image, width, height):
    """Scale to fill, cropping from the top so headlines survive."""
    ratio = max(width / image.width, height / image.height)
    resized = image.resize((round(image.width * ratio), round(image.height * ratio)), Image.Resampling.LANCZOS)
    left = (resized.width - width) // 2
    return resized.crop((left, 0, left + width, height))


def gradient(width, height, start, end):
    ramp = Image.linear_gradient("L").rotate(90).resize((width, height))
    return Image.composite(Image.new("RGB", (width, height), end), Image.new("RGB", (width, height), start), ramp)


def wrap(draw, text, face, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=face) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def card(shot, name, kicker, tagline, stack, background, accent_a, accent_b, width, height, shot_height, sizes):
    w, h = width * SS, height * SS
    pad = sizes["pad"] * SS
    bg, a, b = rgb(background), rgb(accent_a), rgb(accent_b)
    canvas = Image.new("RGB", (w, h), bg)

    # Soft accent glow rising from the bottom corner.
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse([w * 0.45, h * 0.62, w * 1.25, h * 1.4], fill=64)
    glow = glow.filter(ImageFilter.GaussianBlur(70 * SS))
    canvas.paste(Image.new("RGB", (w, h), b), mask=glow)

    # Screenshot fading into the card.
    fade = Image.new("L", (1, shot_height * SS), 255)
    for y in range(shot_height * SS):
        t = min(1, max(0, (y / (shot_height * SS) - 0.5) / 0.38))
        fade.putpixel((0, y), round(255 * (1 - t) ** 1.6))
    canvas.paste(cover(fetch(shot), w, shot_height * SS), mask=fade.resize((w, shot_height * SS)))

    draw = ImageDraw.Draw(canvas)
    y = (shot_height - sizes["lift"]) * SS
    draw.text((pad, y), kicker, font=font("consolab.ttf", sizes["kicker"]), fill=a)
    y += round(sizes["kicker"] * 1.5) * SS
    draw.text((pad, y), name, font=font("seguibl.ttf", sizes["name"]), fill=(255, 255, 255))
    y += round(sizes["name"] * 1.34) * SS
    face = font("segoeui.ttf", sizes["tagline"])
    for line in wrap(draw, tagline, face, w - pad * 2):
        draw.text((pad, y), line, font=face, fill=(205, 212, 222))
        y += round(sizes["tagline"] * 1.3) * SS

    if stack:
        y = h - (sizes["chip"] + 40) * SS
        x = pad
        face = font("consola.ttf", sizes["chip"])
        for item in stack:
            label = draw.textlength(item, font=face)
            box = [x, y, x + label + 30 * SS, y + (sizes["chip"] + 18) * SS]
            draw.rounded_rectangle(box, radius=10 * SS, outline=a, width=SS)
            draw.text((x + 15 * SS, y + 8 * SS), item, font=face, fill=a)
            x = box[2] + 12 * SS

    # Gradient border and rounded corners.
    radius = 28 * SS
    border = 3 * SS
    ring = Image.new("L", (w, h), 0)
    ring_draw = ImageDraw.Draw(ring)
    ring_draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    ring_draw.rounded_rectangle([border, border, w - 1 - border, h - 1 - border], radius=radius - border, fill=0)
    canvas.paste(gradient(w, h, a, b), mask=ring)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    canvas.putalpha(mask)
    return canvas.resize((width, height), Image.Resampling.LANCZOS)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    project = {"pad": 36, "lift": 34, "kicker": 22, "name": 46, "tagline": 29, "chip": 21}
    for shot, name, kicker, tagline, stack, background, a, b in PROJECTS:
        image = card(shot, name, kicker, tagline, stack, background, a, b, 880, 545, 330, project)
        image.save(OUTPUT / f"{shot}.webp", quality=86, method=6)

    compact = {"pad": 40, "lift": 40, "kicker": 32, "name": 66, "tagline": 40, "chip": 0}
    for shot, name, kicker, tagline, background, a, b in WORK:
        image = card(shot, name, kicker, tagline, [], background, a, b, 880, 760, 400, compact)
        image.save(OUTPUT / f"{shot}.webp", quality=86, method=6)


if __name__ == "__main__":
    main()
