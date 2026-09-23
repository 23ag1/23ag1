"""Pack recorded frames into looping animated WebP: python pack.py <frames> <assets>

Lossless: flat symbols on transparency compress better than lossy (and stay
sharp). Frames are streamed, 200 RGBA frames at 2x won't fit in memory.
"""

import pathlib
import sys

from PIL import Image

frames, assets = map(pathlib.Path, sys.argv[1:3])
for theme in ("dark", "light"):
    n = len(list((frames / theme).glob("*.png")))
    rest = (Image.open(frames / theme / f"{i}.png") for i in range(1, n))
    Image.open(frames / theme / "0.png").save(
        assets / f"hero-{theme}.webp",
        save_all=True,
        append_images=rest,
        duration=45,  # the site's canvas ticks every 45 ms
        loop=0,
        lossless=True,
        quality=30,
        method=1,
    )
