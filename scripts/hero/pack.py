"""Pack recorded frames into looping animated WebP: python pack.py <frames> <assets>

ffmpeg, lossless: flat symbols on transparency compress better lossless than
lossy and stay sharp, and ffmpeg streams frames (Pillow runs out of memory on
480 frames at 2x). Identical neighbours are merged into longer frames.
"""

import pathlib
import subprocess
import sys

frames, assets = map(pathlib.Path, sys.argv[1:3])
for theme in ("dark", "light"):
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-framerate", "200/9",  # 45 ms per frame, the site's canvas tick
            "-i", str(frames / theme / "%d.png"),
            "-c:v", "libwebp_anim", "-lossless", "1", "-compression_level", "1",
            "-pix_fmt", "bgra", "-loop", "0",
            str(assets / f"hero-{theme}.webp"),
        ],
        check=True,
    )
