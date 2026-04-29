# Eona.Earth

A website that maps Earth's 4.5 billion year history onto a 12-hour clock. Midnight = Earth forms. The full sequence repeats twice per day.

## Concept

The clock runs on local time. When you look at it at 3am or 3pm, you're seeing the Cambrian explosion. At 11:39, the dinosaurs go extinct. Humans appear in the final 0.3 seconds before noon/midnight.

The goal is visceral understanding — not education, but feeling. The "holy shit" moment when abstraction clicks into physical intuition.

---

## Aesthetic Direction

### References
- NASA worm logo
- CMF/Nothing watch faces (cold precision)
- Voyager Golden Record
- Whole Earth Catalog
- Icinori illustration studio (warm, stylized) — https://icinori.fr/
- Vintage astronomical diagrams
- https://deeptime.info/ (functional reference)

### Palette
- **Background**: True black `#000000`
- **Rings/text**: White and grey spectrum — neutral, restrained
- **Accent**: `#FF4D00` — used sparingly for position indicator, era labels, events
- **Earth colours**: See `colour-reference.md` for full per-phase palettes

### Typography
- **Space Mono**: All UI text — data, numbers, labels, era names, timestamp, time display
- **Fraunces**: Event descriptions (Regular 16px, line-height 1.3)
- `-webkit-font-smoothing: antialiased` on body to eliminate subpixel glow on dark backgrounds
- Most info panel text uses `line-height: 1` + `text-box: trim-both cap alphabetic` for cap-to-baseline vertical trim

### Vibe
Cold precision (Nothing/CMF) meets warm illustration (Icinori/Whole Earth). Restrained palette with one strong accent.

---

## Architecture

### Time Model
- 12-hour clock mapped to 4,540 Ma (million years ago)
- `00:00` / `12:00` = 4,540 Ma (Earth forms)
- Current local time = present day; full history repeats every 12 hours
- 1 hour ≈ 378 Ma · 1 minute ≈ 6.3 Ma · 1 second ≈ 105,000 years
- `timeToMa` uses `(hours % 12) / 12` so the 12-hour AM/PM cycles both cover the full sequence

### Three Toggleable Layers
1. **Earth** (`#earth-layer`): WebGL sphere, rotates 1 rev/60 s. Toggled via `data-layer="earth"`. Haze layers (`#haze-layer`, `#dark-haze-layer`, `#earth-shadow`) are hidden when this layer is toggled off.
2. **Eons** (`#infographic-layer`): SVG — eon pie slices with progressive reveal. Event marker dots and hit areas are toggled with this layer via JS (dots in `#persistent-layer`, hit areas disabled via `pointer-events`).
3. **Clock** (`#clock-layer`): SVG minute hand + 60 minute tick marks (`#clock-hour-markers`). `z-index: 1` so it renders above `#persistent-layer`.

Layers stack bottom-to-top: `#infographic-layer` → `#earth-shadow` → `#earth-layer` → `#haze-layer` → `#dark-haze-layer` → `#persistent-layer` → `#clock-layer` (z-index 1). Each toggleable layer toggles independently via `.toggle` buttons.

**`#persistent-layer`** — a non-toggleable SVG always visible, containing: `#clock-eon-markers` (12 hour ticks), `#position-indicator` (scrubber handle), `#event-markers` (dots, shown/hidden with eon layer), `#event-hit-areas` (transparent hit circles, pointer-events toggled with eon layer).

### Interaction
- **Scrub handle** (orange/outline circle, r=24, orbit r=156): drag to scrub through geological time. Globe rotation follows. Acts as the "hour hand" — its position on the ring shows the current geological age.
  - Enters **outline state** (transparent fill + 1px white stroke, 0.5s ease) immediately on grab. Stays outlined until "Return to now" is clicked.
  - Returns to **solid orange** (0.5s ease) on `exitScrub()`.
  - `_handleLatched` flag tracks outline state — only set during `scrub.active`, reset in `exitScrub`.
- **Drag anywhere else** on the clock: rotates the globe only; time stays live.
- **Return to now** button: exits scrub mode, restores handle to orange, restores minute hand + dot. Styled: Space Mono Regular 0.75em black (`#000000`), sentence case, padding 8px 12px, orange fill (`#FF4D00`), pill shape (`border-radius: 999px`). `display: none` by default; `display: inline-flex` when `body.scrubbing`. `transform: translateY(12px)` to optically centre it with the time text.
- **`pointer-events: none`** on `.info-panel` — prevents info bar from blocking clock drags. Interactive children (button, toggles) have `pointer-events: auto` selectively re-enabled.
- Pointer events are on `.clock-container` div (not the SVG) so empty-space drags work reliably.
- **Scrub time display**: while scrubbing, the time display shows the geological clock time (what the clock hand represents) rather than local time. Time display dims to `#666666` when scrubbing (`body.scrubbing #time-display`). Time tracks handle position continuously across 12/24-hour boundaries.
  - **Cumulative angle tracking**: `scrub.cumulativeAngleDelta` accumulates raw angle delta each frame. `scrub.displayStartSecs` stores the displayed time at drag start (carried forward on re-grab). Displayed time = `displayStartSecs + cumulativeAngleDelta / 360 * 43200`, then `% 86400` to wrap. This allows scrubbing past midnight/noon without getting stuck in a 12-hour window.
  - **`lastAngle` is seeded from `maToAngle(initialMa)`** (the handle's true centre angle) — not the pointer's click position. The click offset is absorbed into the first pointermove delta, keeping handle position and displayed time locked to a single source of truth. Seeding from the pointer angle instead caused up to ~17 min of error per grab (click edge of 24px handle on 156px orbit ≈ 8.7° offset ≈ 17 min), compounding across re-grabs.
  - On re-grab (while `scrub.active`): `displayStartSecs` is set to the current displayed time (not real local time) so no jump occurs.
- **Minute hand + central dot**:
  - Hidden (0.3s ease) when scrubbing starts **only if earth layer is visible**.
  - Stay hidden until "Return to now" is clicked (not restored on drag release).
  - If earth layer is toggled during scrub: hand/dot appear when earth hidden, disappear when earth shown.
  - When earth is hidden and scrubbing: minute hand tracks the scrubber position (whole-minute snapping, no motion blur). Angle = `maToAngle(scrub.ma) + 90`.

---

## Technical Implementation

### Stack
- Vanilla JS + HTML + CSS — single self-contained file (`eona.html`)
- Three.js r128 (CDN) for WebGL Earth
- Google Fonts CDN (Space Mono)
- No build step

### Key Functions
```js
timeToMa(h, m, s)           // local time → Ma (12-hour cycle: uses h % 12)
maToAngle(ma)               // Ma → SVG clock angle (degrees, 12 o'clock = −90°)
angleToMa(angleDeg)         // SVG clock angle → Ma (inverse of maToAngle)
getVisualState(ma)          // Ma → { a, b, blend, atmosphereBlend } — two adjacent STATES entries + mix factors
getSdfBlend(ma)             // Ma → { indexA, indexB, blend } — SDF atlas slice addressing
getCurrentEon(ma)           // Ma → eon object
getCurrentEra(ma)           // Ma → era string label
updateEonReveal(ma)         // Ma → updates #eon-reveal-path clipPath for progressive eon disclosure
drawEonRing()               // renders eon pie slices into #eon-ring (called once on init)
drawPositionIndicator()     // updates scrubber handle position; creates persistent SVG elements on first call
updateEventMarkerStates(x,y,ma) // called each frame from drawPositionIndicator; checks pixel + Ma proximity; updates dot colours + handle outline state
drawEventMarkers()          // renders event dots into #event-markers, hit areas into #event-hit-areas (called once on init)
drawClockHourMarkers()      // renders 60 minute ticks into #clock-hour-markers (clock-layer) + 12 hour ticks into #clock-eon-markers (persistent-layer)
showEventDescription(i)     // sets _activeEventMa, updates center suffix + desc; years-display locked via updateDeepTimeDisplay
hideEventDescription()      // clears _activeEventMa, hides center suffix + desc
updateDeepTimeDisplay(ma)   // updates era-display + years-display; locks years to _activeEventMa when ma >= _activeEventMa, resumes live time when past
enterScrub(initialMa, initialAngle) // starts scrub session; seeds cumulative angle tracking
exitScrub()                 // ends scrub session; restores handle to orange, restores minute hand
```

> **Orphaned (defined, not called from `init()`):** `drawLifeRing()` — renders life-milestone arcs into `#life-ring` using the `LIFE` constant; `drawHourMarkers()` — renders 24-tick ring into `#hour-markers`. Both reference elements that exist in the HTML but the functions are not wired up. The `#hour-markers` group sits inside `#infographic-layer`.

### Key Globals
```js
_currentMa          // current geological Ma this frame (set in tick before drawPositionIndicator)
_activeEventMa      // Ma of the currently active event; null when no event active
_handleLatched      // true when scrubber handle is in outline state during a scrub session
_hoveredEventIndex  // index of currently hovered event dot (-1 if none)
```

### Key Constants
```js
EVENTS    // array of { name, time, desc } — event marker data (geological moments)
LIFE      // array of { name, time } — life-milestone data used by drawLifeRing() (not currently active)
STATES    // array of visual waypoints; see STATES Reference below
```

---

## WebGL Earth

### Overview
A Three.js `SphereGeometry` (radius 1, 64×64 segments) with a custom `ShaderMaterial`. The fragment shader is an uber-shader: `renderSurface()` branches on a per-state `surfApproach` uniform (screenprint / watercolor / topographic) and `computeCloudMask()` branches on a per-state `cloudApproach` uniform (warped / ridged_wisps / warped_layers / warped_wisps). Both are called twice per pixel (dual-render A/B) so adjacent states can use different approaches and the cross-fade works naturally. `CLOUDS_ENABLED = true`.

### Camera & Canvas Sizing
- Camera: `PerspectiveCamera(45°, 1, 0.1, 100)`, positioned at `z = 3.12`
- Projected sphere diameter = **1.021 × `--earth-size`** (derived: `arcsin(1/3.12)` = 18.70°, fraction of half-FOV = `tan(18.70°)/tan(22.5°)` = 0.817; × 1.25 canvas ratio = 1.021)
- `--earth-size: calc(var(--clock-size) * 0.45)` — globe is 45% of the clock face diameter
- `--earth-canvas-size = --earth-size × 1.25` — the container is 25% larger than the visual sphere diameter, giving ~12% clear buffer on every side for the atmospheric glow to bleed into without clipping
- Canvas: `width/height: 100%` of the container; no `overflow: hidden` on the container (needed for glow)

### Globe Rotation
- Live mode: 4 rotations per hour (`Math.PI * 2 / 900` rad/s)
- Scrub / drag mode: driven by `scrub.rotationOffset`
- Clouds rotate independently at 1.2× globe speed via `cloudRotation` uniform

### Dual-Render Transition System
Each frame, the shader renders two full surface passes — state A and state B — and blends them by `stateBlend` (0 = fully A, 1 = fully B). This keeps each state's noise pattern locked to its own seed, so surface features don't morph in noise space during transitions; they cross-dissolve cleanly while the globe continues to rotate.

**Key rule**: if two adjacent STATES share the same `seed` AND the same `noiseThresh1`/`noiseThresh2`, the A and B renders produce identical shapes — the blend is a pure colour dissolve with zero shape cross-fade. Use this when you want a palette transition that preserves geography (e.g. Molten Hadean early → late).

### Colour / Layer Coverage Maths
The noise surface path paints three layers in order: c3 base → c2 over shape1 region → c1 over shape2 region.

Coverage (fbm output is roughly uniform in `[0, 0.9375]`, not `[0, 1]` — the formula below is nominal):
```
c3  =  noiseThresh1 × noiseThresh2
c2  =  (1 − noiseThresh1) × noiseThresh2
c1  =  1 − noiseThresh2
```

Calibrated threshold values for common land ratios (t1=0.50 for equal c2/c3 split):
- 20/80 land: `t2=0.65, t1=0.50`
- 25/75 land: `t2=0.62, t1=0.50`
- 44/56 land: `t2=0.56, t1=0.46` (default for SDF phases)
- 60/40 land: `t2=0.40, t1=0.25` (Hadean — old screenprint values)

⚠️ These thresholds assume **fbm noise** (screenprint / watercolor approaches). The **topographic approach** uses `ridgedFbm`, which has a different output distribution (skewed toward 1.0). Hadean states now use topographic with `t1=0.80, t2=0.79` — these high values are correct for ridged noise but would make land invisible on screenprint. When changing a state's surfaceApproach, re-tune thresholds in the colour lab.

⚠️ Do not use `t2 > 0.70` for **screenprint/watercolor** phases — land becomes invisible as the fbm distribution thins out above ~0.75.

### Atmosphere & Cloud System
Clouds are rendered in a separate pass from the surface using `computeCloudMask()`, composited in `main()` using `atmosphereBlend` rather than `stateBlend`. This makes the atmosphere lead surface transitions by 20% of each blend window.

**`atmosphereBlend`** — computed in `getVisualState()` as `smoothstep(clamp(t + 0.2, 0, 1))`. Returned alongside `blend` and passed as a shader uniform.

**Cloud approaches** (selected per-state via `cloudApproach` field):
- **warped** (0.0) — domain-warped fbm, 0.04 smoothstep. Good band↔swirl range via `cloudShp`. Can clump at mid densities. Used for: Hazy Archean (late), GOE (late), Boring Billion (late), Cryogenian.
- **ridged_wisps** (1.0) — ridged multifractal, cirrus-like wisps. Standalone ridged turbulence. Not currently assigned to any production state.
- **warped_layers** (2.0) — three transparent fbm layers at different scales/speeds. Translucent→solid depth. Good for thick, heavy atmospheres. Used for: Hadean, Steam World, Archean (early), GOE (early), Huronian, Boring Billion (early/mid).
- **warped_wisps** (3.0) — warped fbm body + ridged detail + edge erosion. Brushstroke feel without stiffness. Used for: Hothouse, Green World, Modern Earth.

**Cloud animation:**
- Independent rotation via `cloudRotation` uniform (1.2× globe speed, same direction)
- Slow noise drift: `sOff += vec3(time * 0.004, time * 0.003, time * 0.0025)`
- Subtle opacity pulse: `mask *= 1.0 + 0.05 * sin(time * 0.18)` (~35s period)
- Crisp edges: smoothstep width 0.04–0.06 depending on approach

**Hadean states** keep `cloudDensity: 0.00` — no atmosphere renders there regardless of `CLOUDS_ENABLED`.

### Surface Approach System
Surface rendering is selected per-state via `surfaceApproach` field. The uber-shader branches on a float uniform (`aSurfApproach` / `bSurfApproach`):

- **screenprint** (0.0) — two fbm layers, narrow smoothstep (0.04). Hard-edged registered ink zones. The Icinori riso aesthetic. Default for most states. All SDF-era states must use screenprint (the data-driven land/sea path only applies screenprint noise for modulation).
- **watercolor** (1.0) — domain-warped fbm, wide smoothstep (0.18). Colour zones bleed into each other. Soft, organic. Used for: Steam World.
- **topographic** (2.0) — ridged multifractal with contour-line character. Bright creases where noise folds. Requires `ridgedFbm()`. Used for: Molten Hadean (early + late).

**Approach encoding in JS:**
```js
const SURF_APPROACH_ID  = { screenprint: 0.0, watercolor: 1.0, topographic: 2.0 };
const CLOUD_APPROACH_ID = { warped: 0.0, ridged_wisps: 1.0, warped_layers: 2.0, warped_wisps: 3.0 };
```
`setState()` encodes the string → float via these maps each frame.

### Atmospheric Glow
Applied as a CSS `filter: drop-shadow()` on `#earth-layer` each frame via `updateEarth()`. Two stacked shadows (tight core + soft halo) are used for a hot-core feel. Strength and colour are interpolated between STATES A and B alongside the surface blend. Set `glowStrength: 0` on states with no glow.

**States with glow currently:** Molten Hadean early (0.80), late (0.55), Steam World (0.20 — residual cherry red fading to 0). All other states: 0.0.

### Atmospheric Haze Layer
A CSS `#haze-layer` div sits above the WebGL canvas. Each frame `updateEarth()` sets its background to a radial gradient and its opacity to the interpolated per-state value. Visibility is tied to `#earth-layer` — hidden when earth layer is toggled off.

**Noise overlay:** `#haze-layer::after` pseudo-element with a data-URI SVG `feTurbulence` filter (type `fractalNoise`, baseFrequency `0.65`, 200×200px tile) at `mix-blend-mode: multiply`, 15% opacity. Inset 25% so noise stays inside the sphere boundary.

**Sizing:** `calc(var(--earth-size) * 1.021)` with `border-radius: 50%`. The 1.021 factor matches the sphere's true projected diameter (see Camera & Canvas Sizing above), so the haze boundary aligns with the sphere edge.

**Gradient:** `radial-gradient(circle closest-side at center, rgba(r,g,b,0) 50%, rgba(r,g,b,1) 100%)` — transparent at centre, full colour at the limb. `closest-side` locks the gradient circle to the div's inscribed circle, preventing the default `farthest-corner` behaviour which would bleed colour into the transparent corners of the square bounding box.

**Per-state fields on STATES entries:**

| Field | Type | Notes |
|-------|------|-------|
| `hazeColor` | hex string | Haze tint colour |
| `hazeOpacity` | float 0–1 | Overall opacity of the haze element |

Colour and opacity are linearly interpolated between adjacent states each frame (same blend factor `t` as the surface). `hazeRgb` is pre-parsed at startup alongside `glowRgb`.

See `colour-reference.md` for per-phase haze values.

### Dark Haze Layer
A CSS `#dark-haze-layer` div sits above `#haze-layer`, sized identically (`calc(var(--earth-size) * 1.021)`, `border-radius: 50%`). It uses `mix-blend-mode: multiply` to darken the globe in the "future" arc — the region from the current hour position clockwise back to midnight. Visibility is tied to `#earth-layer`.

**Noise overlay:** Same `::after` treatment as `#haze-layer` (fractalNoise, 0.65, multiply, 15%).

**Wipe behaviour:** At midnight the dark zone covers 360° (full globe). As the hour hand sweeps clockwise, the dark zone shrinks. At end of 12-hour cycle it covers 0°. The midnight edge is always hard. The leading edge (receding edge at the hour hand position) has a soft 22.5° conic fade (~20% of sphere diameter at the rim).

**Implementation:** Each frame `updateEarth()` writes a `conic-gradient(from 0deg at center, ...)` directly to `darkHazeEl.style.background`. The gradient goes: transparent 0° → transparent (hourDeg − 22.5°) → dark (hourDeg) → dark 360°. Opacity is set separately via `darkHazeEl.style.opacity`.

**Per-state fields on STATES entries:**

| Field | Type | Notes |
|-------|------|-------|
| `darkHazeColor` | hex string | Multiply-blend tint colour |
| `darkHazeOpacity` | float 0–1 | Overall layer opacity. Interpolated each frame. |

`darkHazeRgb` is pre-parsed at startup in the same `STATES.forEach` pass as `hazeRgb` and `glowRgb`.

See `colour-reference.md` for per-phase dark haze values.

### Earth Shadow Layer
A CSS `#earth-shadow` div sits between `#infographic-layer` and `#earth-layer`. Full clock diameter, `border-radius: 50%`. Radial gradient: `#000000` 100% at 50% radius → transparent at 100%. Creates a vignette behind the earth.

**Noise overlay:** `#earth-shadow::after` with a data-URI SVG `feTurbulence` filter (type `turbulence`, baseFrequency `0.5`, 200×200px tile), 15% opacity.

Visibility is tied to `#earth-layer` — hidden when earth layer is toggled off.

### SDF Paleogeographic Atlas
A base64-encoded PNG (512 × 2816 px) embedded in the HTML. 11 signed-distance fields stacked vertically, one per timestamp:

| Index | Ma  |
|-------|-----|
| 0     | 0   |
| 1     | 66  |
| 2     | 120 |
| 3     | 180 |
| 4     | 240 |
| 5     | 300 |
| 6     | 360 |
| 7     | 420 |
| 8     | 480 |
| 9     | 540 |
| 10    | 635 |

SDF value 0.5 = coastline; >0.5 = land; <0.5 = sea. `useLandSea` on each state blends between pure procedural noise (0.0) and fully data-driven continents (1.0).

#### ⚠️ Known Gotchas — Read Before Touching Texture or Shader

**1. `sdfTex.flipY = false` is mandatory.**
Three.js defaults to `flipY = true`, which flips the PNG vertically on GPU upload. This simultaneously:
- Swaps north and south poles (the shader's `v=0` points to the south pole instead of north)
- Reverses the atlas slice sequence (index 0 reads 635 Ma data, index 10 reads present-day)

Result: Modern Earth shows Pangea; Blue Water World shows modern coastlines. The fix (`flipY = false`) must be set *before* `needsUpdate = true`.

**2. Longitude must use `atan(p.z, -p.x)`, not `atan(p.z, p.x)`.**
Positive `p.x` produces decreasing longitude as you move rightward — east and west are mirrored. Negating `p.x` makes longitude increase eastward correctly. Both bugs have been reintroduced accidentally; if continents look wrong, check these two lines first.

---

## STATES Reference

Each entry in the `STATES` array is a visual waypoint. The Earth interpolates continuously between adjacent entries. Fields:

| Field | Type | Notes |
|-------|------|-------|
| `name` | string | Human label |
| `span` | `[startMa, endMa]` | startMa is older |
| `blendStart` | Ma | When blending toward next entry begins. Equal to `span[0]` for full-span drift. |
| `palette` | 5 hex strings | `[c0, c1, c2, c3, c4]` — see colour-reference.md |
| `noiseThresh1` | float | c3/c2 boundary threshold centre (default 0.46) |
| `noiseThresh2` | float | c2/c1 boundary threshold centre (default 0.56) |
| `glowColor` | hex string | Atmospheric glow colour (omit or `null` if no glow) |
| `glowStrength` | float 0–1 | Glow intensity. 0 = no glow. |
| `hazeColor` | hex string | Atmospheric haze overlay colour |
| `hazeOpacity` | float 0–1 | Overall haze opacity. Interpolated each frame. |
| `darkHazeColor` | hex string | Dark multiply-blend overlay colour |
| `darkHazeOpacity` | float 0–1 | Dark haze opacity. Interpolated each frame. |
| `cloudDensity` | float 0–1 | Cloud coverage |
| `surfaceIntensity` | float 0–1 | How prominent surface features are vs flat |
| `cloudShape` | float 0–1 | 0 = horizontal bands, 1 = swirled Apollo-style |
| `polarIce` | float 0–1 | Polar cap whitening strength |
| `seed` | float | Noise offset — gives each state distinct feature placement |
| `useLandSea` | float 0–1 | 0 = pure procedural, 1 = SDF atlas continents |
| `coastSoftness` | float | Smoothstep width around coastline (0.01 = crisp) |
| `surfaceApproach` | string | `'screenprint'` / `'watercolor'` / `'topographic'` — selects noise shaping |
| `cloudApproach` | string | `'warped'` / `'ridged_wisps'` / `'warped_layers'` / `'warped_wisps'` |

Current STATES sequence (15 entries):

All blends use **smoothstep easing** (slow → fast → slow). Transition style noted per entry.

| # | Name | Span (Ma) | Surface | Clouds | Transition in | Transition out |
|---|------|-----------|---------|--------|---------------|----------------|
| 0 | Molten Hadean (early) | 4540–4420 | topographic | warped_layers | — | Full-span drift. Glow 0.80. |
| 1 | Molten Hadean (late) | 4420–4300 | topographic | warped_layers | Full-span | 30 Ma ramp into Steam World. Glow 0.55. |
| 2 | Steam World | 4300–4000 | watercolor | warped_layers | 30 Ma ramp | 60 Ma ramp. Glow 0.20 fading to 0. |
| 3 | Hazy Archean (early) | 4000–3200 | screenprint | warped_layers | 60 Ma from Steam | Full-span drift. |
| 4 | Hazy Archean (late) | 3200–2500 | screenprint | warped | Full-span | 30 Ma snap into GOE. |
| 5 | Great Oxidation (early) | 2500–2400 | screenprint | warped_layers | 30 Ma snap | Full-span drift. |
| 6 | Great Oxidation (late) | 2400–2300 | screenprint | warped | Full-span | 2 Ma snap into snowball. |
| 7 | Huronian Snowball | 2300–2100 | screenprint | warped_layers | 2 Ma snap | 5 Ma thaw. |
| 8 | Boring Billion (early) | 2100–1500 | screenprint | warped_layers | 5 Ma from snowball | Full-span drift. 25/75 land. |
| 9 | Boring Billion (mid) | 1500–1000 | screenprint | warped_layers | Full-span | Full-span drift. 25/75 land. |
| 10 | Boring Billion (late) | 1000–720 | screenprint | warped | Full-span | 2 Ma snap into Cryogenian. 25/75 land. |
| 11 | Cryogenian Snowball | 720–635 | screenprint | warped | 2 Ma snap | 2 Ma thaw. First SDF data (`useLandSea: 0.35`). |
| 12 | Hothouse World | 635–400 | screenprint | warped_wisps | 2 Ma thaw | 70 Ma ramp. Full SDF (`useLandSea: 1.0`). |
| 13 | Green World | 400–66 | screenprint | warped_wisps | 70 Ma ramp | Full-span drift into Modern Earth. Full SDF. |
| 14 | Modern Earth | 66–0 | screenprint | warped_wisps | Full-span | — Full SDF + polar ice. |

For palette details and colour rationale for each state, see **`colour-reference.md`**.

---

## SVG Layers

### `#infographic-layer` (toggleable — Eons)
- **`#eon-ring`**: Six pie slices (SVG path `M cx cy L p1 A r r 0 largeArc 1 p2 Z`), clipped to `#eon-reveal-clip`. Colours `#BBBBBB` at varying opacity:
- **`#hour-markers`**: 24-tick ring at the outer rim (r=188–195). Populated by `drawHourMarkers()` which is defined but not currently called from `init()`.
  - Hadean (4540–4000 Ma): 16%
  - Archean (4000–2500 Ma): 32%
  - Proterozoic (2500–538.8 Ma): 48%
  - Paleozoic (538.8–251.9 Ma): 64%
  - Mesozoic (251.9–66 Ma): 80%
  - Cenozoic (66–0 Ma): 96%
  - Noise overlay: SVG `<filter>` with `feTurbulence` (baseFrequency 1.0) → `feColorMatrix` (alpha) → `feFlood` black → `feComposite`, 25% opacity
- **Progressive reveal**: `<clipPath id="eon-reveal-clip">` contains a dynamically updated `<path id="eon-reveal-path">` — a conic sector from 12 o'clock to the current hour hand position. Updated every frame by `updateEonReveal(ma)`.

### `#clock-layer` (toggleable — Clock, z-index: 1)
- **`#clock-hour-markers`**: 60 minute ticks, `#666666`, 1px stroke. Inner edge r=180, outer edge r=200.
- **`#clock-hands`**: Minute hand only (`#minute-hand`) — white line, stroke-width 2. Central dot r=8 (16px diameter).

### `#persistent-layer` (non-toggleable — always visible)
- **`#clock-eon-markers`**: 12 hour ticks, `#666666`, 1px stroke. Inner edge r=160, outer edge r=180. Always visible on all layers.
- **`#position-indicator`**: Scrubber handle — persistent SVG circle, r=24, orbit r=156. Solid orange (`#FF4D00`) at rest; outline state (transparent fill + 1px white stroke) during scrub. CSS transition `fill 0.5s ease, stroke 0.5s ease`.
- **`#event-markers`**: Event dots, r=2, orbit r=156. White normally; orange (0.5s ease) when active via scrubber or hover; black when active with handle solid. Shown/hidden with eon layer toggle via `display` style.
- **`#event-hit-areas`**: Transparent hit circles r=12, `pointer-events="all"`. Disabled (`pointer-events="none"`) when eon layer is hidden.

---

## Event Marker Behaviour

- **Dot states**: white (default) → orange (active, handle outlined) → black (active, handle solid) — 0.5s ease transition
- **Active zone**: scrubber centre within ±4px of a dot AND within 300 Ma of the event's geological time → that dot activates. The Ma-proximity check prevents the "Earth forms" dot (at 12 o'clock = 4540 Ma) from triggering near end-of-cycle (0 Ma), which maps to the same clock position. Only one active at a time (closest wins).
- **Overlap zone**: scrubber centre within 24px of any dot → handle enters outline state (latched for duration of scrub).
- **Hover**: hovering a hit area turns the dot orange and shows the floating tooltip (when eon layer visible).
- **Event active in center column**: when an event activates, `#event-name-suffix` appends ` • Event Name` to the timestamp, `#event-desc-center` shows the description above the timestamp row, and `_activeEventMa` is set to the event's time.
  - **Timestamp locking**: `updateDeepTimeDisplay` locks `#years-display` to the event time while `ma >= _activeEventMa` (scrubber approaching or at event). Once `ma < _activeEventMa` (scrubber passes the event toward present), years-display resumes live time — even if the event name/desc are still showing.
  - **Event description**: Fraunces Regular 16px `#ffffff`, line-height 1.3, 300px fixed width, `display: none` → `display: block` via `.visible` class. Positioned above `.center-timestamp` in the flex column (grows upward, timestamp stays pinned to baseline).
- **Tooltip** (floating, follows cursor): shown on hover only. `#222222` background, Space Mono 0.6em, max-width 250px. Disabled when eon layer hidden.

---

## UI — Info Panel

Fixed bottom bar, `padding: 24px 32px 32px`, flex row space-between, `align-items: flex-end`. `pointer-events: none` on the panel itself; interactive children have `pointer-events: auto`.

**Top-left header** (`.header`, flex row, `align-items: flex-end`):
- `.title`: `<img src="images/logo.svg" width="70">` — SVG logo replaces text.
- `.layers-control` (header-center): layers button + expandable tree. "Layers" label is white (`#ffffff`); hidden (`display: none`) when tree is expanded (`.layers-btn.active`). `layers-default.svg` = white strokes, `layers-hover.svg` = white strokes, `layers-active.svg` = white strokes.
- **Layer tree**: `connector-section` height 16px; horizontal connector line at `top: 8px`; `vline-outer` 8px; `vline-middle` 16px.

**Images directory:**
- `images/logo.svg` — wordmark/logo used in `.title`
- `images/favicon.png` — browser tab icon (`<link rel="icon">` in `<head>`)

**Left column** (`.info-left`, `flex: 1`):
- `.era` (`#era-display`): current eon/era name. Space Mono Regular 1em `#aaaaaa`.

**Centre column** (`.info-center`, flex-column, `align-items: center`, `justify-content: flex-end`, `gap: 16px`, `flex: 1`):
- `.info-event-name` → `#event-name-suffix`: event name label. Space Mono bold 12px `#FF4D00`. Empty when no event active. Sits 16px above event description via column gap.
- `#event-desc-center` (`.center-event-desc`): event description. `display: none` → `display: block` via `.visible`. Fraunces Regular 16px `#ffffff`, line-height 1.3, `text-align: center`, fixed `width: 300px`.
- `.center-timestamp` (in `.info-bottom` centre): `#years-display` (Space Mono bold 0.75em `#FF4D00`).

**Right column** (`.info-right`, flex-row, `align-items: flex-end`, `justify-content: flex-end`, `gap: 16px`, `flex: 1`):
- `#time-display`: local time. Space Mono Regular 1em `#aaaaaa`. Dims to `#666666` when `body.scrubbing`.
- `#return-to-now` (`.return-to-now`): 32×32px SVG circle button, `#E34E2A` fill. `display: none` by default; `display: inline-block` when `body.scrubbing`.

All Space Mono text: `line-height: 1`, `text-box: trim-both cap alphabetic`.

---

## Colour Reference

See **`colour-reference.md`** for:
- Full 5-stop palette (`c0`–`c4`) for every phase
- Coverage rationale for each colour slot
- Atmosphere/glow notes per phase
- Palette design principles

---

## Render Labs

Standalone HTML dashboards for comparing shader approaches side-by-side. Each renders multiple WebGL globes with shared controls (palette, speed, thresholds) so treatments can be evaluated under identical conditions. Same design language as the main app: black background, Space Mono, `#FF4D00` accents.

### `cloud-compare.html` — Cloud Render Lab

Four cloud rendering approaches on a 4-column grid. Each globe shares a `surfaceColor()` function and differs only in `cloudMask()`.

**Approaches:**
- **Warped** — current shader baseline. Domain-warped fbm, 0.04 smoothstep. Good band↔swirl range via `cloudShp`. Can clump at mid densities.
- **Ridged Wisps** — ridged multifractal, cirrus-like wisps from dependent octaves. Standalone ridged turbulence.
- **Warped Layers** — three transparent fbm layers at different scales/speeds. Translucent→solid depth. Camo breakup at mid-range.
- **Warped Wisps** — warped fbm body + ridged detail + edge erosion. Keeps Warped's shape range, breaks up clumpy silhouettes. Primary replacement candidate.

**Controls:** Cloud Density (0–0.80), Cloud Shape (band↔swirl, 0–1), Rotation Speed, Palette (modern/hadean/archean/hothouse/snowball), Presets (Steam, Archean, Modern, Hothouse, Cryo).

**Outcome:** Warped Wisps selected as the production cloud approach — brushstroke feel without stiffness. However, per-state approach selection was adopted instead of a single global approach: warped_layers for heavy early atmospheres, warped for transitional/snowball states, warped_wisps for post-snowball.

### `surface-compare.html` — Surface Render Lab

Five surface rendering approaches split across two grids: procedural (3-column) and data-driven (2-column). Each globe shares the same PREAMBLE (noise functions, rotY, fakeSdf) and differs in `surfaceColor()`.

**Procedural approaches** (pre-SDF eras — pure noise, no continent data):
- **Screenprint** — current shader. Two fbm layers, narrow smoothstep (0.04). Hard-edged registered ink zones. The Icinori riso aesthetic.
- **Watercolor** — wide smoothstep (0.18), domain-warped fbm. Colour zones bleed into each other. Soft, organic, imprecise. Suited to dreamy early eras.
- **Topographic** — ridged multifractal with contour-line character. Bright creases where noise folds. High-frequency detail, busy and layered.

**Data-driven approaches** (post-snowball — SDF continents):
- **Clean Data** — current SDF approach. Near-flat land/sea, ±7% noise modulation, crisp coastline. Maximum continent readability.
- **Riso Print** — heavy grain, dithered coastline edge, visible dot texture on both land and sea. Printmaking aesthetic pushed to the maximum. Screenprint texture is the star, continents are secondary.

**Controls:** Thresh 1 (c3/c2 boundary), Thresh 2 (c2/c1 boundary), Surface Intensity, Speed, Palette (modern/hadean/archean/hothouse/snowball/boring billion), Presets (Hadean 60/40, Archean 20/80, Boring Bn, Modern 44/56, Hothouse, Snowball). Coast softness is hardcoded at 0.03.

**Key finding:** Data-driven approaches have limited stylistic flex — the SDF continents must read clearly, so heavy texture fights legibility. The procedural eras have much more room to push things. Riso Print is the maximum viable texture for continent-era states.

### `colour-lab.html` — Colour Lab

Unified per-phase editor for palette, shader approach, haze, and render parameters. Single raw-WebGL globe (quad-shader, no Three.js) with CSS haze overlays, matching the production rendering pipeline. Three-column layout: phase list → globe + colour picker → shader controls.

**Layout:**
- **Top strip** — all 15 phases as stacked c3→c0 colour bands; click to jump.
- **Left panel** — scrollable phase list with 4 swatches per phase. Click any swatch to edit. Active phase highlighted with `#FF4D00` index number.
- **Centre: globe** — 240px WebGL globe rendered via a fullscreen-quad fragment shader (no geometry). Identical PREAMBLE (noise functions, `rotY`) shared with cloud-compare and surface-compare. Light haze and dark haze are CSS div overlays on top, using the production `radial-gradient(circle closest-side ...)` approach. Rotation is west-to-east (negative angle in `rotY` convention). Clouds rotate independently at a separate speed.
- **Centre: colour wheel** — HSL gradient wheel (radius = saturation, angle = hue) rendered to a 400×400 canvas, displayed at 200px. Lightness slider below. Crosshair tracks current position. Direct hex input with swatch preview.
- **Centre: haze pickers** — Light Haze and Dark Haze colour circles below the c0–c3 slots. Click to switch the colour wheel target to `hazeColor` or `darkHazeColor`. Opacity sliders for each, writing to `hazeOpacity` and `darkHazeOpacity` on the active phase.
- **Right panel: surface controls** — Approach tabs (Screenprint, Watercolour, Topographic), Thresh 1, Thresh 2, Intensity, Speed sliders. SDF phases (`useLandSea > 0`) grey out Watercolour and Topographic — only Screenprint available, since the procedural alternatives don't apply to continent data.
- **Right panel: cloud controls** — Approach tabs (Warped, Ridged Wisps, Warped Layers, Warped Wisps), Density, Shape, Speed sliders. All four approaches available on every phase.
- **Bottom global bar** — Toggles for Clouds, Light Haze, Dark Haze (apply across all phases). Grain slider (global). Undo button (per-phase stack). Reset Phase button (reverts active phase to original prod values). Copy Palette JS export button.

**Shader architecture:** The globe compiles a fragment shader by concatenating `PREAMBLE + SURF_FN[key] + CLOUD_FN[key] + MAIN_FN`. Switching surface or cloud approach triggers a recompile. Switching phases also forces recompile (clears `currentSurfKey`/`currentCloudKey`). Uniform locations are cached per-program.

**Per-phase state fields managed by colour lab:**
- `palette` (5 hex strings, c0–c4)
- `hazeColor`, `hazeOpacity`, `darkHazeColor`, `darkHazeOpacity`
- `noiseThresh1`, `noiseThresh2`, `surfaceIntensity`
- `cloudDensity`, `cloudShape`
- `surfaceApproach` (one of `screenprint`, `watercolor`, `topographic`)
- `cloudApproach` (one of `warped`, `ridged_wisps`, `warped_layers`, `warped_wisps`)

**Undo system:** One undo snapshot pushed per drag gesture (not per frame), using a `_undoPushedThisDrag` flag. `pointerdown` on any interactive control pushes a deep-copy of the full phase state; subsequent `input` events during the same drag do not push. `pointerup` resets the flag. 50-deep stack per phase. Cmd/Ctrl+Z keyboard shortcut. Reset Phase pushes an undo before reverting.

**Keyboard navigation:** Arrow keys or vim `hjkl`. Up/down = phase. Left/right cycles through targets: `c0 → c1 → c2 → c3 → hazeColor → darkHazeColor`.

**Export:** "Copy Palette JS" button writes all 15 phases' palette, haze, threshold, cloud, and approach values to the clipboard as JS-ready snippets. The exported values are stored in `palette-js.md` and have been applied to production `eona.html` via `implement_palette.py`.

---

## Known Issues / Watch-outs

1. **SDF orientation** — `flipY = false` and `atan(p.z, -p.x)` must both be present. Easy to lose when refactoring the texture setup or shader. See SDF gotchas above.
2. **Cloud rotation direction** — `cloudRotation` must be decremented (not incremented) each frame to match globe rotation direction. `rotateY()` in the shader applies an inverse rotation, so negating the JS-side value corrects it.
3. **Glow requires no `overflow: hidden`** — The `.earth-container` must not clip its canvas, otherwise the CSS `drop-shadow` filter is cut off at the container edge. The container intentionally has no `border-radius` or `overflow: hidden`.
4. **Dual-render shape cross-fade** — If two adjacent STATES have different `noiseThresh` values, shapes will cross-fade during transitions. Intentional for most state changes; use matching thresholds + seed when a colour-only transition is desired.
5. **Haze div sizing** — `#haze-layer` is `calc(var(--earth-size) * 1.021)`, not `--earth-size`. The projected sphere is 2.1% wider than `--earth-size` (camera geometry). Using `--earth-size` leaves a thin sphere rim outside the haze boundary, creating a visible layering artifact.
6. **Haze gradient keyword** — The gradient uses `circle closest-side`, not the default `circle` (which is `farthest-corner`). On a square div, `farthest-corner` extends the gradient to the corners, making the haze bleed outside the sphere as a square shape. `closest-side` locks the gradient to the inscribed circle.
7. **Progressive reveal clip-path** — `#eon-reveal-path` uses a conic sector (not a full rectangle) for the clip. When `hourDeg >= 360`, the path is set to a full bounding rectangle `M 0 0 H 400 V 400 H 0 Z` — an arc path at exactly 360° can have degenerate start/end points. When `hourDeg <= 0`, `d` is set to empty string (nothing revealed).
8. **Event hit areas in persistent-layer** — Hit areas (`#event-hit-areas`) are in `#persistent-layer` (always on top) while visual dots (`#event-markers`) are also in `#persistent-layer` above `#position-indicator`. Both are toggled via JS when the eon layer is hidden, not via the layer's CSS `hidden` class.
9. **Handle latch only during scrub** — `_handleLatched` must only be set when `scrub.active` is true. If set without an active scrub, the handle stays in outline state permanently (no `exitScrub` to reset it).
10. **12-hour geological cycle** — `timeToMa` uses `(hours % 12) / 12`. Both 3am and 3pm map to the same geological time. The dark haze and scrubber position both track the 12-hour cycle.
11. **Scrub time uses cumulative angle, not `scrub.ma`** — `scrub.ma` is clamped to 0–4540 and can't track multiple revolutions. Time display during scrub must use `scrub.cumulativeAngleDelta` (raw accumulated angle) + `scrub.displayStartSecs` (time at drag start). Never derive displayed time from `scrub.ma` alone — it will lock the display to a single 12-hour window.
12. **"Earth forms" dot at 12 o'clock ambiguity** — Both 0 Ma (present) and 4540 Ma (Earth forms) map to the 12 o'clock position on the ring. Without a Ma-proximity check, the Earth forms event triggers near end-of-cycle (~65 Ma / 23:49 local time) because the scrubber visually overlaps the dot. Fixed by requiring `|EVENTS[i].time - currentMa| < 300` alongside the pixel-distance check in `updateEventMarkerStates`. The 300 Ma threshold is safely between the ~65 Ma end-of-cycle position and the 4540 Ma start-of-cycle.
13. **Approach transitions in dual-render** — When state A and state B use different `surfaceApproach` or `cloudApproach` values, the uber-shader executes both branches per pixel during the blend. This is correct (each state renders with its own approach, then they cross-dissolve), but means approach-boundary transitions (e.g. topographic→watercolor at Hadean→Steam World) are heavier on the GPU than same-approach blends. Not a problem at current complexity but worth knowing if adding more expensive approaches.
14. **Topographic thresholds are coupled to ridgedFbm** — If a topographic state's `surfaceApproach` is changed to screenprint without re-tuning thresholds, the high `noiseThresh1`/`noiseThresh2` values (0.75–0.80) will make the surface nearly invisible because fbm output rarely reaches that high. Always re-tune thresholds in the colour lab when changing approach.

---

## Future Directions

### Backlog
- [x] Phase colour review pass — all 15 states tuned in `colour-lab.html`, exported via `palette-js.md`
- [x] Finalise surface approach per phase — topographic for Hadean, watercolor for Steam World, screenprint for everything else
- [x] Finalise cloud approach per phase — warped_layers for early/thick atmospheres, warped for transitional states, warped_wisps for post-snowball
- [x] Finalise haze colours per phase — tuned per-state in colour lab, applied to production
- [x] Implement multi-approach uber-shader — renderSurface + computeCloudMask branch on per-state uniforms
- [ ] Visual QA pass on approach transitions — verify Hadean→Steam World (topographic→watercolor) and Steam World→Archean (watercolor→screenprint) dual-render cross-fades look correct in production
- [ ] Noise on scrubber handle (multi, 0.5, 15% opacity)
- [ ] Eon/era labels on rings
- [ ] Mobile touch optimisation (tap for tooltips)
- [ ] "Humans in the last second" callout
- [ ] Watch app / mobile app
- [ ] Sound design

### Data Sources
- Paleogeographic SDFs: Scotese PaleoMAP via `typpo/ancient-earth` (GitHub), CC-BY
- ICS stratigraphic data: `github.com/TobbeTripitaka/strat2file`

### Project Files
- `palette-js.md` — colour-lab export of all 15 states' tuned values (palette, haze, thresholds, approaches). The authoritative source for STATES data; if values need re-tuning, update here first, then re-apply.
- `implement_palette.py` — Python script that applies `palette-js.md` values to `eona.html`. Adds the uber-shader architecture (ridged noise functions, multi-approach branching, approach uniforms) and replaces all STATES entries. Re-runnable: takes a stock `eona.html` and outputs the patched version.
- `colour-reference.md` — human-readable documentation of each phase's palette rationale and colour slot roles.
- `colour-lab.html` — interactive per-phase editor for palette, shader approach, haze, and render parameters.
- `cloud-compare.html` — side-by-side cloud approach comparison (4 globes).
- `surface-compare.html` — side-by-side surface approach comparison (5 globes).
