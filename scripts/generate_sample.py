#!/usr/bin/env python3
"""
Generates assets/sample.jpg during the Docker build.
Run after Pillow is installed.
"""
from pathlib import Path
from PIL import Image, ImageDraw

W, H = 576, 864

img = Image.new("RGB", (W, H))
draw = ImageDraw.Draw(img)

# Gradient background (dark blue-purple, typical photobooth backdrop)
for y in range(H):
    t = y / H
    r = int(30 + 60 * t)
    g = int(20 + 50 * t)
    b = int(80 + 60 * t)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# Simple person silhouette — head
draw.ellipse([(W // 2 - 70, 60), (W // 2 + 70, 200)], fill=(245, 210, 175))
# Neck
draw.rectangle([(W // 2 - 25, 195), (W // 2 + 25, 240)], fill=(245, 210, 175))
# Body/shirt
draw.ellipse([(W // 2 - 130, 220), (W // 2 + 130, 580)], fill=(55, 90, 160))
# Eyes
draw.ellipse([(W // 2 - 28, 115), (W // 2 - 8, 140)], fill=(50, 35, 20))
draw.ellipse([(W // 2 + 8, 115), (W // 2 + 28, 140)], fill=(50, 35, 20))
# Smile
draw.arc([(W // 2 - 30, 148), (W // 2 + 30, 185)], 10, 170, fill=(120, 60, 40), width=4)

# Decorative corner flourishes
for corner in [(0, 0), (W - 60, 0), (0, H - 60), (W - 60, H - 60)]:
    draw.rectangle([corner, (corner[0] + 50, corner[1] + 50)],
                   outline=(255, 220, 80), width=4)

# Frame border
draw.rectangle([(8, 8), (W - 8, H - 8)], outline=(255, 255, 255), width=5)

# Footer bar with event text
draw.rectangle([(0, H - 130), (W, H)], fill=(15, 15, 35, 230))
# Simple white text blocks (no font file required)
draw.rectangle([(W // 2 - 100, H - 110), (W // 2 + 100, H - 90)], fill=(255, 255, 255))
draw.rectangle([(W // 2 - 70, H - 80), (W // 2 + 70, H - 65)], fill=(180, 180, 210))
draw.rectangle([(W // 2 - 45, H - 55), (W // 2 + 45, H - 42)], fill=(120, 120, 170))

# Star / bokeh decoration
import math
for i in range(12):
    angle = math.pi * 2 * i / 12
    cx = int(W / 2 + 200 * math.cos(angle))
    cy = int(H / 2 + 260 * math.sin(angle))
    r = 6 + (i % 3) * 4
    if 0 <= cx < W and 0 <= cy < H:
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)],
                     fill=(255, 200, 80, 120))

out = Path("/app/assets/sample.jpg")
out.parent.mkdir(parents=True, exist_ok=True)
img.save(str(out), quality=92)
print(f"Generated {out} ({W}x{H})")
