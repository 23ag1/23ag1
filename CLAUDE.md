# 23ag1 — GitHub profile README

Repository `23ag1/23ag1`: its README.md is shown on github.com/23ag1.
The look is the 23ag.one signature ported to what a README allows.

## Stack

- Markdown + the HTML subset GitHub allows in READMEs.
- Python 3.12 + fontTools, brotli, Pillow for the generated SVGs.
- GitHub Actions for the daily refresh.

## Architecture

- `README.md` — hero, status line, tagline, open-source list, year field,
  links. All text is real Markdown except numbers that must update daily.
- `scripts/render.py` writes:
  - `assets/hero-{dark,light}.svg` — "23AG" (Liberation Serif Bold = Times
    metrics, as on the site) filled with a field of symbols `* + · ✦ ⋆ ◦ ° ∘ : ✳ • ×`;
    cells twinkle (CSS), some swap symbols (SMIL `href`), a rainbow glint
    sweeps through (masked moving gradient), a full-colour flash every 11 s,
    and a flock of ASCII birds `\·/ ~·~ -·- /·\` flapping across the sky.
    Fixed random seed, so daily runs don't churn it.
  - `assets/year-{dark,light}.svg` — contribution calendar via GraphQL, one
    symbol per day (`· ◦ + * ✦` by quartile), same glint, three numbers.
  - `assets/dot.svg` — pulsing green status dot.
- `scripts/fonts/` — subsets of Liberation Serif Bold, DejaVu Sans (symbols
  only) and Golos Text, with licences. Glyphs become outline paths; Golos is
  embedded as woff2 for the 16 px labels. `<img>` SVGs can't load fonts or JS.
- `.github/workflows/hero.yml` — daily 03:17 UTC, manual dispatch, and on
  pushes to `scripts/**`; commits `assets/` only if it changed.

## Conventions

- SVG width 846 = README column on desktop, 1 unit = 1 CSS px.
- Minimum text size 16. No monospace fonts: symbols are drawn as paths.
- Dark/light via `<picture>` + `prefers-color-scheme`.
- No third-party badge services — the old ones died (readme-stats 503,
  activity-graph 402) and left broken images.
- `prefers-reduced-motion` stops every animation.

## Limits

- On a phone the SVGs scale to ~318 px: the word and field still read, the
  16 px labels under the numbers become small. Everything else is Markdown.
- Streaks are counted inside the last 12 months only.
- Run locally: `GITHUB_TOKEN=$(gh auth token) python3 scripts/render.py`.
