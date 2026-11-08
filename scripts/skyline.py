"""Render a year of GitHub contributions as a rotating isometric ring city.

Weeks run around the ring, weekdays are the rows from the inside out, and tower
height follows the day's contribution count.

    GH_TOKEN=... python scripts/skyline.py USERNAME -o dist/skyline.webp
    python scripts/skyline.py --input days.json -o skyline.webp

--input takes a JSON list of {"date": "YYYY-MM-DD", "count": N}.
"""

import argparse
import datetime as dt
import json
import math
import os
import random
import urllib.request
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 860, 520
SS = 2  # supersampling factor
FRAMES = 150
FRAME_MS = 40
QUALITY = 72
SCALE = 23.0
CX, CY = WIDTH / 2, 312
ELEVATION = math.radians(30)
SIN_E, COS_E = math.sin(ELEVATION), math.cos(ELEVATION)

R_INNER = 8.6
ROW = 1.0
GAP = 0.09
MAX_TOWER = 3.8
BASE_SLAB = 0.1
LIGHT = (-0.55, 0.83)

BACKGROUND = (13, 17, 23)
GROUND = (20, 27, 36)
RIM = (48, 62, 78)
TEXT = (201, 209, 217)
MUTED = (125, 136, 148)
ACCENT = (57, 211, 83)
BEACON = (125, 249, 255)
# Same greens as the GitHub contribution graph, so it matches the shooter.
LEVELS = [(14, 68, 41), (0, 109, 50), (38, 166, 65), (57, 211, 83)]
EMPTY = (30, 40, 52)

QUERY = """query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""


def fetch_days(username, token):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": username}}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise SystemExit(f"GitHub API error: {payload['errors']}")
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [
        {"date": day["date"], "count": day["contributionCount"]}
        for week in weeks
        for day in week["contributionDays"]
    ]


def stats(days):
    days = sorted(days, key=lambda d: d["date"])
    longest = run = 0
    for day in days:
        run = run + 1 if day["count"] else 0
        longest = max(longest, run)
    return {
        "total": sum(d["count"] for d in days),
        "best": max(d["count"] for d in days),
        "streak": longest,
        "active": sum(1 for d in days if d["count"]),
    }


def build_city(days):
    """Turn days into polar footprints and work out the look of each tower."""
    days = sorted(days, key=lambda d: d["date"])
    first = dt.date.fromisoformat(days[0]["date"])
    origin = first - dt.timedelta(days=(first.weekday() + 1) % 7)  # back to Sunday
    placed = []
    for day in days:
        date = dt.date.fromisoformat(day["date"])
        offset = (date - origin).days
        placed.append((offset // 7, offset % 7, date, day["count"]))
    weeks = max(p[0] for p in placed) + 1
    step = math.tau / weeks

    counts = sorted(c for *_, c in placed if c)
    cap = counts[int(len(counts) * 0.97)] if counts else 1
    quartiles = [counts[len(counts) * q // 4] for q in (1, 2, 3)] if counts else [1, 1, 1]

    towers = []
    for index, (week, weekday, date, count) in enumerate(placed):
        a0 = week * step + step * GAP / 2
        a1 = (week + 1) * step - step * GAP / 2
        r0 = R_INNER + weekday * ROW + GAP / 2
        r1 = R_INNER + (weekday + 1) * ROW - GAP / 2
        footprint = [
            (r0 * math.cos(a0), r0 * math.sin(a0)),
            (r1 * math.cos(a0), r1 * math.sin(a0)),
            (r1 * math.cos(a1), r1 * math.sin(a1)),
            (r0 * math.cos(a1), r0 * math.sin(a1)),
        ]
        if count:
            height = BASE_SLAB + MAX_TOWER * min(count / max(cap, 1), 1) ** 0.65
            level = sum(count > q for q in quartiles)
            colour = LEVELS[level]
        else:
            height, colour = BASE_SLAB * 0.6, EMPTY
        seed = random.Random(index)
        towers.append(
            {
                "footprint": footprint,
                "centre": (sum(p[0] for p in footprint) / 4, sum(p[1] for p in footprint) / 4),
                "height": height,
                "colour": colour,
                "peak": count >= cap and count > 0,
                "windows": [seed.random() < 0.55 for _ in range(64)],
            }
        )

    labels = []
    seen = set()
    for week, _, date, _ in sorted(placed, key=lambda p: p[0]):
        key = (date.year, date.month)
        if key in seen or date.day > 7:
            continue
        seen.add(key)
        labels.append((date.strftime("%b").upper(), (week + 0.5) * step))
    if len(labels) > 1 and labels[0][0] == labels[-1][0]:
        labels.pop()  # the same month at both ends of the year would collide
    return towers, labels


def project(x, y, z, cos_t, sin_t):
    rx = x * cos_t - y * sin_t
    ry = x * sin_t + y * cos_t
    return (
        (CX + SCALE * rx) * SS,
        (CY + SCALE * (ry * SIN_E - z * COS_E)) * SS,
    ), ry


def shade(colour, amount):
    return tuple(min(255, int(c * amount)) for c in colour)


def lerp(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def draw_windows(draw, base_a, base_b, top_a, top_b, tower, tower_face, brightness):
    rows = int(tower["height"] / 0.42)
    columns = 3
    if rows < 2:
        return
    for row in range(rows):
        v0 = (row + 0.3) / rows
        v1 = (row + 0.72) / rows
        for column in range(columns):
            if not tower["windows"][(row * columns + column + tower_face * 7) % 64]:
                continue
            u0 = (column + 0.22) / columns
            u1 = (column + 0.78) / columns
            quad = [
                lerp(lerp(base_a, base_b, u0), lerp(top_a, top_b, u0), v0),
                lerp(lerp(base_a, base_b, u1), lerp(top_a, top_b, u1), v0),
                lerp(lerp(base_a, base_b, u1), lerp(top_a, top_b, u1), v1),
                lerp(lerp(base_a, base_b, u0), lerp(top_a, top_b, u0), v1),
            ]
            draw.polygon(quad, fill=shade((255, 214, 120), 0.45 + 0.55 * brightness))


def draw_tower(draw, tower, cos_t, sin_t):
    base, top = [], []
    for x, y in tower["footprint"]:
        base.append(project(x, y, 0, cos_t, sin_t)[0])
        top.append(project(x, y, tower["height"], cos_t, sin_t)[0])

    for face in range(4):
        (x0, y0), (x1, y1) = tower["footprint"][face], tower["footprint"][(face + 1) % 4]
        # The footprint winds counter-clockwise, so (dy, -dx) points outward.
        nx, ny = y1 - y0, x0 - x1
        length = math.hypot(nx, ny) or 1
        nx, ny = nx / length, ny / length
        view_x, view_y = nx * cos_t - ny * sin_t, nx * sin_t + ny * cos_t
        if view_y <= 0:
            continue
        lit = max(0.0, view_x * LIGHT[0] + view_y * LIGHT[1])
        j = (face + 1) % 4
        draw.polygon(
            [base[face], base[j], top[j], top[face]],
            fill=shade(tower["colour"], 0.34 + 0.5 * lit),
        )
        draw_windows(draw, base[face], base[j], top[face], top[j], tower, face, lit)

    draw.polygon(top, fill=shade(tower["colour"], 1.25) if tower["height"] > 0.3 else tower["colour"])
    if tower["peak"]:
        draw.polygon(top, fill=BEACON)


def ellipse_box(radius, z=0):
    x = CX * SS
    y = (CY - z * SCALE * COS_E) * SS
    rx, ry = radius * SCALE * SS, radius * SCALE * SIN_E * SS
    return [x - rx, y - ry, x + rx, y + ry]


def draw_core(draw, font, total):
    """The plaza beacon in the middle, showing the year's total."""
    for radius, colour in ((6.2, (24, 42, 44)), (4.6, (30, 62, 60)), (2.6, (46, 110, 104))):
        draw.ellipse(ellipse_box(radius), fill=colour)
    draw.ellipse(ellipse_box(1.1), fill=BEACON)
    x, base_y = CX * SS, CY * SS
    top_y = base_y - 3.1 * SCALE * COS_E * SS
    draw.polygon([(x - 7, base_y), (x + 7, base_y), (x + 1, top_y), (x - 1, top_y)], fill=BEACON)
    draw.text((x, top_y - 8 * SS), f"{total:,} contributions", font=font, fill=(255, 255, 255), anchor="md")


def render_frame(index, towers, labels, numbers, fonts, backdrop):
    angle = math.tau * index / FRAMES
    cos_t, sin_t = math.cos(angle), math.sin(angle)
    image = backdrop.copy()
    draw = ImageDraw.Draw(image)

    for radius, colour in ((R_INNER + 7 * ROW + 0.55, RIM), (R_INNER + 7 * ROW + 0.48, GROUND)):
        draw.ellipse(ellipse_box(radius), fill=colour)
    draw.ellipse(ellipse_box(R_INNER - 0.1), fill=(16, 22, 30))

    for label, a in labels:
        radius = R_INNER + 7 * ROW + 1.1
        (x, y), _ = project(radius * math.cos(a), radius * math.sin(a), 0, cos_t, sin_t)
        draw.text((x, y), label, font=fonts["month"], fill=MUTED, anchor="mm")

    order = sorted(
        towers,
        key=lambda t: t["centre"][0] * sin_t + t["centre"][1] * cos_t,
    )
    far = [t for t in order if t["centre"][0] * sin_t + t["centre"][1] * cos_t < 0]
    near = order[len(far):]
    for tower in far:
        draw_tower(draw, tower, cos_t, sin_t)
    draw_core(draw, fonts["total"], numbers["total"])
    for tower in near:
        draw_tower(draw, tower, cos_t, sin_t)

    # Neon bloom, then downsample for clean edges.
    small = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    glow = small.point(lambda v: max(0, v - 175)).filter(ImageFilter.GaussianBlur(6))
    return ImageChops.screen(small, glow)


def make_backdrop(numbers, fonts):
    image = Image.new("RGB", (WIDTH * SS, HEIGHT * SS), BACKGROUND)
    draw = ImageDraw.Draw(image)
    stars = random.Random(7)
    for _ in range(190):
        x, y = stars.randrange(WIDTH * SS), stars.randrange(HEIGHT * SS)
        size = stars.choice((1, 1, 2, 2, 3))
        tone = stars.randrange(60, 200)
        draw.ellipse([x, y, x + size, y + size], fill=(tone, tone, min(255, tone + 20)))

    draw.text((24 * SS, 22 * SS), "CONTRIBUTION CITY", font=fonts["title"], fill=TEXT)
    draw.text((24 * SS, 46 * SS), "one tower per day, last 12 months", font=fonts["small"], fill=MUTED)
    rows = [
        (f"{numbers['best']}", "best day"),
        (f"{numbers['streak']}d", "longest streak"),
        (f"{numbers['active']}", "active days"),
    ]
    for i, (value, label) in enumerate(rows):
        y = (22 + i * 25) * SS
        draw.text(((WIDTH - 24) * SS, y), label, font=fonts["small"], fill=MUTED, anchor="ra")
        offset = draw.textlength(label, font=fonts["small"]) + 9 * SS
        draw.text(((WIDTH - 24) * SS - offset, y - 2 * SS), value, font=fonts["stat"], fill=ACCENT, anchor="ra")
    return image


def render(days, output):
    towers, labels = build_city(days)
    numbers = stats(days)
    fonts = {
        "title": ImageFont.load_default(18 * SS),
        "stat": ImageFont.load_default(17 * SS),
        "small": ImageFont.load_default(12 * SS),
        "month": ImageFont.load_default(11 * SS),
        "total": ImageFont.load_default(19 * SS),
    }
    backdrop = make_backdrop(numbers, fonts)
    frames = [render_frame(i, towers, labels, numbers, fonts, backdrop) for i in range(FRAMES)]

    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_MS,
        loop=0,
        quality=QUALITY,
        method=4,
    )
    print(f"{output}: {output.stat().st_size / 1e6:.2f} MB, {numbers}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("username", nargs="?")
    parser.add_argument("-o", "--output", type=Path, default=Path("skyline.webp"))
    parser.add_argument("--input", type=Path, help="read days from a JSON file")
    args = parser.parse_args()

    if args.input:
        days = json.loads(args.input.read_text())
    elif args.username:
        token = os.environ.get("GH_TOKEN")
        if not token:
            parser.error("set GH_TOKEN, or pass --input")
        days = fetch_days(args.username, token)
    else:
        parser.error("pass a username or --input")
    render(days, args.output)


if __name__ == "__main__":
    main()
