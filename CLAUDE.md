# 23ag1 — GitHub profile README

Repository `23ag1/23ag1`: its README.md is shown on github.com/23ag1.

## Stack

- Markdown + HTML subset that GitHub allows in READMEs.
- Python 3.12 + fontTools (+ brotli for woff2) for the generated header.
- GitHub Actions for the daily refresh.

## Architecture

- `README.md` — header picture, projects, tools, links. Everything except the
  header is plain text on purpose: readable on mobile, selectable, no services.
- `scripts/render.py` — pulls the contribution calendar via GraphQL and writes
  `assets/hero-dark.svg` and `assets/hero-light.svg`.
- `scripts/fonts/` — static, Latin-subset instances of Unbounded SemiBold and
  Golos Text (OFL licences alongside). Render subsets them again to the exact
  glyphs used and embeds them as base64 woff2 — GitHub shows SVG through
  `<img>`, where external fonts cannot load.
- `.github/workflows/hero.yml` — daily at 03:17 UTC, on manual dispatch and on
  pushes to `scripts/**`; commits `assets/` only if it changed.

## Conventions

- Colour: avatar pink `#DF769B`; grey tokens follow GitHub's own dark/light
  palette so the header sits on the page without a box.
- SVG width 846 = README column width on desktop, 1 unit = 1 CSS px.
  Minimum text size 16. No monospace fonts anywhere.
- Dark/light switch through `<picture>` + `prefers-color-scheme`.
- No third-party badge services: the old ones died (readme-stats 503,
  activity-graph 402) and left broken images.

## Limits

- On a phone the header scales down to ~318 px, so its 16 px labels become
  ~6 px. The numbers and grid stay legible; the text below is real Markdown.
- Streaks are counted inside the last 12 months only (calendar window).
- Run locally: `GITHUB_TOKEN=$(gh auth token) python3 scripts/render.py`.
