# 23ag1 — GitHub profile README

Repository `23ag1/23ag1`: its README.md is shown on github.com/23ag1.
The look is the 23ag.one signature ported to what a README allows.

## Stack

- Markdown + the HTML subset GitHub allows in READMEs.
- Hero: canvas page recorded with Playwright, packed to animated WebP (ffmpeg).
- Text + year: Python 3.12 + fontTools → static SVGs, refreshed daily by an Action.

## Architecture

- `README.md` — only `<picture>` blocks (dark/light), each row wrapped in its
  link: hero, tagline, "Open source" + 4 project rows, "Last 12 months" +
  year, "Elsewhere" + 5 link rows, colophon. Markdown can't set a font, so all
  text is Times New Roman outlines; alt text carries the words.
- `scripts/hero/hero.html` — the site's sky row as it lays out on a phone,
  compacted: 7 ASCII birds on top (16 px, one per row, spread evenly over the
  full width, one direction and speed so they never bunch; whole birds only), "bigwm" below at full width — symbols on a grid of
  height/30 (site: /22, denser here so the word reads heavier) masked to
  "23AG" in Times New Roman Bold. 4 glint passes per 21.6 s loop; each pass
  reshuffles the symbols it sweeps over; 3 colour flashes. Seamless loop.
- `scripts/hero/record.mjs` → PNG frames (2x); `scripts/hero/pack.py` (ffmpeg)
  → `assets/hero-{dark,light}.webp`, lossless, 45 ms frames like the site.
  Re-run by hand only when the design changes.
- `scripts/render.py` → every text block + the year (GraphQL calendar, one
  symbol per day `· ◦ + * ✦`). Set like the site's CSS: `.tagline`, `.block__h`,
  `.svc` (bold underlined name, → at .35, description at .55); ASCII instead
  of rules: `-·-` rows for block tops, `·` rows for hairlines. Kerning from TNR.
- `.github/workflows/hero.yml` — daily 03:17 UTC, manual dispatch, pushes to
  `scripts/**`; installs msttcorefonts; commits `assets/` only if changed.

## Conventions

- Width 846 = README column on desktop; 24 px margins on every side, nothing
  may touch the image edge (check alpha bbox of frames).
- Birds are drawn whole or not at all, like the site.
- Minimum text size 16 (desktop). Times New Roman everywhere — the owner's explicit choice
  for this page; symbols from DejaVu Sans.
- Dark/light via `<picture>` + `prefers-color-scheme`.
- No animated SVG: in `<img>` it repaints on the main thread every frame
  (measured: hero 73% of main thread at 4x CPU throttle). WebP decodes off it.
- WebP weight = changed area per frame. Keep changes local: symbols swap only
  inside the glint band, hue is fixed per pass, alpha is constant. Random swaps
  over the whole word doubled the file (9 MB).
- Times New Roman is not redistributable: never commit the font file.

## Limits

- Hero WebP is ~5 MB per theme (lossless, 480 frames at 2x).
- On a phone every image scales to ~318 px: all text shrinks to ~6 px.
- Streaks are counted inside the last 12 months only.
- Local: `GITHUB_TOKEN=$(gh auth token) python3 scripts/render.py`;
  hero: `node scripts/hero/record.mjs /tmp/frames && python3 scripts/hero/pack.py /tmp/frames assets`.
