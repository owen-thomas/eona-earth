# Eona.Earth

A website that maps Earth's 4.5 billion year history onto a 12-hour clock. Midnight = Earth forms. The full sequence repeats twice per day.

## Concept

The clock runs on local time. When you look at it at 10:34, you're seeing the Cambrian explosion. At 11:39, the dinosaurs go extinct. Humans appear within the last 3 seconds before noon/midnight.

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
- **Accent**: `#E34E2A` — used sparingly for position indicator, era labels, events
- **Earth colours**: See `colour-reference.md` for full per-phase palettes

### Typography
- **Space Grotesk**: Primary UI font — margin text, ring labels, general body text (weight 300–700)
- **Space Mono**: Data displays only — `#years-display`, `#time-display` (arc text in the margin ring)
- `-webkit-font-smoothing: antialiased` on body to eliminate subpixel glow on dark backgrounds
- Margin text (`#margin-top`, `.ring-text`) uses `font-size: 8px`, `font-weight: 300`, `letter-spacing: 0.2px` — scales with `--clock-size` via SVG viewBox or proportional CSS
- **Accent text** (`#years-display`): `font-family: 'Space Mono'`, same 8px treatment, `fill: #ffffff`

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

### Layers
1. **Earth** (`#earth-layer`): WebGL sphere, rotates 1 rev/60 s. Haze layers (`#haze-layer`, `#dark-haze-layer`, `#earth-shadow`) share its visibility.
2. **Eons** (`#infographic-layer`): SVG — eon pie slices with progressive reveal.
3. **Clock** (`#clock-layer`): SVG minute hand + 60 minute tick marks (`#clock-hour-markers`). `z-index: 1` so it renders above `#persistent-layer`.

Layers stack bottom-to-top: `#infographic-layer` → `#earth-shadow` → `#earth-layer` → `#haze-layer` → `#dark-haze-layer` → `#persistent-layer` → `#clock-layer` (z-index 1). All layers are always visible — there are no toggle buttons in the current design.

**`#persistent-layer`** — always-visible SVG, containing: `#clock-eon-markers` (12 hour ticks), `#position-indicator` (scrubber handle), `#event-markers` (dots; future vs. past halves swapped by `_doMarkerSwap()`), `#event-hit-areas` (transparent hit circles).

### Interaction
- **Scrub handle** (orange/outline circle, r=24, orbit r=156): drag to scrub through geological time. Globe rotation follows. Acts as the "hour hand" — its position on the ring shows the current geological age.
  - Enters **outline state** (transparent fill + 1px white stroke, 0.5s ease) immediately on grab. Stays outlined until "Return to now" is clicked.
  - Returns to **solid orange** (0.5s ease) on `exitScrub()`.
  - `_handleLatched` flag tracks outline state — only set during `scrub.active`, reset in `exitScrub`.
- **Drag anywhere else** on the clock: rotates the globe only; time stays live.
- **Return to now** button: exits scrub mode, restores handle to orange, restores minute hand + dot. Styled: Space Mono Regular 10px uppercase 1px letter-spacing black (`#000000`), padding 8px 12px, orange fill (`#E34E2A`), pill shape (`border-radius: 999px`). `display: none` by default; `display: block` when `body.scrubbing`. `transform: translateY(8px)` to optically centre it with the time text.
- Pointer events are on `.clock-container` div (not the SVG) so empty-space drags work reliably.
- **Scrub handle detection is geometric** — `pointerdown` converts the click to SVG coordinates and checks distance to the handle centre (r=24 on orbit r=156). Does not rely on `e.target` because hit areas in `#event-hit-areas` sit on top of `_indicatorGrab` in the DOM and intercept events.
- **Grab cursor** is managed on `container.style.cursor` via `mousemove`, using the same geometric distance check. Hit areas have no `cursor` style set so they inherit from the container, ensuring `grab`/`grabbing` always shows over the handle regardless of what element is on top.
- **Handle hover state**: `#F2A08A` when pointer is within r=24 of handle centre and not latched. Tracked via `_handleHovered` flag; applied through `_applyHandleOutline()` to avoid being stomped by per-frame calls.
- **Scrub time display**: while scrubbing, the time display shows the geological clock time (what the clock hand represents) rather than local time. Time display dims to `#666666` when scrubbing (`body.scrubbing #time-display`). Time tracks handle position continuously across 12/24-hour boundaries.
  - **Cumulative angle tracking**: `scrub.cumulativeAngleDelta` accumulates raw angle delta each frame. `scrub.displayStartSecs` stores the displayed time at drag start (carried forward on re-grab). Displayed time = `displayStartSecs + cumulativeAngleDelta / 360 * 43200`, then `% 86400` to wrap. This allows scrubbing past midnight/noon without getting stuck in a 12-hour window.
  - **`lastAngle` is seeded from `maToAngle(initialMa)`** (the handle's true centre angle) — not the pointer's click position. The click offset is absorbed into the first pointermove delta, keeping handle position and displayed time locked to a single source of truth. Seeding from the pointer angle instead caused up to ~17 min of error per grab (click edge of 24px handle on 156px orbit ≈ 8.7° offset ≈ 17 min), compounding across re-grabs.
  - On re-grab (while `scrub.active`): `displayStartSecs` is set to the current displayed time (not real local time) so no jump occurs.
- **Minute hand + central dot**:
  - Hidden (0.3s ease) when scrubbing starts.
  - Stay hidden until "Return to now" is clicked (not restored on drag release).
  - When scrubbing: minute hand tracks the scrubber position (whole-minute snapping, no motion blur). Angle = `maToAngle(scrub.ma) + 90`.

---

## Technical Implementation

### Stack
- Vanilla JS + HTML + CSS — single source file (`eona.html`) with `<!-- @if WEB/PI -->` build directives
- Three.js r128 (CDN on web; local `lib/three.r128.min.js` on Pi)
- Google Fonts CDN (Space Grotesk + Space Mono) on web; local woff2 files on Pi
- `build.sh` preprocesses `eona.html` into:
  - `dist/web/index.html` + `dist/web/images/` — served by Vercel and `server.js`
  - `dist/pi/clock.html` — deployed to the Raspberry Pi

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
_handleHovered      // true when pointer is within r=24 of handle centre; drives hover colour via _applyHandleOutline()
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
A Three.js `SphereGeometry` (radius 1, 48×48 segments on web / 32×32 on Pi) with a custom `ShaderMaterial`. The fragment shader uses **screenprint** surface rendering and **warped_wisps** cloud rendering — single branches, no approach switching at runtime. Surface is rendered twice per pixel (dual-render A/B) so adjacent STATES cross-dissolve cleanly while each keeps its own noise seed. `CLOUDS_ENABLED = true`.

### Camera & Canvas Sizing
- Camera: `PerspectiveCamera(45°, 1, 0.1, 100)`, positioned at `z = 3.12`
- Projected sphere diameter = **1.021 × `--earth-size`** (derived: `arcsin(1/3.12)` = 18.70°, fraction of half-FOV = `tan(18.70°)/tan(22.5°)` = 0.817; × 1.25 canvas ratio = 1.021)
- `--earth-size: calc(var(--clock-size) * 0.33)` — globe is 33% of the clock face diameter
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

⚠️ These thresholds assume **fbm noise** (screenprint). The **topographic approach** (colour lab only) uses `ridgedFbm`, which has a different output distribution (skewed toward 1.0) — it needs `t1=0.80, t2=0.79` or similar high values that would make land invisible on screenprint. If you experiment with topographic in the colour lab, re-tune thresholds before comparing — they are not interchangeable.

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

**Hadean phases** keep `cloudDensity: 0.00` — no atmosphere renders there regardless of `CLOUDS_ENABLED`.

### Surface Approach System
The production shader uses **screenprint** only — hard-edged fbm ink zones, narrow smoothstep (0.04). The Icinori riso aesthetic. All phases use this approach; `surfaceApproach` field on STATES entries is retained for the colour lab but ignored by the production shader.

All SDF-era phases must use screenprint (the data-driven land/sea path only applies screenprint noise for modulation).

Other approaches exist in `colour-lab.html` as lab-only options:
- **watercolor** — domain-warped fbm, wide smoothstep (0.18). Soft, organic.
- **topographic** — ridged multifractal with contour-line character. Requires `ridgedFbm()`.

⚠️ Topographic thresholds are calibrated for ridgedFbm output distribution. If you change any phase's `surfaceApproach` field in the colour lab, re-tune `noiseThresh1`/`noiseThresh2` — fbm and ridgedFbm have different distributions and shared thresholds will make land invisible or solid.

### Atmospheric Glow
Applied as a CSS `filter: drop-shadow()` on `#earth-layer` each frame via `updateEarth()`. Two stacked shadows (tight core + soft halo) are used for a hot-core feel. Strength and colour are interpolated between STATES A and B alongside the surface blend. Set `glowStrength: 0` on states with no glow.

**Phases with glow currently:** Molten Hadean early (0.80), late (0.55), Steam World (0.20 — residual cherry red fading to 0). All other phases: 0.0.

### Atmospheric Haze Layer
A CSS `#haze-layer` div sits above the WebGL canvas. Each frame `updateEarth()` sets its background to a radial gradient and its opacity to the interpolated per-state value. Visibility is tied to `#earth-layer`.

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

Visibility is tied to `#earth-layer`.

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
| `surfaceApproach` | string | Data only — production shader uses `'screenprint'` on all phases; colour lab reads this field |
| `cloudApproach` | string | Data only — production shader uses `'warped_wisps'` on all phases; colour lab reads this field |

Current STATES sequence (14 entries):

All blends use **smoothstep easing** (slow → fast → slow). Transition style noted per entry.

| # | Name | Span (Ma) | Surface | Clouds | Transition in | Transition out |
|---|------|-----------|---------|--------|---------------|----------------|
| 0 | Molten Hadean (early) | 4540–4420 | screenprint | warped_layers | — | Full-span drift. Glow 0.80. |
| 1 | Molten Hadean (late) | 4420–4300 | screenprint | warped_layers | Full-span | 30 Ma ramp into Steam World. Glow 0.55. |
| 2 | Steam World | 4300–4000 | screenprint | warped_layers | 30 Ma ramp | 60 Ma ramp. Glow 0.20 fading to 0. |
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

For palette details and colour rationale for each phase, see **`colour-reference.md`**.

---

## SVG Layers

### `#infographic-layer` (Eons)
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

### `#clock-layer` (Clock, z-index: 1)
- **`#clock-hour-markers`**: 60 minute ticks, `#666666`, 1px stroke. Inner edge r=180, outer edge r=200.
- **`#clock-hands`**: Minute hand only (`#minute-hand`) — white line, stroke-width 2. Central dot r=8 (16px diameter).

### `#persistent-layer` (non-toggleable — always visible)
- **`#clock-eon-markers`**: 12 hour ticks, `#666666`, 1px stroke. Inner edge r=160, outer edge r=180. Always visible on all layers.
- **`#position-indicator`**: Scrubber handle — persistent SVG circle, r=24, orbit r=156. Solid orange (`#E34E2A`) at rest; outline state (transparent fill + 1px white stroke) during scrub. CSS transition `fill 0.5s ease, stroke 0.5s ease`.
- **`#event-markers`**: Event dots, r=2, orbit r=156. White normally; black when active (hidden behind overlay). Dots with `data-event-future` are swapped in/out via `_doMarkerSwap()` when the clock crosses the present/future boundary. Contains `#event-marker-overlay` — a single extra dot always appended last so it paints on top of all others; positioned over the active dot each frame and coloured orange (handle outlined) or black (handle solid). Ensures the active dot is never obscured by a neighbouring dot.
- **`#event-hit-areas`**: Transparent hit circles r=12, `pointer-events="all"`. Disabled (`pointer-events="none"`) when eon layer is hidden.

---

## Event Marker Behaviour

- **Dot states**: white (default) → orange (active, handle outlined) → black (active, handle solid) — 0.5s ease transition
- **Active zone**: scrubber centre within ±4px of a dot AND within 300 Ma of the event's geological time → that dot activates. The Ma-proximity check prevents the "Earth forms" dot (at 12 o'clock = 4540 Ma) from triggering near end-of-cycle (0 Ma), which maps to the same clock position. Only one active at a time (closest wins).
- **Overlap zone**: scrubber centre within 24px of any dot → handle enters outline state (latched for duration of scrub).
- **Hover**: hovering a hit area turns the dot orange. Floating tooltip is disabled (`showTooltip` returns immediately).
- **Event active in arc text**: when an event activates, `showEventDescription(event)` replaces `#era-display` (bottom arc) with the event name (bold, accent colour) + description inline. `_activeEventMa` is set to the event's time.
  - **Timestamp locking**: `updateDeepTimeDisplay` locks `#years-display` to the event time while `ma >= _activeEventMa` (scrubber approaching or at event). Once `ma < _activeEventMa` (scrubber passes the event toward present), years-display resumes live time — even if the era arc is still showing the event.
  - `hideEventDescription()` restores `#era-display` to the normal eon/era label from `getEonLabel(ma)`.

---

## UI — Clock Face

There is no bottom info bar. All UI lives inside the clock circle: arc text around the inner rim, a margin strip above, and a ghost handle for scrub position.

**Arc ring text** — three `<textPath>` elements in `#persistent-layer`, each following a circular arc inside the clock ring:
- `#years-display` (left arc, `#arc-ring-left`): geological age in Ma — Space Mono, `fill: #ffffff`, 8px.
- `#era-display` (bottom arc, `#arc-ring-bottom`): current eon/era name — Space Grotesk weight 300, `fill: #999999`, 8px.
- `#time-display` (right arc, `#arc-ring-right`): local time — Space Mono, `fill: #999999`, 8px.

**Margin top** — `#margin-top` div above the clock circle, holds the logo:
- `#logo-clock`: `<img src="images/logo-clock.svg">`. Width: `calc(var(--clock-size) * 84 / 1080)` — proportional to clock size.

**Images directory:**
- `images/logo-clock.svg` — clock-specific wordmark/logo
- `images/favicon.png` — browser tab icon (`<link rel="icon">` in `<head>`)

**Ghost handle** (`#ghost-indicator` / `#ghost-handle`) — appears while scrubbing. An outline circle (r=16.5, `stroke: #E34E2A`, transparent fill) positioned at the real local-time angle. Fades in after a brief delay so it doesn't flash on short scrubs. `display: none` by default; `display: block` when `body.scrubbing`. Opacity managed by JS (not CSS class) so it can fade smoothly in and out independently of the `body.scrubbing` class.

---

## Colour Reference

See **`colour-reference.md`** for:
- Full 5-stop palette (`c0`–`c4`) for every phase
- Coverage rationale for each colour slot
- Atmosphere/glow notes per phase
- Palette design principles

---

## Render Labs

### Design Decisions (from prior render lab work)

**Cloud approaches evaluated:** warped, ridged_wisps, warped_layers, warped_wisps. Warped Wisps selected as the primary production approach — brushstroke feel without stiffness. Per-state approach variation adopted for realism range: warped_layers for heavy early atmospheres (pre-GOE), warped for transitional/snowball phases, warped_wisps for post-snowball through Modern.

**Surface approaches evaluated:** screenprint, watercolor, topographic. Screenprint selected for all phases — the Icinori riso aesthetic holds across geological eras. SDF continent phases require screenprint specifically: watercolor bleed and topographic ridges fight coastline readability. The procedural (pre-SDF) eras can push harder stylistically but screenprint is consistent enough to keep.

### `colour-lab.html` — Colour Lab

Unified per-phase editor for palette, shader approach, haze, and render parameters. Single raw-WebGL globe (quad-shader, no Three.js) with CSS haze overlays, matching the production rendering pipeline. Three-column layout: phase list → globe + colour picker → shader controls.

**Layout:**
- **Top strip** — all 14 phases as stacked c3→c0 colour bands; click to jump.
- **Left panel** — scrollable phase list with 4 swatches per phase. Click any swatch to edit. Active phase highlighted with `#E34E2A` index number.
- **Centre: globe** — 240px WebGL globe rendered via a fullscreen-quad fragment shader (no geometry). Light haze and dark haze are CSS div overlays on top, using the production `radial-gradient(circle closest-side ...)` approach. Rotation is west-to-east (negative angle in `rotY` convention). Clouds rotate independently at a separate speed.
- **Centre: colour wheel** — HSL gradient wheel (radius = saturation, angle = hue) rendered to a 400×400 canvas, displayed at 200px. Lightness slider below. Crosshair tracks current position. Direct hex input with swatch preview.
- **Centre: haze pickers** — Light Haze and Dark Haze colour circles below the c0–c3 slots. Click to switch the colour wheel target to `hazeColor` or `darkHazeColor`. Opacity sliders for each, writing to `hazeOpacity` and `darkHazeOpacity` on the active phase.
- **Right panel: surface controls** — Approach tabs (Screenprint, Watercolour (lab), Topographic (lab)), Thresh 1, Thresh 2, Intensity, Speed sliders. SDF phases (`useLandSea > 0`) grey out lab approaches. Lab tabs are for visual comparison only — production shader uses screenprint on all phases.
- **Right panel: cloud controls** — Approach tabs (Warped (lab), Ridged Wisps (lab), Warped Layers (lab), Warped Wisps), Density, Shape, Speed sliders. Warped Wisps is the production approach; the others are lab-only tabs for comparison.
- **Bottom global bar** — Toggles for Clouds, Light Haze, Dark Haze (apply across all phases). Grain slider (global). Undo button (per-phase stack). Reset Phase button (reverts active phase to original prod values). Copy Palette JS export button.

**Shader architecture:** The globe compiles a fragment shader by concatenating `PREAMBLE + SURF_FN[key] + CLOUD_FN[key] + MAIN_FN`. Switching surface or cloud approach triggers a recompile. Switching phases also forces recompile (clears `currentSurfKey`/`currentCloudKey`). Uniform locations are cached per-program.

**Per-phase state fields managed by colour lab:**
- `palette` (5 hex strings, c0–c4)
- `hazeColor`, `hazeOpacity`, `darkHazeColor`, `darkHazeOpacity`
- `noiseThresh1`, `noiseThresh2`, `surfaceIntensity`
- `cloudDensity`, `cloudShape`
- `surfaceApproach` — stored per-phase for the colour lab; production shader always uses `screenprint`
- `cloudApproach` — stored per-phase; production shader always uses `warped_wisps`

**Undo system:** One undo snapshot pushed per drag gesture (not per frame), using a `_undoPushedThisDrag` flag. `pointerdown` on any interactive control pushes a deep-copy of the full phase state; subsequent `input` events during the same drag do not push. `pointerup` resets the flag. 50-deep stack per phase. Cmd/Ctrl+Z keyboard shortcut. Reset Phase pushes an undo before reverting.

**Keyboard navigation:** Arrow keys or vim `hjkl`. Up/down = phase. Left/right cycles through targets: `c0 → c1 → c2 → c3 → hazeColor → darkHazeColor`.

**Export:** "Copy Palette JS" button writes all 14 phases' palette, haze, threshold, cloud, and approach values to the clipboard as JS-ready snippets. Paste directly into the `STATES` array in `eona.html`.

---

## Physical Build — Raspberry Pi

### Hardware

**Components:**
- Raspberry Pi 5 (2GB RAM) — VideoCore VII handles the WebGL shader without crashing
- Waveshare round display (1080×1080, 8" diameter)
- Micro-HDMI to HDMI adapter
- Waveshare M.2 Adapter with Active Cooler (PCIe via FFC connector; temperature-controlled blower fan)
- Kingston 256GB 2230 NVMe SSD (boots via M.2 adapter — replaces SD card)
- Raspberry Pi 27W USB-C Power Supply

**Wiring:**

| Display port | Connects to |
|---|---|
| HDMI | Pi 5 **HDMI0** (micro-HDMI closest to USB-C power port) |
| USB-C (touch) | Pi USB 3 port (blue) — USB 2 underpowers it |
| USB-C (power) | Pi USB 2 port (black) — 300mA draw, no data needed |

Single wall cable: only the Pi's USB-C power supply runs to the wall. Display is powered from the Pi.

**Mounting:** Pi fastened to back of display via hex standoffs (busy side facing inward). Assembly depth: **54mm** — standoffs + display PCB + Pi board + active cooler stack. SSD mounts flat alongside heatsink, does not add height.

**Mounting:** No enclosure — hanging open-back. Front: clean black circle, thin edge. Back: Pi 5 PCB, gold standoffs, braided HDMI cable. Reads as intentional. Wire from top two standoffs (58mm apart) to a single wall hook; thin picture wire or eye bolt standoffs for a cleaner attachment point. White USB-C power cable exits at bottom to wall — accepted.

**Audio (deferred):** Display board has NS4263 mono 3W amp with PH1.25 JST "Speaker" connector and 3.5mm audio input. Speaker needed: 8Ω 2W, PH1.25 connector — Waveshare 2030 Cavity Speaker. Confirm HDMI audio routing with `aplay -l` before purchasing.

### Software

**OS:** Raspberry Pi OS (Debian Trixie), Wayland display server. Hostname: `eona` (`eona.local`). User: `pi`.

**Repo:** `https://github.com/owen-thomas/eona-earth.git`, cloned to `~/eona`. Served from `~/eona/dist/pi/clock.html` (built from `eona.html` by `build.sh`).

**Offline assets** — bundled locally, no internet required:
- `lib/three.r128.min.js`
- `fonts/space-grotesk-variable.woff2`, `fonts/space-mono-400.woff2`, `fonts/space-mono-700.woff2` — note: the Pi `@font-face` block declares only Grotesk + Mono 400; Mono 700 has no face declared (synthetic bold — fix scheduled in BUILD-SYSTEM-PLAN.md C3). `fonts/fraunces-400.woff2` is bundled but unreferenced.
- Logo SVG referenced as `images/logo-clock.svg`

**Autostart** (`~/.config/autostart/clock.desktop`):
```ini
[Desktop Entry]
Type=Application
Name=Clock
Exec=chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --password-store=basic file:///home/pi/eona/dist/pi/clock.html
```

Key flags: `--password-store=basic` suppresses keyring prompt; `--kiosk` is full-screen. `--disable-gpu` and `--enable-unsafe-swiftshader` are **not needed** on Pi 5 — VideoCore VII handles WebGL with hardware rendering.

**Update workflow:**
```bash
ssh pi@eona.local
cd ~/eona && git pull && ./build.sh pi && sudo reboot
```

Pi runs Wayland — `DISPLAY=:0` does not work from SSH. Reboot is the standard way to reload Chromium after a pull.

### Pi Build — `@if PI` Differences

`dist/pi/clock.html` is produced by `./build.sh pi`. The `<!-- @if PI -->` blocks swap in these differences from the web build:

| Feature | Web build | Pi build |
|---------|-----------|----------|
| Three.js | CDN | `lib/three.r128.min.js` (local) |
| Fonts | Google Fonts CDN | `@font-face` from local woff2 files |
| `--clock-size` | `min(calc(100vw - 48px), calc(100vh - 48px))` | `1080px` fixed |
| `html, body` | responsive, flexbox centred | `1080px × 1080px`, `overflow: hidden` |
| `.clock-container` | `position: relative; width: var(--clock-size)` | `position: absolute; inset: 0; width: 1080px` |
| Renderer | `antialias: true`, native DPR, `setSize(size, size)` | `antialias: false`, DPR=1, `setSize(size × 0.5, size × 0.5)` + CSS scale ×2 |
| Sphere geometry | `SphereGeometry(1, 48, 48)` | `SphereGeometry(1, 32, 32)` |
| `CLOUDS_ENABLED` | `true` | Conditional: cloud function absent from GLSL when `false` |

**V3D instruction budget** — Pi 5's limit sits between ~20 and ~24 noise3d-equivalent calls:

| Config | Calls | Result |
|--------|-------|--------|
| Multi-branch cloud (warped + warped_layers) | ~24 | crash |
| warped_wisps + 2-oct ridgedFbm2 + 2-oct warp | ~14 | stable |
| warped_wisps + 5-oct ridgedFbm2 + 2-oct warp | ~20 | **current** ✅ |

### Installation Status

- [x] Mount Pi 5 to display via hex standoffs
- [x] Connect M.2 adapter FFC cable to Pi 5 PCIe connector
- [x] Connect active cooler fan header + 5V/GND GPIO power
- [x] Boot from SD card — clock loads, globe stable, clouds working
- [x] Seat Kingston 2230 NVMe in M.2 slot
- [x] Flash Pi OS to NVMe; set boot order (NVMe first, SD fallback)
- [ ] Check `aplay -l` for HDMI audio device (for future speaker work)

### Known Issues (Pi)

- **SSH password lockout** — After reboot, SSH password auth may fail (caps lock / keyboard layout). Fix: plug in USB keyboard, `Ctrl+Alt+F2` for text console, run `passwd pi`.
- **Chromium package name** — On this Pi OS version, the package and binary are `chromium`, not `chromium-browser`.
- **V3D GPU crash** — Pi 4 cannot run the shader (VideoCore VI limitation, dead end). On Pi 5, the multi-branch cloud function exceeded V3D's instruction limit. Fix: collapse to single warped_wisps branch and wrap the function in a JS template literal conditional so it is absent from the GLSL string entirely when `CLOUDS_ENABLED = false`.
- **Clock showed stale time after power-off (fixed 2026-07-15)** — Root cause was not NTP/timesyncd config (both were already active), but that NetworkManager had **no saved WiFi profile at all** — `nmcli connection show` listed only the wired connection, likely lost during the NVMe OS reflash. With no WiFi credentials to reconnect with, the Pi had no path to NTP after any power loss. Fixed by creating the profile explicitly system-wide and autoconnecting: `sudo nmcli connection add type wifi con-name "home-wifi" ifname wlan0 ssid "<ssid>" -- wifi-sec.key-mgmt wpa-psk wifi-sec.psk "<password>" connection.autoconnect yes connection.permissions ""` (empty `permissions` = available before any user login, not scoped to one user). Verified via cold `sudo reboot` with ethernet unplugged: `wlan0` reconnects automatically and `timedatectl` shows `System clock synchronized: yes` within ~10s. RTC battery (A2 in BUILD-SYSTEM-PLAN.md) was considered as a belt-and-suspenders fix but declined 2026-07-15 (no further hardware spend) — the WiFi/NTP fix is the accepted solution. Known residual: if the WiFi itself is down after a power loss, the clock shows stale time until connectivity returns.

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

---

## Future Directions

### Backlog
- [ ] Keyboard navigation to jump between events
- [ ] Display auto-dim after inactivity; touchscreen tap restores full brightness
- [ ] Scrub without spinning the globe to observe continental drift
- [ ] Future Earth projection — second 12-hour period covering the remaining lifespan of the planet
- [ ] Eon/era labels on rings — curved text along eon pie slices in infographic layer
- [ ] Sound design
- [ ] Watch app / mobile app

### Data Sources
- Paleogeographic SDFs: Scotese PaleoMAP via `typpo/ancient-earth` (GitHub), CC-BY
- ICS stratigraphic data: `github.com/TobbeTripitaka/strat2file`

### Project Files
- `colour-lab.html` — interactive per-phase editor for palette, shader approach, haze, and render parameters.
- `BUILD-SYSTEM-PLAN.md` — plan for hardening `build.sh` and restructuring platform differences (PLATFORM config, OR-list directives) ahead of the desktop target. Phase A closed 2026-07-15 (A1 done; A2 battery declined).
- `DESKTOP-APP-PLAN.md` — Electron desktop widget plan; depends on BUILD-SYSTEM-PLAN.md Phases B–D landing first.
