"""Render the profile graphics — the 23ag.one signature, ported to SVG.

  assets/hero-{dark,light}.svg  "23AG" as a live field of symbols with a colour
                                glint and an occasional flash; a flock of ASCII
                                birds flapping across the sky above it.
  assets/year-{dark,light}.svg  the contribution calendar of the last 12 months,
                                one symbol per day, heavier symbol = busier day.
  assets/dot.svg                the pulsing "taking on projects" dot.

GitHub shows README images through <img>: no JS, no external fonts. So every
glyph is an outline path, motion is CSS + SMIL, and the one text font (Golos
Text) is embedded as a subset woff2. Runs daily from .github/workflows/hero.yml.
"""

import base64
import datetime as dt
import io
import json
import os
import pathlib
import random
import re
import urllib.request

from fontTools import subset
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw

LOGIN = "23ag1"
WORD = "23AG"

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "scripts" / "fonts"
OUT = ROOT / "assets"

SERIF = TTFont(FONTS / "LiberationSerif-Bold.ttf")  # Times metrics, as on 23ag.one
SYMBOLS = TTFont(FONTS / "DejaVuSans-Symbols.ttf")

# README column on github.com is 846 CSS px wide: 1 SVG unit = 1 px on desktop.
W = 846
GLYPHS = ["*", "+", "·", "✦", "⋆", "◦", "°", "∘", ":", "✳", "•", "×"]
REEL = ["\\·/", "~·~", "-·-", "/·\\", "-·-", "~·~"]  # one flap, body = ·

THEMES = {
    "dark": {"ink": "#E6EDF3", "sky": "#7D8590", "muted": "#9198A1", "light": 62},
    "light": {"ink": "#1A1A17", "sky": "#A7A49B", "muted": "#59636E", "light": 52},
}

# ── outlines ────────────────────────────────────────────────────────────────


def outline(font, text, size, x=0.0, baseline=0.0, tracking=0.0):
    """Text → one SVG path (y down). Returns (d, advance width)."""
    gs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    scale = size / font["head"].unitsPerEm
    pen = SVGPathPen(gs)
    cx = x
    for ch in text:
        name = cmap[ord(ch)]
        gs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, cx, baseline)))
        cx += hmtx[name][0] * scale + tracking * size
    return pen.getCommands(), cx - x - tracking * size


# box each symbol fills, as a share of the cell: marks are big, dots stay dots
SYMBOL_BOX = {"·": 0.3, "•": 0.5, "°": 0.5, "◦": 0.55, "∘": 0.55, ":": 0.75}


def symbol_defs(cell, prefix):
    """Each symbol normalised to its box and centred on (0,0), so a <use x y>
    puts it in a cell centre. DejaVu draws these marks small inside the em;
    sizing by bounds is what makes the field read as solid letters."""
    gs, cmap = SYMBOLS.getGlyphSet(), SYMBOLS.getBestCmap()
    out = []
    for i, ch in enumerate(GLYPHS):
        g = gs[cmap[ord(ch)]]
        bp = BoundsPen(gs)
        g.draw(bp)
        x0, y0, x1, y1 = bp.bounds
        scale = cell * SYMBOL_BOX.get(ch, 0.9) / max(x1 - x0, y1 - y0)
        pen = SVGPathPen(gs)
        g.draw(TransformPen(pen, (scale, 0, 0, -scale, -(x0 + x1) / 2 * scale, (y0 + y1) / 2 * scale)))
        out.append(f'<path id="{prefix}{i}" d="{pen.getCommands()}"/>')
    return "".join(out)


def reel_defs(size):
    """Bird frames: three symbols on a fixed 0.62em pitch, like the site's <pre>."""
    out = []
    for i, frame in enumerate(REEL):
        d = "".join(
            outline(SYMBOLS, ch, size, x=k * size * 0.62, baseline=size * 0.36)[0]
            for k, ch in enumerate(frame)
        )
        out.append(f'<path id="b{i}" d="{d}"/>')
    return "".join(out)


def font_face(family, file, text):
    font = TTFont(FONTS / file)
    opts = subset.Options()
    opts.layout_features = ["kern", "liga", "tnum", "lnum"]
    sub = subset.Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    font.flavor = "woff2"
    buf = io.BytesIO()
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{family}';src:url(data:font/woff2;base64,{data}) format('woff2');}}"


def hue_gradient(light, span):
    """A full hue wheel repeated every `span` px, drifting sideways — the
    'moving hue' that gives the site's glint its iridescent wash."""
    stops = "".join(
        f'<stop offset="{i / 6:.3f}" stop-color="hsl({i * 60} 88% {light}%)"/>'
        for i in range(7)
    )
    return (
        f'<linearGradient id="hue" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{span:.0f}" y2="0" spreadMethod="repeat">{stops}'
        f'<animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="{span:.0f} 0" dur="14s" repeatCount="indefinite"/>'
        "</linearGradient>"
    )


def glint_band(x2, y2, width, travel, dur):
    """White band for a mask: sweeps across, then rests before the next pass."""
    return (
        f'<linearGradient id="band" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{x2:.0f}" y2="{y2:.0f}">'
        f'<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="{width / 2}" stop-color="#fff"/>'
        f'<stop offset="{width}" stop-color="#fff" stop-opacity="0"/>'
        f'<animateTransform attributeName="gradientTransform" type="translate" values="-{W} 0;{W * travel:.0f} 0;{W * travel:.0f} 0" '
        f'keyTimes="0;.6;1" dur="{dur}s" repeatCount="indefinite"/></linearGradient>'
    )


# ── hero ────────────────────────────────────────────────────────────────────


def raster(d_path, w, h, k=2):
    """Rasterise an M/L/H/V/Q/Z path even-odd, so counters (holes in A, G) stay open."""
    toks = re.findall(r"[MLHVQCZ]|-?\d+(?:\.\d+)?", d_path)
    polys, poly, cur, i = [], [], (0.0, 0.0), 0
    while i < len(toks):
        c = toks[i]
        if c in "ML":
            if c == "M" and poly:
                polys.append(poly)
                poly = []
            cur = (float(toks[i + 1]), float(toks[i + 2]))
            poly.append(cur)
            i += 3
        elif c in "HV":
            v = float(toks[i + 1])
            cur = (v, cur[1]) if c == "H" else (cur[0], v)
            poly.append(cur)
            i += 2
        elif c == "Q":
            c1 = (float(toks[i + 1]), float(toks[i + 2]))
            p2 = (float(toks[i + 3]), float(toks[i + 4]))
            for s in range(1, 9):
                t = s / 8
                poly.append(
                    (
                        (1 - t) ** 2 * cur[0] + 2 * (1 - t) * t * c1[0] + t * t * p2[0],
                        (1 - t) ** 2 * cur[1] + 2 * (1 - t) * t * c1[1] + t * t * p2[1],
                    )
                )
            cur = p2
            i += 5
        else:
            i += 1
    if poly:
        polys.append(poly)
    acc = Image.new("1", (w * k, h * k), 0)
    for p in polys:
        layer = Image.new("1", acc.size, 0)
        ImageDraw.Draw(layer).polygon([(x * k, y * k) for x, y in p], fill=1)
        acc = ImageChops.logical_xor(acc, layer)
    return acc, k


def hero(theme, rng):
    t = THEMES[theme]
    sky_h, word_h = 92, 236
    h = sky_h + word_h

    # the word, fitted edge to edge with the site's -0.02em tracking
    _, adv = outline(SERIF, WORD, 100, tracking=-0.02)
    size = 100 * (W - 4) / adv
    cap = SERIF["OS/2"].sCapHeight / SERIF["head"].unitsPerEm * size
    baseline = sky_h + (word_h + cap) / 2 - 2
    d_word, _ = outline(SERIF, WORD, size, x=2, baseline=baseline, tracking=-0.02)

    mask, k = raster(d_word, W, h)
    step = 11
    uses = []
    for cy in range(int(baseline - cap) - step, int(baseline) + step, step):
        for cx in range(0, W, step):
            if (
                mask.crop((cx * k, cy * k, (cx + step) * k, (cy + step) * k)).getbbox()
                is None
            ):
                continue
            if rng.random() > 0.93:  # the site keeps ~90% of cells alive
                continue
            x, y = cx + step / 2, cy + step / 2
            g = rng.randrange(len(GLYPHS))
            r = rng.random()
            cls = f' class="w{rng.randrange(6)}"' if r < 0.45 else ""
            if r > 0.86:  # a few cells keep changing their symbol, like the canvas
                seq = ";".join(f"#g{rng.randrange(len(GLYPHS))}" for _ in range(4))
                anim = (
                    f'<animate attributeName="href" values="{seq}" dur="{rng.uniform(2.4, 6):.1f}s" '
                    f'begin="-{rng.uniform(0, 6):.1f}s" calcMode="discrete" repeatCount="indefinite"/>'
                )
                uses.append(
                    f'<use href="#g{g}" x="{x:.1f}" y="{y:.1f}"{cls}>{anim}</use>'
                )
            else:
                uses.append(f'<use href="#g{g}" x="{x:.1f}" y="{y:.1f}"{cls}/>')

    # the flock: one bird per lane, so they never overlap; each flaps and glides at its own pace
    birds = []
    lanes = 4
    for i in range(lanes):
        y = 14 + i * (sky_h - 30) / (lanes - 1) + rng.uniform(-2, 2)
        dur = rng.uniform(26, 48)
        flap = rng.choice([0.9, 1.35])
        x0, x1 = (W + 20, -60) if rng.random() < 0.5 else (-60, W + 20)
        start = rng.randrange(6)
        frames = ";".join(f"#b{(start + j) % 6}" for j in range(6))
        birds.append(
            f'<use href="#b{start}" y="{y:.0f}">'
            f'<animate attributeName="href" values="{frames}" dur="{flap}s" calcMode="discrete" repeatCount="indefinite"/>'
            f'<animate attributeName="x" from="{x0}" to="{x1}" dur="{dur:.0f}s" begin="-{rng.uniform(0, dur):.0f}s" repeatCount="indefinite"/>'
            "</use>"
        )

    css = (
        "".join(
            f".w{i}{{animation:tw {d}s ease-in-out -{(d * 0.37 * i) % d:.2f}s infinite}}"
            for i, d in enumerate([2.3, 3.1, 3.7, 4.3, 5.3, 6.1])
        )
        + "@keyframes tw{50%{opacity:.18}}"
        + ".fl{opacity:0;animation:fl 11s ease-out 2.5s infinite}"
        + "@keyframes fl{0%,86%{opacity:0}89%{opacity:1}100%{opacity:0}}"
        + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    )

    top = int(baseline - cap - step)
    paint = f'y="{top}" width="{W}" height="{h - top}"'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="23AG">
<style>{css}</style>
<defs>
{symbol_defs(10, "g")}
{reel_defs(22)}
<clipPath id="word"><path d="{d_word}"/></clipPath>
<mask id="field" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{h}"><g fill="#fff" clip-path="url(#word)">{"".join(uses)}</g></mask>
{hue_gradient(t["light"], W * 1.4)}
{glint_band(W, h * 0.6, 0.34, 1.4, 5)}
<mask id="glint" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{h}"><rect width="{W}" height="{h}" fill="url(#band)"/></mask>
</defs>
<g mask="url(#field)">
<rect {paint} fill="{t["ink"]}"/>
<rect {paint} fill="url(#hue)" mask="url(#glint)"/>
<rect {paint} fill="url(#hue)" class="fl"/>
</g>
<g fill="{t["sky"]}">{"".join(birds)}</g>
</svg>
"""


# ── year ────────────────────────────────────────────────────────────────────

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""
# heavier symbol = busier day: · ◦ + * ✦  (indexes into GLYPHS)
LEVEL_GLYPH = {
    "NONE": 2,
    "FIRST_QUARTILE": 5,
    "SECOND_QUARTILE": 1,
    "THIRD_QUARTILE": 0,
    "FOURTH_QUARTILE": 3,
}


def fetch_calendar():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={
            "Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def streaks(days):
    """Longest run in the window, and the run that ends today (or yesterday,
    so the number doesn't drop to zero every morning before the first commit)."""
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    tail = days[:-1] if days and not days[-1]["contributionCount"] else days
    current = 0
    for d in reversed(tail):
        if not d["contributionCount"]:
            break
        current += 1
    return longest, current


def year(cal, theme):
    t = THEMES[theme]
    weeks = cal["weeks"][-53:]
    days = [d for w in weeks for d in w["contributionDays"]]
    longest, current = streaks(days)
    total = f"{cal['totalContributions']:,}".replace(",", " ")
    stats = [
        (total, "contributions, last 12 months"),
        (str(longest), "days, longest streak"),
        (str(current), "days, current streak"),
    ]

    step = (W - 8) / 53
    top = 4
    uses = []
    for wi, week in enumerate(weeks):
        for d in week["contributionDays"]:
            wd = (
                dt.date.fromisoformat(d["date"]).weekday() + 1
            ) % 7  # Sunday on top, as on GitHub
            lvl = d["contributionLevel"]
            x, y = 4 + wi * step + step / 2, top + wd * step + step / 2
            dim = ' opacity=".35"' if lvl == "NONE" else ""
            uses.append(
                f'<use href="#y{LEVEL_GLYPH[lvl]}" x="{x:.1f}" y="{y:.1f}"{dim}/>'
            )

    grid_h = top + 7 * step + 4
    vy = grid_h + 54
    values, labels = [], []
    for i, (value, label) in enumerate(stats):
        x = 4 + i * 18 * step + 2
        d, _ = outline(SERIF, value, 44, x=x, baseline=vy)
        values.append(f'<path d="{d}"/>')
        labels.append(f'<text x="{x:.1f}" y="{vy + 28:.0f}">{label}</text>')
    h = int(vy + 40)

    css = font_face(
        "AG Text", "GolosText-Regular.ttf", "".join(l for _, l in stats)
    ) + (f"text{{font:400 16px 'AG Text',sans-serif;fill:{t['muted']}}}")
    area = f'width="{W}" height="{grid_h:.0f}"'
    label = f"{total} contributions in the last 12 months, longest streak {longest} days, current streak {current} days."
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{label}">
<style>{css}</style>
<defs>
{symbol_defs(11, "y")}
{hue_gradient(t["light"], W * 1.4)}
{glint_band(W, grid_h, 0.16, 1.2, 9)}
<mask id="cells" maskUnits="userSpaceOnUse" x="0" y="0" {area}><g fill="#fff">{"".join(uses)}</g></mask>
<mask id="glint" maskUnits="userSpaceOnUse" x="0" y="0" {area}><rect {area} fill="url(#band)"/></mask>
</defs>
<g mask="url(#cells)">
<rect {area} fill="{t["ink"]}"/>
<rect {area} fill="url(#hue)" mask="url(#glint)"/>
</g>
<g fill="{t["ink"]}">{"".join(values)}</g>
{"".join(labels)}
</svg>
"""


DOT = """<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12">
<style>circle{animation:p 2.4s ease-in-out infinite}@keyframes p{50%{opacity:.35}}@media (prefers-reduced-motion:reduce){circle{animation:none}}</style>
<circle cx="6" cy="6" r="5" fill="#3FB950"/></svg>
"""


def main():
    OUT.mkdir(exist_ok=True)
    for theme in THEMES:
        # fixed seed: the hero only changes when this script does, so daily runs don't churn it
        (OUT / f"hero-{theme}.svg").write_text(
            hero(theme, random.Random(23)), encoding="utf-8"
        )
    (OUT / "dot.svg").write_text(DOT, encoding="utf-8")
    cal = fetch_calendar()
    for theme in THEMES:
        (OUT / f"year-{theme}.svg").write_text(year(cal, theme), encoding="utf-8")


if __name__ == "__main__":
    main()
