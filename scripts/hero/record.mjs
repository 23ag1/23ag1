// Records hero.html into PNG frames: node record.mjs <outdir>
// Then scripts/hero/pack.py packs them into assets/hero-{dark,light}.webp.
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const out = process.argv[2] || 'frames';
const here = path.dirname(new URL(import.meta.url).pathname);
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto('file://' + path.join(here, 'hero.html'));
await page.evaluate(() => document.fonts.ready);
const { FRAMES } = await page.evaluate(() => window.SIZE);
for (const theme of ['dark', 'light']) {
  fs.mkdirSync(path.join(out, theme), { recursive: true });
  for (let f = 0; f < FRAMES; f++) {
    const data = await page.evaluate(([f, theme]) => { window.draw(f, theme); return document.getElementById('c').toDataURL('image/png'); }, [f, theme]);
    fs.writeFileSync(path.join(out, theme, `${f}.png`), Buffer.from(data.split(',')[1], 'base64'));
  }
}
await browser.close();
