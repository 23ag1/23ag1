# 23ag1 — GitHub profile README

Repository `23ag1/23ag1`: its README.md is shown on github.com/23ag1.
The look is the 23ag.one signature ported to what a README allows.

## Stack

- Markdown + the HTML subset GitHub allows in READMEs.
- Hero: canvas page recorded with Playwright, packed to animated WebP (Pillow).
- Year: Python 3.12 + fontTools → static SVG, refreshed daily by an Action.

## Architecture

- `README.md` — hero, tagline, open-source list, year field, links.
- `scripts/hero/hero.html` — the site's "bigwm" canvas + ASCII flock,
  rewritten as a pure function of the frame number: "23AG" in Times New Roman
  Bold filled with symbols `* + · ✦ ⋆ ◦ ° ∘ : ✳ • ×`, symbol swaps and blinks,
  two rainbow glint passes and one flash per 9 s loop, 7 lanes of birds.
  Every event is laid out on the loop period, so the loop is seamless.
- `scripts/hero/record.mjs` → PNG frames (2x); `scripts/hero/pack.py` →
  `assets/hero-{dark,light}.webp`, lossless, 45 ms per frame like the site.
  Re-run by hand only when the design changes.
- `scripts/render.py` → `assets/year-{dark,light}.svg`: calendar via GraphQL,
  one symbol per day (`· ◦ + * ✦` by quartile), numbers in Times New Roman.
- `.github/workflows/hero.yml` — daily 03:17 UTC, manual dispatch, pushes to
  `scripts/**`; installs msttcorefonts; commits `assets/` only if changed.

## Conventions

- Width 846 = README column on desktop; 24 px margins on every side, nothing
  may touch the image edge (check alpha bbox of frames).
- Birds are drawn whole or not at all, like the site.
- Minimum text size 16. No monospace fonts: symbols come from DejaVu Sans.
- Dark/light via `<picture>` + `prefers-color-scheme`.
- No animated SVG: in `<img>` it repaints on the main thread every frame
  (measured: hero 73% of main thread at 4x CPU throttle). WebP decodes off it.
- Symbol swaps happen only on flock ticks (150 ms): scattered per-frame
  changes make every WebP frame full-size.
- Times New Roman is not redistributable: never commit the font file.

## Limits

- Hero WebP is ~5 MB per theme (lossless, 200 frames at 2x).
- On a phone everything scales to ~318 px; labels under numbers get small.
- Streaks are counted inside the last 12 months only.
- Local: `GITHUB_TOKEN=$(gh auth token) python3 scripts/render.py`;
  hero: `node scripts/hero/record.mjs /tmp/frames && python3 scripts/hero/pack.py /tmp/frames assets`.
