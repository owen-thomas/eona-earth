#!/usr/bin/env python3
"""
Generate future SDF atlas from land/sea mask PNGs.

Input:  images/future/{50,100,150,200,250}.png  (512×256 RGBA, land=255 sea=0)
Output: images/future/future_sdf_atlas.png       (512×1280 greyscale, 5 slices stacked)

SDF encoding (matches existing past atlas convention):
  128 = coastline (zero distance)
  >128 = land interior (distance to coast scaled to [129..255])
  <128 = sea interior (distance to coast scaled to [127..0])
"""

import sys
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

# How many pixels from coast reach full saturation (0 or 255).
# The past atlas used ~30px clamping range empirically.
SCALE_PX = 30.0

TIMESTAMPS = [50, 100, 150, 200, 250]
INPUT_DIR  = 'images/future'
OUTPUT     = 'images/future/future_sdf_atlas.png'


def make_sdf_slice(path: str) -> np.ndarray:
    img  = Image.open(path).convert('L')   # greyscale
    gray = np.array(img, dtype=np.uint8)

    # Threshold: land=1, sea=0
    land = (gray >= 128).astype(np.uint8)

    # Distance from every sea pixel to nearest land pixel
    dist_to_land = distance_transform_edt(1 - land)   # EDT of sea mask
    # Distance from every land pixel to nearest sea pixel
    dist_to_coast_from_land = distance_transform_edt(land)

    # Signed distance: positive inside land, negative in sea
    # (land pixels → positive distance, sea pixels → negative distance)
    sdf = np.where(land, dist_to_coast_from_land, -dist_to_land)

    # Scale to [0, 255] around 128
    scaled = 128.0 + (sdf / SCALE_PX) * 127.0
    clamped = np.clip(scaled, 0, 255).astype(np.uint8)

    return clamped  # shape (256, 512)


def main():
    slices = []
    for t in TIMESTAMPS:
        path = f'{INPUT_DIR}/{t}.png'
        print(f'  Processing {t} Ma... ', end='', flush=True)
        sl = make_sdf_slice(path)
        print(f'land={( sl > 128).sum()} sea={(sl < 128).sum()} coast={(sl == 128).sum()}')
        slices.append(sl)

    atlas = np.vstack(slices)          # (1280, 512) uint8
    print(f'\nAtlas shape: {atlas.shape}')

    out = Image.fromarray(atlas, mode='L')
    out.save(OUTPUT)
    print(f'Saved: {OUTPUT}')

    # Print base64 size estimate
    import base64, io
    buf = io.BytesIO()
    out.save(buf, format='PNG', optimize=True)
    b64 = base64.b64encode(buf.getvalue())
    print(f'Base64 length: {len(b64):,} chars ({len(b64)//1024} KB)')


if __name__ == '__main__':
    main()
