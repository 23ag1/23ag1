"""Render every text block of the README as SVG, set like 23ag.one: plain
Times New Roman, no styling beyond what the site's CSS does (bold names with
browser-style underlines, → arrows, opacity instead of colour) and ASCII
ornaments instead of rules.

  assets/<block>-{dark,light}.svg

Markdown can't choose a font, so text becomes outlines; alt text carries the
words. Static on purpose: an animated SVG in <img> repaints on the main thread
every frame — the motion lives in the hero WebP (scripts/hero/).
Needs Times New Roman (Debian/Ubuntu: ttf-mscorefonts-installer).
Runs daily from .github/workflows/hero.yml (the year block changes daily).
"""

import datetime as dt
import json
import os
import pathlib
import urllib.request
from dataclasses import dataclass
from html import escape

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

LOGIN = "23ag1"
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
MS = pathlib.Path("/usr/share/fonts/truetype/msttcorefonts")

# README column on github.com is 846 CSS px wide: 1 SVG unit = 1 px on desktop.
W = 846
PAD = 24  # side margins, same as the hero
INNER = W - PAD * 2

THEMES = {
    "dark": "#E6EDF3",
    "light": "#1A1A17",
}  # ink; everything else is ink at an opacity, as on the site


class Face:
    """A font with advances and pair kerning, drawn as outline paths."""

    def __init__(self, path):
        self.font = TTFont(path)
        self.gs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.hmtx = self.font["hmtx"]
        self.upm = self.font["head"].unitsPerEm
        self.kern = (
            self.font["kern"].kernTables[0].kernTable if "kern" in self.font else {}
        )
        post = self.font["post"]
        self.ul_pos, self.ul_thick = (
            post.underlinePosition / self.upm,
            post.underlineThickness / self.upm,
        )

    def _names(self, text):
        return [self.cmap[ord(ch)] for ch in text]

    def width(self, text, size, tracking=0.0):
        names = self._names(text)
        units = sum(self.hmtx[n][0] for n in names)
        units += sum(self.kern.get((a, b), 0) for a, b in zip(names, names[1:]))
        return units * size / self.upm + tracking * size * max(len(names) - 1, 0)

    def path(self, text, size, x, baseline, tracking=0.0):
        scale = size / self.upm
        pen = SVGPathPen(self.gs)
        names = self._names(text)
        for i, n in enumerate(names):
            self.gs[n].draw(TransformPen(pen, (scale, 0, 0, -scale, x, baseline)))
            x += self.hmtx[n][0] * scale + tracking * size
            if i + 1 < len(names):
                x += self.kern.get((n, names[i + 1]), 0) * scale
        return pen.getCommands()

    def wrap(self, text, size, max_w):
        lines, line = [], ""
        for word in text.split(" "):
            test = f"{line} {word}".strip()
            if line and self.width(test, size) > max_w:
                lines.append(line)
                line = word
            else:
                line = test
        return lines + [line]


ROMAN = Face(MS / "Times_New_Roman.ttf")
BOLD = Face(MS / "Times_New_Roman_Bold.ttf")
SYMBOLS = Face(
    ROOT / "scripts" / "fonts" / "DejaVuSans-Symbols.ttf"
)  # the same marks as the hero


@dataclass
class Block:
    h: float
    body: str
    alt: str


def text(face, s, size, x, y, opacity=1.0, anchor="start", tracking=0.0):
    if anchor == "end":
        x -= face.width(s, size, tracking)
    op = "" if opacity == 1 else f' fill-opacity="{opacity}"'
    return f'<path d="{face.path(s, size, x, y, tracking)}"{op}/>'


def underline(face, s, size, x, y, tracking=0.0):
    """Browser-style underline, text-underline-offset: 4px (site CSS)."""
    w = face.width(s, size, tracking)
    thick = max(1.0, face.ul_thick * size)
    return f'<rect x="{x:.1f}" y="{y + 4:.1f}" width="{w:.1f}" height="{thick:.2f}"/>'


def dots(y, opacity=0.22):
    """ASCII hairline: a row of middle dots, the site's 1 px border drawn in type."""
    pitch = 9
    n = int(INNER // pitch)
    x0 = PAD + (INNER - (n - 1) * pitch) / 2
    return "".join(
        text(SYMBOLS, "·", 12, x0 + i * pitch - 2, y, opacity) for i in range(n)
    )


def flock_rule(y, opacity=0.45):
    """The block's top rule: a line of gliding birds, -·- (the site's 2px black rule)."""
    unit = "-·-"
    size = 17
    uw = SYMBOLS.width(unit, size) + size * 1.6
    n = int((INNER + size * 1.6) // uw)
    x0 = PAD + (INNER - (n * uw - size * 1.6)) / 2
    return "".join(text(SYMBOLS, unit, size, x0 + i * uw, y, opacity) for i in range(n))


# ── blocks ──────────────────────────────────────────────────────────────────


def tagline(s):
    size, lh = 19, 19 * 1.45  # .tagline, compacted
    lines = ROMAN.wrap(s, size, 440)  # max-width: 42ch
    body = "".join(
        text(ROMAN, ln, size, PAD, 4 + size + i * lh, 0.65)
        for i, ln in enumerate(lines)
    )
    return Block(4 + size + (len(lines) - 1) * lh + 10, body, s)


def head(title):
    """.block top: ASCII rule, then the bold heading with the site's spacing."""
    size = 28  # .block__h, compacted
    body = flock_rule(14) + text(
        BOLD, title, size, PAD, 14 + 26 + size * 0.8, tracking=-0.02
    )
    return Block(14 + 26 + size * 0.8 + 16, body, title)


def row(name, desc=""):
    """.svc: bold underlined name, → on the right, description under it at .55."""
    ns, ds, dlh = 19, 16, 16 * 1.4
    y = 12 + ns * 0.8 + 4
    body = (
        dots(6)
        + text(BOLD, name, ns, PAD, y, tracking=-0.01)
        + underline(BOLD, name, ns, PAD, y, tracking=-0.01)
    )
    body += text(ROMAN, "→", 17, W - PAD, y, 0.35, anchor="end")
    lines = ROMAN.wrap(desc, ds, INNER - 60) if desc else []
    for i, ln in enumerate(lines):
        body += text(ROMAN, ln, ds, PAD, y + 8 + ds + i * dlh, 0.55)
    h = y + (8 + ds + (len(lines) - 1) * dlh if lines else 0) + 10
    return Block(h, body, f"{name} — {desc}" if desc else name)


def colophon():
    size = 16
    year = dt.date.today().year
    s = f"© {year} 23AG · Remote, worldwide"
    body = flock_rule(14) + text(ROMAN, s, size, PAD, 14 + 24 + size, 0.45)
    body += text(SYMBOLS, "~·~", 16, W - PAD, 14 + 24 + size, 0.45, anchor="end")
    return Block(14 + 24 + size + 14, body, s)


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
# heavier symbol = busier day
LEVEL_GLYPH = {
    "NONE": "·",
    "FIRST_QUARTILE": "◦",
    "SECOND_QUARTILE": "+",
    "THIRD_QUARTILE": "*",
    "FOURTH_QUARTILE": "✦",
}
SYMBOL_BOX = {
    "·": 0.3,
    "◦": 0.55,
}  # share of the cell a mark fills: marks are big, dots stay dots


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


def symbol_defs(cell):
    out = []
    for level, ch in LEVEL_GLYPH.items():
        g = SYMBOLS.gs[SYMBOLS.cmap[ord(ch)]]
        bp = BoundsPen(SYMBOLS.gs)
        g.draw(bp)
        x0, y0, x1, y1 = bp.bounds
        scale = cell * SYMBOL_BOX.get(ch, 0.9) / max(x1 - x0, y1 - y0)
        pen = SVGPathPen(SYMBOLS.gs)
        g.draw(
            TransformPen(
                pen,
                (scale, 0, 0, -scale, -(x0 + x1) / 2 * scale, (y0 + y1) / 2 * scale),
            )
        )
        out.append(f'<path id="{level}" d="{pen.getCommands()}"/>')
    return "".join(out)


def year(cal):
    weeks = cal["weeks"][-53:]
    days = [d for w in weeks for d in w["contributionDays"]]
    longest, current = streaks(days)
    total = f"{cal['totalContributions']:,}".replace(",", " ")
    stats = [
        (total, "contributions, last 12 months"),
        (str(longest), "days, longest streak"),
        (str(current), "days, current streak"),
    ]
    step = INNER / 53
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
    vy = top + 7 * step + 46
    body = f"<defs>{symbol_defs(11)}</defs>" + "".join(uses)
    for i, (value, label) in enumerate(stats):
        x = PAD + i * 18 * step
        body += text(BOLD, value, 34, x, vy, tracking=-0.02) + text(
            ROMAN, label, 16, x, vy + 24, 0.55
        )
    alt = f"{total} contributions in the last 12 months, longest streak {longest} days, current streak {current} days."
    return Block(vy + 24 + 14, body, alt)


# ── output ──────────────────────────────────────────────────────────────────

PROJECTS = [
    (
        "ClawdOS",
        "The web GUI & productivity workspace for OpenClaw — tasks, news, dashboards, package tracking, skill marketplace. Self-hosted & private.",
    ),
    (
        "completely",
        "Quality-first harness for autonomous AI coding agents — deterministic gates + a default-FAIL evaluator over a Beads task spine. Claude Code plugin; done is earned, not asserted.",
    ),
    (
        "frontend-quality",
        "Claude Code plugin: a frontend standard — taste decisions, layout checks in a real browser, a catalogue of failure modes, performance profiling attributed to functions.",
    ),
    (
        "site-teardown-skill",
        "Reverse engineers any website into a build blueprint: stack, effects, design tokens, section-by-section plan.",
    ),
]
ELSEWHERE = [
    ("23ag.one", "AI Products, Interfaces and the Systems Behind Them"),
    ("Lab", "Interface experiments made without a brief"),
    ("Telegram", ""),
    ("X", ""),
    ("Instagram", ""),
]
TAGLINE = "23AG builds AI products and the interfaces around them — decided, designed and built in one place, for founders and small teams."


def write(name, block):
    for theme, ink in THEMES.items():
        h = int(block.h + 0.999)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
            f'role="img" aria-label="{escape(block.alt)}"><g fill="{ink}">{block.body}</g></svg>\n'
        )
        (OUT / f"{name}-{theme}.svg").write_text(svg, encoding="utf-8")


def slug(s):
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")


def main():
    OUT.mkdir(exist_ok=True)
    write("tagline", tagline(TAGLINE))
    write("head-open-source", head("Open source"))
    for name, desc in PROJECTS:
        write(f"row-{slug(name)}", row(name, desc))
    write("head-last-12-months", head("Last 12 months"))
    write("year", year(fetch_calendar()))
    write("head-elsewhere", head("Elsewhere"))
    for name, desc in ELSEWHERE:
        write(f"row-{slug(name)}", row(name, desc))
    write("colophon", colophon())


if __name__ == "__main__":
    main()
