"""Render the profile header: name, one line about me, and the real
contribution calendar for the last year. Writes assets/hero-{dark,light}.svg.

Runs daily from .github/workflows/hero.yml. Needs GITHUB_TOKEN (read-only
public data is enough). Fonts are embedded as subset woff2 so the SVG looks
the same inside GitHub's <img> sandbox, where external fonts can't load.
"""

import base64
import datetime as dt
import io
import json
import os
import pathlib
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont

LOGIN = "23ag1"
NAME = "AG"
TAGLINE = "AI builder. Making tools I want to use."

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "scripts" / "fonts"
OUT = ROOT / "assets"

# README column on github.com is ~846 CSS px wide: 1 SVG unit = 1 px on desktop.
W = 846
PAD = 27
CELL, GAP = 12, 3
STEP = CELL + GAP

PINK = "#DF769B"  # the avatar's pink
THEMES = {
    "dark": {
        "fg": "#E6EDF3",
        "muted": "#9198A1",
        "empty": "#1C2129",
        "levels": (0.4, 0.6, 0.8, 1.0),
    },
    "light": {
        "fg": "#1F2328",
        "muted": "#59636E",
        "empty": "#EFF2F5",
        "levels": (0.38, 0.6, 0.8, 1.0),
    },
}
LEVEL = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
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


def font_face(family, file, text):
    font = TTFont(FONTS / file)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "tnum", "lnum"]
    sub = subset.Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{family}';src:url(data:font/woff2;base64,{data}) format('woff2');}}"


def fmt(n):
    return f"{n:,}".replace(",", " ")  # thin space: 1 520


def plural(n, word):
    return f"{word}" if n == 1 else f"{word}s"


def render(cal, theme):
    t = THEMES[theme]
    weeks = cal["weeks"][-53:]
    days = [d for w in weeks for d in w["contributionDays"]]
    total = cal["totalContributions"]
    longest, current = streaks(days)

    stats = [
        (fmt(total), "contributions, last 12 months"),
        (str(longest), f"{plural(longest, 'day')}, longest streak"),
        (str(current), f"{plural(current, 'day')}, current streak"),
    ]

    display_text = NAME + "".join(v for v, _ in stats)
    body_text = TAGLINE + "".join(l for _, l in stats)

    grid_top = 176
    grid_h = 7 * STEP - GAP
    h = grid_top + grid_h + 90

    cells = []
    for wi, week in enumerate(weeks):
        for d in week["contributionDays"]:
            wd = (
                dt.date.fromisoformat(d["date"]).weekday() + 1
            ) % 7  # Sunday on top, as on GitHub
            lvl = LEVEL[d["contributionLevel"]]
            x, y = PAD + wi * STEP, grid_top + wd * STEP
            fill = t["empty"] if lvl == 0 else PINK
            op = "" if lvl == 0 else f' fill-opacity="{t["levels"][lvl - 1]}"'
            delay = f"{wi * 18 + wd * 6}ms"
            cells.append(
                f'<rect class="c" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{fill}"{op} '
                f'style="animation-delay:{delay}"><title>{d["date"]}: {d["contributionCount"]}</title></rect>'
            )

    stat_rows = []
    for i, (value, label) in enumerate(stats):
        x = PAD + i * 18 * STEP  # three columns on week 0, 18, 36 of the grid
        y = grid_top + grid_h + 50
        stat_rows.append(f'<text x="{x}" y="{y}" class="v">{value}</text><text x="{x}" y="{y + 26}" class="l">{label}</text>')

    css = (
        font_face("AG Display", "Unbounded-SemiBold.ttf", display_text)
        + font_face("AG Text", "GolosText-Regular.ttf", body_text)
        + f".n{{font:600 104px 'AG Display',sans-serif;fill:{t['fg']};letter-spacing:-4px}}"
        + f".t{{font:400 22px 'AG Text',sans-serif;fill:{t['muted']}}}"
        + f".v{{font:600 28px 'AG Display',sans-serif;fill:{t['fg']};font-variant-numeric:tabular-nums}}"
        + f".l{{font:400 16px 'AG Text',sans-serif;fill:{t['muted']}}}"
        + ".c{animation:in .5s cubic-bezier(.2,.7,.2,1) both}"
        + "@keyframes in{from{opacity:0;transform:translateY(4px)}}"
        + "@media (prefers-reduced-motion:reduce){.c{animation:none}}"
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{NAME} — {TAGLINE} {fmt(total)} contributions in the last year.">
<style>{css}</style>
<text x="{PAD - 6}" y="100" class="n">{NAME}</text>
<text x="{PAD}" y="142" class="t">{TAGLINE}</text>
{''.join(stat_rows)}
{''.join(cells)}
</svg>
"""


def main():
    cal = fetch_calendar()
    OUT.mkdir(exist_ok=True)
    for theme in THEMES:
        (OUT / f"hero-{theme}.svg").write_text(render(cal, theme), encoding="utf-8")


if __name__ == "__main__":
    main()
