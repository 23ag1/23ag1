"""Render assets/year-{dark,light}.svg: the contribution calendar of the last
12 months drawn in the 23ag.one symbols (one per day, heavier = busier) and
three numbers set in Times New Roman Bold.

Static on purpose: an animated SVG inside <img> repaints on the main thread
every frame. The motion lives in the hero WebP (scripts/hero/).

GitHub shows README images through <img>: no JS, no external fonts. So glyphs
are outline paths and the label font (Golos Text) is embedded as woff2.
Needs Times New Roman (Debian/Ubuntu: ttf-mscorefonts-installer).
Runs daily from .github/workflows/hero.yml.
"""

import base64
import datetime as dt
import io
import json
import os
import pathlib
import urllib.request

from fontTools import subset
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

LOGIN = "23ag1"

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "scripts" / "fonts"
OUT = ROOT / "assets"

TIMES = TTFont("/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold.ttf")
SYMBOLS = TTFont(FONTS / "DejaVuSans-Symbols.ttf")

# README column on github.com is 846 CSS px wide: 1 SVG unit = 1 px on desktop.
W = 846
PAD = 24  # same side margins as the hero
# heavier symbol = busier day
LEVEL_GLYPH = {
    "NONE": "·",
    "FIRST_QUARTILE": "◦",
    "SECOND_QUARTILE": "+",
    "THIRD_QUARTILE": "*",
    "FOURTH_QUARTILE": "✦",
}
# box each symbol fills, as a share of the cell: marks are big, dots stay dots
SYMBOL_BOX = {"·": 0.3, "◦": 0.55}

THEMES = {
    "dark": {"ink": "#E6EDF3", "muted": "#9198A1"},
    "light": {"ink": "#1A1A17", "muted": "#59636E"},
}

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


def outline(font, text, size, x=0.0, baseline=0.0):
    """Text → one SVG path (y down)."""
    gs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    scale = size / font["head"].unitsPerEm
    pen = SVGPathPen(gs)
    for ch in text:
        name = cmap[ord(ch)]
        gs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, baseline)))
        x += hmtx[name][0] * scale
    return pen.getCommands()


def symbol_defs(cell):
    """Each symbol normalised to its box and centred on (0,0)."""
    gs, cmap = SYMBOLS.getGlyphSet(), SYMBOLS.getBestCmap()
    out = []
    for level, ch in LEVEL_GLYPH.items():
        g = gs[cmap[ord(ch)]]
        bp = BoundsPen(gs)
        g.draw(bp)
        x0, y0, x1, y1 = bp.bounds
        scale = cell * SYMBOL_BOX.get(ch, 0.9) / max(x1 - x0, y1 - y0)
        pen = SVGPathPen(gs)
        g.draw(
            TransformPen(
                pen,
                (scale, 0, 0, -scale, -(x0 + x1) / 2 * scale, (y0 + y1) / 2 * scale),
            )
        )
        out.append(f'<path id="{level}" d="{pen.getCommands()}"/>')
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

    step = (W - PAD * 2) / 53
    top = 4
    uses = []
    for wi, week in enumerate(weeks):
        for d in week["contributionDays"]:
            wd = (
                dt.date.fromisoformat(d["date"]).weekday() + 1
            ) % 7  # Sunday on top, as on GitHub
            lvl = d["contributionLevel"]
            x, y = PAD + wi * step + step / 2, top + wd * step + step / 2
            dim = ' opacity=".35"' if lvl == "NONE" else ""
            uses.append(f'<use href="#{lvl}" x="{x:.1f}" y="{y:.1f}"{dim}/>')

    vy = top + 7 * step + 58
    values, labels = [], []
    for i, (value, label) in enumerate(stats):
        x = PAD + i * 18 * step
        values.append(f'<path d="{outline(TIMES, value, 48, x=x, baseline=vy)}"/>')
        labels.append(f'<text x="{x:.1f}" y="{vy + 28:.0f}">{label}</text>')
    h = int(vy + 40)

    css = font_face(
        "AG Text", "GolosText-Regular.ttf", "".join(l for _, l in stats)
    ) + (f"text{{font:400 16px 'AG Text',sans-serif;fill:{t['muted']}}}")
    label = f"{total} contributions in the last 12 months, longest streak {longest} days, current streak {current} days."
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{label}">
<style>{css}</style>
<defs>{symbol_defs(11)}</defs>
<g fill="{t["ink"]}">{"".join(uses)}{"".join(values)}</g>
{"".join(labels)}
</svg>
"""


def main():
    cal = fetch_calendar()
    OUT.mkdir(exist_ok=True)
    for theme in THEMES:
        (OUT / f"year-{theme}.svg").write_text(year(cal, theme), encoding="utf-8")


if __name__ == "__main__":
    main()
