#!/usr/bin/env python3
"""
Generate future SDF atlas from land/sea mask PNGs.

Input:  images/future/{50,100,150,200,250}.png  (RGBA, land=255 sea=0)
Output: images/future/future_sdf_atlas.png       (greyscale, 5 slices stacked)

All input images are resized to OUTPUT_SIZE before SDF generation. If your
source art is higher-resolution, use a larger OUTPUT_SIZE to preserve detail.

SDF encoding (matches existing past atlas convention):
  128 = coastline (zero distance)
  >128 = land interior (distance to coast scaled to [129..255])
  <128 = sea interior (distance to coast scaled to [127..0])
"""

import sys
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

# Output resolution per slice. Use 2048x1024 if source art was built at that
# resolution (or higher); 512x256 for legacy low-res sources.
OUTPUT_SIZE = (2048, 1024)   # (width, height)

# How many pixels from coast reach full saturation (0 or 255).
# Scale proportionally with OUTPUT_SIZE so the coast gradient spans the same
# fraction of the globe regardless of resolution.
# Baseline: SCALE_PX=30 at 512x256 → scale by width ratio.
SCALE_PX = 30.0 * OUTPUT_SIZE[0] / 512.0

TIMESTAMPS = [50, 100, 125, 150, 200, 225, 250]
INPUT_DIR  = 'images/future'
OUTPUT     = 'images/future/future_sdf_atlas.png'


def make_sdf_slice(path: str) -> np.ndarray:
    img  = Image.open(path).convert('L')
    if img.size != OUTPUT_SIZE:
        print(f'    (resizing {img.size} → {OUTPUT_SIZE})', end=' ')
        img = img.resize(OUTPUT_SIZE, Image.LANCZOS)
    gray = np.array(img, dtype=np.uint8)

    # Threshold: land=1, sea=0
    land = (gray >= 128).astype(np.uint8)

    dist_to_land = distance_transform_edt(1 - land)
    dist_to_coast_from_land = distance_transform_edt(land)
    sdf = np.where(land, dist_to_coast_from_land, -dist_to_land)

    scaled = 128.0 + (sdf / SCALE_PX) * 127.0
    clamped = np.clip(scaled, 0, 255).astype(np.uint8)

    return clamped  # shape (OUTPUT_SIZE[1], OUTPUT_SIZE[0])


def main():
    slices = []
    for t in TIMESTAMPS:
        path = f'{INPUT_DIR}/{t}.png'
        print(f'  Processing {t} Ma... ', end='', flush=True)
        sl = make_sdf_slice(path)
        print(f'land={(sl > 128).sum()} sea={(sl < 128).sum()} coast={(sl == 128).sum()}')
        slices.append(sl)

    atlas = np.vstack(slices)
    print(f'\nAtlas shape: {atlas.shape}  ({OUTPUT_SIZE[0]}×{OUTPUT_SIZE[1]*len(TIMESTAMPS)})')

    out = Image.fromarray(atlas, mode='L')
    out.save(OUTPUT)
    print(f'Saved: {OUTPUT}')

    import base64, io
    buf = io.BytesIO()
    out.save(buf, format='PNG', optimize=True)
    b64 = base64.b64encode(buf.getvalue())
    print(f'Base64 length: {len(b64):,} chars ({len(b64)//1024} KB)')


if __name__ == '__main__':
    main()
