# 2D Panoramic Strip — Migration Guide

Replace the Three.js WebGL sphere with a 2D Canvas rendering pipeline that uses the
existing SDF atlas and visual states directly, scrolled horizontally behind a circular
mask. All clock logic, eon ring, event markers, scrubber, and info panel are untouched.

---

## Branch First

```bash
git checkout -b feature/2d-panoramic
```

Work entirely on this branch. `main` stays at the last working WebGL version. Only
merge when Step 11 (regression testing) passes cleanly. If anything goes badly wrong,
`git checkout main` puts you back at a known-good state in seconds.

---

## What Changes vs. What Stays

### Unchanged
- Everything outside `#earth-layer` and the WebGL initialisation block
- `timeToMa`, `maToAngle`, `getVisualState`, `getSdfBlend`, `getCurrentEon`
- All STATES data (colours, thresholds, haze, glow values)
- All EONS / LIFE / EVENTS data
- `#haze-layer`, `#dark-haze-layer`, `#earth-shadow` — same CSS, same JS update logic
- Atmospheric glow (`filter: drop-shadow`) — same interpolation, same per-state values
- `updateEarth()` entry point — still called every frame; rewritten internally
- The `--earth-size` and `--earth-canvas-size` CSS variables

### Removed
- `<script src="three.js">` CDN import
- Three.js scene, camera, renderer, geometry, ShaderMaterial
- The GLSL fragment shader (~200 lines)
- SDF atlas as a Three.js `DataTexture`

### Added
- Canvas 2D rendering pipeline (~150 lines) replacing the shader
- A noise atlas (base64 PNG, 512 × 3072) pre-baked from the existing GLSL shader
- Both atlases decoded once into `ImageData` objects at startup
- A `scrollOffset` variable driven by the same rotation logic as `mesh.rotation.y`

---

## Conceptual Model

Two flat atlases drive the entire render:

**SDF atlas** (existing) — 512 × 2816 px, 11 slices at fixed paleogeographic timestamps
(635 Ma → 0 Ma). Used for states 11–14 (Cryogenian through Modern Earth).

**Noise atlas** (new, pre-baked) — 512 × 3072 px, 12 slices, one per procedural STATES
entry (indices 0–11, Molten Hadean through Cryogenian Snowball). Each slice is a
greyscale image of the fBm noise field for that state's `seed` and `surfaceIntensity`,
frozen at a fixed noise offset. Greyscale value maps directly to the noise output the
GLSL shader would have produced.

Both atlases are treated identically at render time: sample a pixel, get a value (0–255),
threshold against `noiseThresh1`/`noiseThresh2` to assign `c1`/`c2`/`c3`, blend between
adjacent states with the same `sdfBlend` factor already computed by `getSdfBlend()`.

```
Noise atlas slice [512 × 256]   SDF atlas slice [512 × 256]
       ↓                                  ↓
  threshold → c1/c2/c3             threshold → c1/c2/c3
       ↓                                  ↓
       └──── blended by sdfBlend ─────────┘
                    ↓
             scroll by scrollOffset (wraps at 512)
                    ↓
         draw onto canvas, clipped to circle
                    ↓
         haze + glow applied as CSS (unchanged)
```

For state 11 (Cryogenian, `useLandSea: 0.35`), both atlases contribute: the final pixel
value is `noiseValue * 0.65 + sdfValue * 0.35` before thresholding. All other procedural
states use noise atlas only. All states from 12 onward use SDF atlas only.

---

## Step 1 — Pre-Bake the Noise Atlas

This is a one-time offline step. The output is a single base64 PNG string that you paste
into `deeptime.html` alongside the existing `base64SdfAtlas` constant.

### Which states need baking

| STATES index | Name | useLandSea | Needs bake |
|---|---|---|---|
| 0 | Molten Hadean (early) | 0 | ✓ |
| 1 | Molten Hadean (late) | 0 | ✓ |
| 2 | Steam World | 0 | ✓ |
| 3 | Hazy Archean (early) | 0 | ✓ |
| 4 | Hazy Archean (late) | 0 | ✓ |
| 5 | Great Oxidation (early) | 0 | ✓ |
| 6 | Great Oxidation (late) | 0 | ✓ |
| 7 | Huronian Snowball | 0 | ✓ |
| 8 | Boring Billion (early) | 0 | ✓ |
| 9 | Boring Billion (mid) | 0 | ✓ |
| 10 | Boring Billion (late) | 0 | ✓ |
| 11 | Cryogenian Snowball | 0.35 | ✓ (noise component) |
| 12–14 | Hothouse → Modern | 1.0 | ✗ (SDF only) |

12 slices total. Atlas output: 512 × (256 × 12) = 512 × 3072 px.

### The bake script

Create `bake-noise-atlas.html` as a standalone file — open it in a browser, click Bake,
download `noise-atlas.png`. This is not part of the main application; discard after use.

The script re-uses the existing `fbm()` / `noise3D()` GLSL functions from the shader,
renders each state to a 512 × 256 offscreen WebGL canvas, then stitches the slices into
a single tall PNG.

```html
<!DOCTYPE html>
<html>
<head><title>Noise Atlas Baker</title></head>
<body>
<button id="bake">Bake noise atlas</button>
<p id="status"></p>
<canvas id="gl" width="512" height="256" style="display:none"></canvas>
<canvas id="out" width="512" height="3072" style="display:none"></canvas>
<script>

// ── Copy these constants verbatim from deeptime.html ──────────────────────
// STATES array (indices 0–11 only — the 12 procedural entries)
const STATES = [ /* … paste from deeptime.html … */ ];

// ── GLSL source ────────────────────────────────────────────────────────────
// The fragment shader renders a single flat equirectangular pass.
// No sphere projection, no SDF, no clouds, no blending.
// Output: greyscale where 1.0 = max noise, 0.0 = min noise.
// noiseThresh1 / noiseThresh2 are NOT applied here — raw noise value only.

const VERT = `
  attribute vec2 a_pos;
  varying vec2 v_uv;
  void main() {
    v_uv = a_pos * 0.5 + 0.5;
    gl_Position = vec4(a_pos, 0.0, 1.0);
  }
`;

const FRAG = `
  precision highp float;
  varying vec2 v_uv;
  uniform float u_seed;
  uniform float u_surfaceIntensity;

  // ── Paste fbm / noise3D from deeptime.html exactly ──────────────────

  void main() {
    // Equirectangular → sphere surface normal
    float lon = (v_uv.x * 2.0 - 1.0) * 3.14159265;
    float lat = (v_uv.y * 2.0 - 1.0) * 1.5707963;
    vec3 p = vec3(cos(lat) * cos(lon), sin(lat), cos(lat) * sin(lon));

    // Same noise evaluation as the shader surface path
    vec3 noisePos = p + vec3(u_seed * 7.3, u_seed * 3.1, u_seed * 5.7);
    float n = fbm(noisePos * 2.5);
    n = clamp(n / 0.9375, 0.0, 1.0); // normalise fbm range to [0,1]
    n = mix(0.5, n, u_surfaceIntensity); // apply surfaceIntensity

    gl_FragColor = vec4(n, n, n, 1.0);
  }
`;

document.getElementById('bake').addEventListener('click', async () => {
  const status   = document.getElementById('status');
  const glCanvas = document.getElementById('gl');
  const gl       = glCanvas.getContext('webgl', { preserveDrawingBuffer: true });

  const vert = compileShader(gl, gl.VERTEX_SHADER,   VERT);
  const frag = compileShader(gl, gl.FRAGMENT_SHADER, FRAG);
  const prog = gl.createProgram();
  gl.attachShader(prog, vert);
  gl.attachShader(prog, frag);
  gl.linkProgram(prog);
  gl.useProgram(prog);

  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER,
    new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
  const aPos = gl.getAttribLocation(prog, 'a_pos');
  gl.enableVertexAttribArray(aPos);
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

  const uSeed      = gl.getUniformLocation(prog, 'u_seed');
  const uIntensity = gl.getUniformLocation(prog, 'u_surfaceIntensity');

  const outCanvas = document.getElementById('out');
  const outCtx    = outCanvas.getContext('2d');

  for (let i = 0; i < 12; i++) {
    const s = STATES[i];
    gl.uniform1f(uSeed,      s.seed);
    gl.uniform1f(uIntensity, s.surfaceIntensity);
    gl.viewport(0, 0, 512, 256);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

    const pixels = new Uint8Array(512 * 256 * 4);
    gl.readPixels(0, 0, 512, 256, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    const slice = new ImageData(new Uint8ClampedArray(pixels), 512, 256);
    outCtx.putImageData(slice, 0, i * 256);

    status.textContent = `Baked ${i + 1} / 12 — ${s.name}`;
    await new Promise(r => setTimeout(r, 0)); // yield to repaint
  }

  outCanvas.toBlob(blob => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'noise-atlas.png';
    a.click();
    status.textContent = 'Done. Convert to base64 and paste into deeptime.html.';
  });
});

function compileShader(gl, type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS))
    throw new Error(gl.getShaderInfoLog(s));
  return s;
}

</script>
</body>
</html>
```

### Embedding the result

After downloading `noise-atlas.png`, convert to base64 and embed:

```bash
# macOS / Linux
base64 -i noise-atlas.png | tr -d '\n' > noise-atlas.b64
```

In `deeptime.html`, alongside the existing atlas constant:

```js
const base64SdfAtlas   = '…'; // existing, unchanged
const base64NoiseAtlas = '…'; // new — paste noise-atlas.b64 content here
```

The noise atlas PNG is typically 80–150 KB before base64 encoding (12 greyscale slices,
good PNG compression). Acceptable as an inline constant.

### Bake gotchas

**Orientation must match the SDF atlas.** The equirectangular → sphere mapping in the
bake shader must produce the same north/south and east/west orientation as the SDF
atlas. Verify by comparing the Cryogenian noise slice (index 11) against the Cryogenian
SDF slice (index 10 of the SDF atlas, at 635 Ma) — they should blend continuously
rather than flipping geography at the transition.

**`surfaceIntensity` must be applied identically.** The shader uses
`mix(0.5, n, surfaceIntensity)`. Snowball states (7, 11) use 0.28–0.32 — their baked
slices will look nearly flat mid-grey, which is correct.

**Noise drift is intentionally dropped.** The original shader animates a slow noise
drift (`sOff += vec3(time * 0.004, …)`). The bake freezes noise at `time = 0`. The
horizontal scrolling of the panoramic strip provides equivalent visual interest. If you
want subtle surface shimmer later, re-introduce it as a slow independent UV offset
applied to the noise atlas at render time, separate from `scrollOffset`.

---

## Step 2 — Remove Three.js

Delete or comment out:

1. The Three.js CDN `<script>` tag
2. The entire `// === WebGL Earth ===` block — scene, camera, renderer, geometry,
   ShaderMaterial, GLSL source strings, texture setup, `mesh`, `animate()` WebGL loop
3. The SDF atlas `DataTexture` creation code
4. `renderer.setAnimationLoop(animate)`

Keep both `base64SdfAtlas` and `base64NoiseAtlas` strings.

---

## Step 3 — Decode Both Atlases

At startup (after DOMContentLoaded), decode both atlases into reusable pixel buffers.
Do this once; both are accessed every frame.

```js
let sdfImageData   = null;
let noiseImageData = null;

function decodeAtlas(base64) {
  return new Promise(resolve => {
    const img = new Image();
    img.onload = () => {
      const offscreen = document.createElement('canvas');
      offscreen.width  = img.naturalWidth;
      offscreen.height = img.naturalHeight;
      offscreen.getContext('2d').drawImage(img, 0, 0);
      resolve(offscreen.getContext('2d').getImageData(
        0, 0, img.naturalWidth, img.naturalHeight
      ));
    };
    img.src = 'data:image/png;base64,' + base64;
  });
}

// In init:
[sdfImageData, noiseImageData] = await Promise.all([
  decodeAtlas(base64SdfAtlas),
  decodeAtlas(base64NoiseAtlas),
]);
```

---

## Step 4 — Scroll Offset

Replace `mesh.rotation.y` with a plain JS variable:

```js
let scrollOffset = 0; // 0–511, wraps at 512

// pixels/second: one full 512px wrap per 900s (= 4 rotations/hour)
// matches original: Math.PI*2/900 rad/s × 512/(2π) px/rad
const SCROLL_SPEED = 512 / 900;

// In the main render loop:
scrollOffset = (scrollOffset + SCROLL_SPEED * deltaTime) % 512;
```

During globe-only drag (not time scrub), accumulate `scrub.rotationOffset` into
`scrollOffset` the same way the original applies it to `mesh.rotation.y`.

---

## Step 5 — Atlas Sampling Helper

Both atlases are sampled identically. A shared helper avoids duplication:

```js
// Returns 0–255 from the R channel of imageData at (lonFrac, latFrac) in slice index
function sampleAtlas(imageData, index, lonFrac, latFrac) {
  const ATLAS_W = imageData.width;  // 512
  const SLICE_H = 256;
  const sx = Math.floor(((lonFrac % 1 + 1) % 1) * ATLAS_W); // handles negative wrap
  const sy = Math.min(
    Math.floor(index * SLICE_H + latFrac * SLICE_H),
    imageData.height - 1
  );
  return imageData.data[(sy * ATLAS_W + sx) * 4]; // R channel
}
```

---

## Step 6 — 2D Render Function

Replaces `renderer.render(scene, camera)`. Called once per frame from `updateEarth()`.

```js
const earthCanvas = document.getElementById('earth-canvas');
const earthCtx    = earthCanvas.getContext('2d');
const bufCanvas   = document.createElement('canvas');
const bufCtx      = bufCanvas.getContext('2d');

function renderEarth2D(ma) {
  const { a, b, blend } = getVisualState(ma);
  const { indexA, indexB, blend: sdfBlend } = getSdfBlend(ma);

  const W = earthCanvas.width;
  const H = earthCanvas.height;
  if (bufCanvas.width !== W || bufCanvas.height !== H) {
    bufCanvas.width  = W;
    bufCanvas.height = H;
  }

  const R  = W / 2;
  const cx = R;
  const cy = R;

  // Pre-parse per-frame constants (avoid per-pixel object creation)
  const c1A = a.c1rgb, c2A = a.c2rgb, c3A = a.c3rgb;
  const c1B = b.c1rgb, c2B = b.c2rgb, c3B = b.c3rgb;
  const t1A = a.noiseThresh1 * 255, t2A = a.noiseThresh2 * 255;
  const t1B = b.noiseThresh1 * 255, t2B = b.noiseThresh2 * 255;

  const buf = bufCtx.createImageData(W, H);
  const out = buf.data;

  for (let py = 0; py < H; py++) {
    for (let px = 0; px < W; px++) {

      const nx = (px - cx) / R;
      const ny = (py - cy) / R;
      if (nx * nx + ny * ny > 1.0) continue; // circular mask

      // Equirectangular coordinates (full 360° across strip width)
      const lonFrac = (nx + 1) / 2 + scrollOffset / 512;
      const latFrac = 1.0 - (ny + 1) / 2; // top = north

      // ── Sample state A ───────────────────────────────────────────────
      let valA;
      if (a.useLandSea >= 1.0) {
        valA = sampleAtlas(sdfImageData, indexA, lonFrac, latFrac);
      } else if (a.useLandSea <= 0.0) {
        valA = sampleAtlas(noiseImageData, indexA, lonFrac, latFrac);
      } else {
        // Hybrid (Cryogenian): noise + SDF
        const noise = sampleAtlas(noiseImageData, indexA, lonFrac, latFrac);
        const sdf   = sampleAtlas(sdfImageData,   indexA, lonFrac, latFrac);
        valA = noise * (1 - a.useLandSea) + sdf * a.useLandSea;
      }

      // ── Sample state B ───────────────────────────────────────────────
      let valB;
      if (b.useLandSea >= 1.0) {
        valB = sampleAtlas(sdfImageData, indexB, lonFrac, latFrac);
      } else if (b.useLandSea <= 0.0) {
        valB = sampleAtlas(noiseImageData, indexB, lonFrac, latFrac);
      } else {
        const noise = sampleAtlas(noiseImageData, indexB, lonFrac, latFrac);
        const sdf   = sampleAtlas(sdfImageData,   indexB, lonFrac, latFrac);
        valB = noise * (1 - b.useLandSea) + sdf * b.useLandSea;
      }

      // ── Colour assignment (mirrors shader: c3 base, c2 mid, c1 top) ─
      const colA = valA > t2A ? c1A : (valA > t1A ? c2A : c3A);
      const colB = valB > t2B ? c1B : (valB > t1B ? c2B : c3B);

      // ── Blend A → B ──────────────────────────────────────────────────
      const i = (py * W + px) * 4;
      out[i]     = Math.round(colA[0] * (1 - blend) + colB[0] * blend);
      out[i + 1] = Math.round(colA[1] * (1 - blend) + colB[1] * blend);
      out[i + 2] = Math.round(colA[2] * (1 - blend) + colB[2] * blend);
      out[i + 3] = 255;
    }
  }

  bufCtx.putImageData(buf, 0, 0);

  // Draw to main canvas, clipped to disc
  earthCtx.clearRect(0, 0, W, H);
  earthCtx.save();
  earthCtx.beginPath();
  earthCtx.arc(cx, cy, R, 0, Math.PI * 2);
  earthCtx.clip();
  earthCtx.drawImage(bufCanvas, 0, 0);
  earthCtx.restore();
}
```

> **Note on `getSdfBlend` index reuse:** `getSdfBlend()` returns atlas indices into the
> SDF atlas (0–10). The noise atlas uses the same index values mapped against STATES
> entries 0–11. Confirm this is consistent at the noise → SDF boundary (state 11 → 12)
> to ensure `indexA` and `indexB` are being routed to the correct atlas.

---

## Step 7 — Integrate into `updateEarth()`

```js
let lastFrameTime = performance.now();

function updateEarth() {
  const now = performance.now();
  const dt  = (now - lastFrameTime) / 1000;
  lastFrameTime = now;

  const { h, m, s } = getCurrentTime();
  const ma = scrub.active ? scrub.ma : timeToMa(h, m, s);

  if (!scrub.draggingGlobe) {
    scrollOffset = (scrollOffset + SCROLL_SPEED * dt) % 512;
  }

  renderEarth2D(ma);

  // Unchanged from original:
  updateHaze(ma);
  updateGlow(ma);
  updateDarkHaze(ma);
}
```

---

## Step 8 — Canvas Sizing

Same as before — the 25% buffer is still needed for the atmospheric glow.

```js
function resizeEarthCanvas() {
  const earthSize  = parseFloat(getComputedStyle(document.documentElement)
                       .getPropertyValue('--earth-size'));
  const canvasSize = Math.round(earthSize * 1.25);
  earthCanvas.width  = canvasSize;
  earthCanvas.height = canvasSize;
  bufCanvas.width    = canvasSize;
  bufCanvas.height   = canvasSize;
}

window.addEventListener('resize', resizeEarthCanvas);
resizeEarthCanvas();
```

---

## Step 9 — Colour Parsing

Pre-parse `c1rgb`–`c3rgb` on each STATES entry alongside the existing `hazeRgb` /
`glowRgb` / `darkHazeRgb` pass:

```js
STATES.forEach(s => {
  s.c1rgb = hexToRgb(s.palette[1]); // land
  s.c2rgb = hexToRgb(s.palette[2]); // ocean primary
  s.c3rgb = hexToRgb(s.palette[3]); // ocean deep
  // c0 (atmosphere) and c4 (silhouette) not needed in the 2D pipeline
});
```

---

## Step 10 — Stylistic Passes

Optional Canvas 2D compositing layers applied after the base render.

### Grain overlay

```js
// Pre-generate once at startup via SVG feTurbulence → canvas
const grainCanvas = generateGrainTexture(512, 512);

// In renderEarth2D, after putImageData, inside the arc clip:
earthCtx.globalAlpha = 0.10;
earthCtx.globalCompositeOperation = 'overlay';
const grainX = (scrollOffset * 0.3) % 512; // parallax offset
earthCtx.drawImage(grainCanvas, -grainX,         0, 512, H);
earthCtx.drawImage(grainCanvas, 512 - grainX,    0, 512, H); // wrap seam
earthCtx.globalCompositeOperation = 'source-over';
earthCtx.globalAlpha = 1.0;
```

### Limb darkening / vignette

```js
// Last pass before earthCtx.restore():
const vig = earthCtx.createRadialGradient(cx, cy, R * 0.55, cx, cy, R);
vig.addColorStop(0,    'rgba(0,0,0,0)');
vig.addColorStop(0.75, 'rgba(0,0,0,0)');
vig.addColorStop(1.0,  'rgba(0,0,0,0.6)');
earthCtx.globalCompositeOperation = 'multiply';
earthCtx.fillStyle = vig;
earthCtx.beginPath();
earthCtx.arc(cx, cy, R, 0, Math.PI * 2);
earthCtx.fill();
earthCtx.globalCompositeOperation = 'source-over';
```

---

## Step 11 — Regression Checklist

Work through this before merging to `main`:

- [ ] All three layer toggles (Earth, Eons, Clock) show/hide correctly
- [ ] Haze colour and opacity transition correctly across all 14 state boundaries
- [ ] Atmospheric glow present on Molten Hadean, fades through Steam World, absent elsewhere
- [ ] Dark haze wipe tracks the hour position correctly
- [ ] Scrubber drag changes geological time; globe scrolls to match
- [ ] Globe-only drag scrolls the strip without moving the handle
- [ ] Return to now restores live time and scroll speed
- [ ] Snowball states (Huronian, Cryogenian) appear nearly flat/white as expected
- [ ] Cryogenian → Hothouse transition shows continent shapes emerging (useLandSea ramp)
- [ ] Modern Earth shows recognisable continents
- [ ] Strip wraps cleanly — no visible seam at the 0/512 px boundary
- [ ] No visible seam at the noise atlas → SDF atlas boundary (Boring Billion late → Cryogenian)
- [ ] Canvas resizes correctly on window resize
- [ ] Performance: consistent 60fps at default `--earth-size`

---

## Files Affected

| File | Change |
|------|--------|
| `deeptime.html` | Remove Three.js `<script>`; replace WebGL block with Canvas 2D pipeline; add `base64NoiseAtlas` constant |
| `bake-noise-atlas.html` | New — one-time offline bake tool, not deployed |
| `CLAUDE.md` | Update WebGL Earth section; update known issues list |
| `colour-reference.md` | No changes |
