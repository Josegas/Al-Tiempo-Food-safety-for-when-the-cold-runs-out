"""Figures for the article and README, generated from code (and from eval results, not by hand).

    python3 scripts/make_figures.py      # needs Pillow (pip install pillow)

Writes PNGs to docs/img/. The model chart reads evals/results/20261103-150404.json, so the
picture can always be checked against the raw data.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "img"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")

# Palette (dataviz reference instance, light mode)
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e6e5e0"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
VIOLET = "#6250d6"
RED = "#e34948"
GRAY_BAR = "#c9c8c1"

# Bedrock prices per 1K tokens (AWS Price List API, us-east-1, checked 2026-11-03)
PRICE = {"us.amazon.nova-2-lite-v1:0": (0.00033, 0.00275)}
LABEL = {
    "us.amazon.nova-lite-v1:0": "Amazon Nova Lite",
    "us.amazon.nova-pro-v1:0": "Amazon Nova Pro",
    "us.amazon.nova-2-lite-v1:0": "Amazon Nova 2 Lite",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except OSError:
        return ImageFont.load_default(size)


def wrap(d: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        line = ""
        for word in para.split(" "):
            test = f"{line} {word}".strip()
            if d.textlength(test, font=f) <= width:
                line = test
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def box(d, xy, title, body="", accent=BLUE, fill="#ffffff", title_size=26, body_size=21):
    x0, y0, x1, y1 = xy
    d.rounded_rectangle(xy, radius=14, fill=fill, outline=GRID, width=2)
    d.rounded_rectangle((x0, y0, x0 + 10, y1), radius=5, fill=accent)
    ft, fb = font(title_size, True), font(body_size)
    y = y0 + 16
    for ln in wrap(d, title, ft, x1 - x0 - 44):
        d.text((x0 + 26, y), ln, font=ft, fill=INK)
        y += title_size + 8
    y += 4
    for ln in wrap(d, body, fb, x1 - x0 - 44):
        d.text((x0 + 26, y), ln, font=fb, fill=INK_2)
        y += body_size + 7


def arrow(d, p0, p1, color=INK_2, width=4, label="", label_dy=-30):
    d.line([p0, p1], fill=color, width=width)
    (x0, y0), (x1, y1) = p0, p1
    import math

    ang = math.atan2(y1 - y0, x1 - x0)
    size = 16
    left = (x1 - size * math.cos(ang - 0.45), y1 - size * math.sin(ang - 0.45))
    right = (x1 - size * math.cos(ang + 0.45), y1 - size * math.sin(ang + 0.45))
    d.polygon([p1, left, right], fill=color)
    if label:
        f = font(19)
        w = d.textlength(label, font=f)
        d.text(((x0 + x1) / 2 - w / 2, (y0 + y1) / 2 + label_dy), label, font=f, fill=INK_2)


def canvas(w, h):
    img = Image.new("RGB", (w, h), SURFACE)
    return img, ImageDraw.Draw(img)


def title(d, text, sub="", x=50, y=36):
    d.text((x, y), text, font=font(38, True), fill=INK)
    if sub:
        d.text((x, y + 54), sub, font=font(23), fill=INK_2)


# ---------------------------------------------------------------------------
def clock_art(d, cx: int, cy: int, r: int, temp: str = "38 °C") -> None:
    """Sun + clock (12:00, red deadline hand) + thermometer, plain shapes (original artwork)."""
    import math

    k = r / 180  # every size below was designed for r = 180
    for i in range(12):
        a = i * math.pi / 6
        d.line(
            [
                (cx + (r + 26 * k) * math.cos(a), cy + (r + 26 * k) * math.sin(a)),
                (cx + (r + 62 * k) * math.cos(a), cy + (r + 62 * k) * math.sin(a)),
            ],
            fill="#f3b13b",
            width=round(14 * k),
        )
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#ffffff", outline=ORANGE, width=round(16 * k))
    for i in range(12):
        a = i * math.pi / 6
        d.line(
            [
                (cx + (r - 40 * k) * math.cos(a), cy + (r - 40 * k) * math.sin(a)),
                (cx + (r - 18 * k) * math.cos(a), cy + (r - 18 * k) * math.sin(a)),
            ],
            fill=INK_2,
            width=round(6 * k),
        )
    d.line([(cx, cy), (cx, cy - 140 * k)], fill=INK, width=round(12 * k))  # 12:00
    d.line([(cx, cy), (cx + 95 * k, cy)], fill=RED, width=round(12 * k))  # deadline hand
    d.ellipse((cx - 16 * k, cy - 16 * k, cx + 16 * k, cy + 16 * k), fill=INK)
    # thermometer
    tx, ty = cx + 300 * k, cy + 120 * k
    d.rounded_rectangle(
        (tx - 22 * k, ty - 260 * k, tx + 22 * k, ty + 40 * k),
        radius=round(22 * k),
        fill="#ffffff",
        outline=INK_2,
        width=round(6 * k),
    )
    d.rounded_rectangle(
        (tx - 10 * k, ty - 170 * k, tx + 10 * k, ty + 40 * k), radius=round(10 * k), fill=RED
    )
    d.ellipse(
        (tx - 45 * k, ty + 10 * k, tx + 45 * k, ty + 100 * k),
        fill=RED,
        outline=INK_2,
        width=round(6 * k),
    )
    d.text((tx - 50 * k, ty - 330 * k), temp, font=font(round(38 * k), True), fill=RED)


def cover() -> None:
    img, d = canvas(1600, 840)
    d.rectangle((0, 0, 1600, 840), fill="#fff7ef")
    clock_art(d, 1210, 380, 180)

    d.text((80, 150), "Al Tiempo", font=font(110, True), fill=INK)
    d.text((86, 290), "Food safety for when the cold runs out", font=font(42), fill=INK_2)
    lines = [
        "An AI agent that tells households and shelters",
        "without refrigeration until what time cooked food",
        "can be eaten, using official food-safety rules",
        "and today's heat forecast.",
    ]
    for i, ln in enumerate(lines):
        d.text((86, 400 + i * 46), ln, font=font(32), fill=INK)
    d.text(
        (86, 640),
        "Strands Agents · AgentCore · English / Español",
        font=font(28, True),
        fill=ORANGE,
    )
    d.text(
        (86, 690),
        "WHO · U.S. FDA · CDC · NHS rules, each with its verbatim source",
        font=font(26),
        fill=INK_2,
    )
    img.save(OUT / "cover.png", optimize=True)


# ---------------------------------------------------------------------------
def architecture() -> None:
    img, d = canvas(1700, 1190)
    title(d, "Al Tiempo on AWS", "All infrastructure is AWS CDK (2 stacks). Nothing runs 24/7.")
    y0 = 170
    box(
        d,
        (40, y0, 330, y0 + 170),
        "Phone or browser",
        "Bilingual web, demo mode, voice button, no login",
        MUTED,
    )
    box(
        d,
        (400, y0, 720, y0 + 170),
        "CloudFront + S3",
        "Static web, private bucket (OAC), security headers",
        VIOLET,
    )
    box(
        d,
        (790, y0, 1130, y0 + 170),
        "API Gateway + Lambda",
        "10 req/s, burst 20. Daily caps in DynamoDB; warm-up on page load",
        ORANGE,
    )
    arrow(d, (330, y0 + 85), (400, y0 + 85))
    arrow(d, (720, y0 + 85), (790, y0 + 85), label="/api/*")
    box(d, (790, y0 + 240, 1130, y0 + 360), "Amazon Polly", "Reads answers aloud (es/en)", AQUA)
    arrow(d, (960, y0 + 170), (960, y0 + 240))

    # Agent runtime
    ax0, ay0, ax1, ay1 = 1200, y0, 1660, y0 + 560
    d.rounded_rectangle((ax0, ay0, ax1, ay1), radius=18, fill="#f1f6fd", outline=BLUE, width=3)
    d.text((ax0 + 24, ay0 + 18), "Bedrock AgentCore Runtime", font=font(25, True), fill=INK)
    d.text((ax0 + 24, ay0 + 54), "ARM64 zip, no Docker · IAM auth only", font=font(20), fill=INK_2)
    box(
        d,
        (ax0 + 24, ay0 + 100, ax1 - 24, ay0 + 225),
        "Strands agent",
        "Agent loop + 7 tools, one session per user",
        BLUE,
    )
    box(
        d,
        (ax0 + 24, ay0 + 245, ax1 - 24, ay0 + 385),
        "Amazon Nova 2 Lite",
        "via a tagged application inference profile (cost per project)",
        BLUE,
    )
    box(
        d,
        (ax0 + 24, ay0 + 405, ax1 - 24, ay0 + 540),
        "Verifier hook",
        "Blocks any time or limit that the rules engine did not produce",
        RED,
    )
    arrow(d, (1130, y0 + 85), (ax0, y0 + 85), label="invoke")

    # Tools row
    ty = 850
    d.text(
        (40, ty - 112),
        "Agent tools and what they trigger (deterministic code, unit-tested)",
        font=font(26, True),
        fill=INK,
    )
    box(
        d,
        (40, ty, 420, ty + 200),
        "Rules engine",
        "11 official rules in YAML (WHO, FDA, CDC, NHS), each with its verbatim sentence",
        RED,
    )
    box(
        d,
        (450, ty, 800, ty + 200),
        "Forecast",
        "Open-Meteo hourly temperature; saved 38 °C day in demo mode",
        AQUA,
    )
    box(
        d,
        (830, ty, 1240, ty + 200),
        "EventBridge Scheduler",
        "One-time reminder at the exact minute; deletes itself after running",
        ORANGE,
    )
    box(
        d,
        (1270, ty, 1660, ty + 200),
        "Lambda + DynamoDB",
        "Stores the delivered reminder; data expires in 7 days (TTL). SMS optional",
        VIOLET,
    )
    arrow(d, (1240, ty + 100), (1270, ty + 100))
    d.line([(1430, ay1), (1430, ty - 50)], fill=INK_2, width=4)
    d.line([(230, ty - 50), (1430, ty - 50)], fill=INK_2, width=4)
    for x in (230, 625, 1035):
        arrow(d, (x, ty - 50), (x, ty - 4))

    # Ops band
    oy = 1085
    d.rounded_rectangle((40, oy, 1660, oy + 80), radius=14, fill="#ffffff", outline=GRID, width=2)
    d.text(
        (64, oy + 24),
        "Ops: CloudWatch dashboard + 3 alarms to email · $10 budget with automatic kill switch · GitHub Actions + OIDC",
        font=font(22),
        fill=INK_2,
    )
    img.save(OUT / "architecture.png", optimize=True)


# ---------------------------------------------------------------------------
def verifier() -> None:
    img, d = canvas(1700, 860)
    title(
        d,
        "The model talks. The rules decide.",
        "What happens to one message (real example, demo day of 38 °C, clock at 12:00)",
    )
    y = 190
    w, h, gap = 290, 210, 40
    xs = [40 + i * (w + gap) for i in range(5)]
    steps = [
        ("1. User", '"I cooked beans at 12:00. Until when can we eat them?"', MUTED),
        (
            "2. Code reads the time",
            "From the user's own words: cooked at 12:00. The model cannot change it.",
            AQUA,
        ),
        ("3. Rules engine", "38 °C > 32 °C, so the FDA 1-hour rule applies: eat by 13:00", RED),
        ("4. Model writes", "Nova 2 Lite explains the result in the user's language", BLUE),
        ("5. Verifier hook", "Is every time and limit in the answer in the engine's result?", RED),
    ]
    for x, (t, b, c) in zip(xs, steps, strict=True):
        box(d, (x, y, x + w, y + h), t, b, c, title_size=25, body_size=20)
    for i in range(4):
        arrow(d, (xs[i] + w, y + h / 2), (xs[i + 1], y + h / 2))

    r2 = 540
    box(
        d,
        (xs[4], r2, xs[4] + w, r2 + 160),
        "Yes: send it",
        '"Eat them before 13:00 or throw them away."',
        AQUA,
        title_size=24,
        body_size=20,
    )
    arrow(d, (xs[4] + w / 2, y + h), (xs[4] + w / 2, r2))
    d.text((xs[4] + w / 2 + 14, 480), "yes", font=font(19), fill=INK_2)
    box(
        d,
        (xs[3], r2, xs[3] + w, r2 + 160),
        "No: retry once",
        "The model gets a correction note and rewrites",
        ORANGE,
        title_size=24,
        body_size=20,
    )
    d.line([(xs[4] + 40, y + h), (xs[4] + 40, 470)], fill=INK_2, width=4)
    d.line([(xs[4] + 40, 470), (xs[3] + w / 2, 470)], fill=INK_2, width=4)
    arrow(d, (xs[3] + w / 2, 470), (xs[3] + w / 2, r2))
    d.text((xs[3] + w / 2 + 14, 480), "no", font=font(19), fill=INK_2)
    box(
        d,
        (xs[0] + 60, r2, xs[2] + w, r2 + 160),
        "Still unbacked after the retry: safe template",
        '"According to U.S. FDA, eat it before 13:00 or throw it away."',
        RED,
        title_size=24,
        body_size=20,
    )
    arrow(d, (xs[3], r2 + 80), (xs[2] + w, r2 + 80))
    d.text(
        (40, 770),
        "Measured: 8 of 8 invented times blocked in adversarial tests; 0 of 100 eval answers needed the template.",
        font=font(22, True),
        fill=INK,
    )
    img.save(OUT / "verifier.png", optimize=True)


# ---------------------------------------------------------------------------
def model_chart() -> None:
    data = json.loads((ROOT / "evals/results/20261103-150404.json").read_text())
    rows = []
    for m in data:
        cost = m["cost_per_turn_usd"]
        if cost is None:  # price was added to the runner after this run: tokens x price
            pin, pout = PRICE[m["model"]]
            cost = m["avg_input_tokens"] / 1000 * pin + m["avg_output_tokens"] / 1000 * pout
        rows.append((LABEL[m["model"]], m["passed"], m["runs"], cost, m["median_latency_ms"]))

    img, d = canvas(1600, 760)
    title(
        d,
        "Choosing the model with evals, not by guessing",
        "Same agent, same 18 bilingual scenarios (incl. adversarial ones), 1 run per model",
    )
    x0, x1 = 420, 1240
    top, bar_h, step = 220, 74, 150
    for pct in (0, 25, 50, 75, 100):
        x = x0 + (x1 - x0) * pct / 100
        d.line([(x, top - 30), (x, top + step * 3 - 50)], fill=GRID, width=2)
        lbl = f"{pct}%"
        d.text(
            (x - d.textlength(lbl, font=font(20)) / 2, top + step * 3 - 40),
            lbl,
            font=font(20),
            fill=MUTED,
        )
    for i, (name, passed, runs, cost, lat) in enumerate(rows):
        y = top + i * step
        chosen = passed == runs
        d.text((40, y + 8), name, font=font(28, True), fill=INK)
        d.text((40, y + 46), "chosen" if chosen else "", font=font(22, True), fill=BLUE)
        w = (x1 - x0) * passed / runs
        d.rounded_rectangle((x0, y, x0 + w, y + bar_h), radius=4, fill=BLUE if chosen else GRAY_BAR)
        d.rectangle((x0, y, x0 + 6, y + bar_h), fill=BLUE if chosen else GRAY_BAR)
        d.text(
            (x0 + w + 18, y + 4),
            f"{passed}/{runs} ({passed / runs:.0%})",
            font=font(28, True),
            fill=INK,
        )
        d.text((x0 + w + 18, y + 42), f"${cost:.4f}/turn · {lat:,} ms", font=font(21), fill=INK_2)
    d.text(
        (40, 700),
        "Cost = measured tokens × AWS Price List API price (us-east-1). Data: evals/results/20261103-150404.json",
        font=font(20),
        fill=MUTED,
    )
    img.save(OUT / "model-evals.png", optimize=True)


# ---------------------------------------------------------------------------
def video_thumbnail() -> None:
    """YouTube thumbnail, 1280x720 (16:9). Few, big words: it is seen at phone size."""
    img, d = canvas(1280, 720)
    d.rectangle((0, 0, 1280, 720), fill="#fff7ef")
    d.rectangle((0, 0, 1280, 16), fill=ORANGE)
    clock_art(d, 840, 380, 175, temp="")
    d.text((60, 70), "38 °C.", font=font(96, True), fill=RED)
    d.text((60, 175), "No fridge.", font=font(96, True), fill=INK)
    d.text((60, 330), "Eat it before", font=font(64, True), fill=INK_2)
    d.text((60, 405), "13:00", font=font(150, True), fill=ORANGE)
    d.text((60, 620), "Al Tiempo · AI food-safety agent", font=font(36, True), fill=INK)
    img.save(OUT / "thumbnail-video.png", optimize=True)


def article_thumbnail() -> None:
    """Article card image, 1600x900 (16:9): name, promise and one measured number."""
    img, d = canvas(1600, 900)
    d.rectangle((0, 0, 1600, 900), fill="#fff7ef")
    d.rectangle((0, 0, 1600, 18), fill=ORANGE)
    clock_art(d, 1170, 440, 210)
    d.text((80, 140), "Al Tiempo", font=font(120, True), fill=INK)
    lines = ["Until what time is", "cooked food safe", "without a fridge?"]
    for i, ln in enumerate(lines):
        d.text((86, 320 + i * 72), ln, font=font(58, True), fill=INK_2)
    d.text((86, 590), "Official rules + today's heat forecast", font=font(36), fill=INK)
    d.text((86, 650), "Strands Agents · Amazon Bedrock AgentCore", font=font(30, True), fill=ORANGE)
    d.text((86, 760), "Health · English / Español", font=font(30), fill=INK_2)
    img.save(OUT / "thumbnail-article.png", optimize=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    cover()
    video_thumbnail()
    article_thumbnail()
    architecture()
    verifier()
    model_chart()
    print("written:", ", ".join(sorted(p.name for p in OUT.glob("*.png"))))
