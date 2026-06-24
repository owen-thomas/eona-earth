# Clock.html Redesign Plan

## Context

Major visual and structural redesign of `clock.html` to achieve a cleaner, more unified aesthetic: smaller earth, two wide gradient rings (eon + outer), dynamic accent colour from the globe, new typography, repositioned UI elements, and extended future eons. The reference image shows the target: teal-tinted rings matching the Archean globe, white scrubber handle, event info at bottom, timestamp/time at left/right margins.

The existing codebase already has AM/PM time model (past/future), `FUTURE_EVENTS`, `FUTURE_PHASES`, and `body.future` class switching. The redesign builds on this foundation.

## File

All changes target **`clock.html`** (~2776 lines, single self-contained file).

## New Layout Geometry

Center at (200, 200) in SVG units. Full clock radius = 200.

| Zone | Inner r | Outer r | Width | % of diameter |
|------|---------|---------|-------|---------------|
| Earth | 0 | 66 | 66 | 33% |
| Eon ring | 66 | 126 | 60 | 30% (2×15%) |
| Outer ring | 126 | 186 | 60 | 30% (2×15%) |
| Margin | 186 | 200 | 14 | 7% |

Current values for reference: earth r≈90 (45%), eon ring r=178 filled pie, scrubber orbit r=156, ticks r=178–200.

## Implementation Phases

### Phase 1: Layout Foundation + Typography

**Goal**: New proportions, new font, repositioned info elements. Rings still render as old-style SVG pies but at correct radii.

**CSS variables** (lines 31–56):
- `--earth-size: calc(var(--clock-size) * 0.33)` (was 0.405)
- `--earth-canvas-size: calc(var(--earth-size) * 1.25)` (unchanged ratio)
- Remove `--ring-r` and `--scrub-orbit-r`; add:
  - `--eon-inner-r: calc(var(--clock-size) * 66 / 400)` (≈ 178px)
  - `--eon-outer-r: calc(var(--clock-size) * 126 / 400)` (≈ 340px)
  - `--outer-ring-inner-r: calc(var(--clock-size) * 126 / 400)`
  - `--outer-ring-outer-r: calc(var(--clock-size) * 186 / 400)` (≈ 502px)
  - `--margin-r: calc(var(--clock-size) * 200 / 400)`

**Font swap**:
- Download Space Grotesk Regular (400) and Bold (700) woff2 files → `fonts/` directory
- Replace `@font-face` declarations (lines 10–30): remove Space Mono + Fraunces, add Space Grotesk
- Update `--font-mono` → `--font-sans: 'Space Grotesk', sans-serif`
- All text: 10px, `letter-spacing: 0.1em`, `font-family: var(--font-sans)`
- Bold for event title only

**Remove toggles**:
- Delete `#ring-layers-svg` group (lines 372–391) from HTML
- Delete toggle CSS (lines 78–99, 244–247)
- Delete toggle JS (lines 2318–2325)
- Layers are always visible (no toggle state management)

**Reposition info elements**:
- Replace SVG `<textPath>` info (lines 393–404) with HTML `<div>` elements positioned in the margin
- New markup inside `.clock-container`:
  - `#margin-top` — logo, centered at 12 o'clock in the 14-unit margin band
  - `#margin-left` — timestamp (`#years-display`), centered at 9 o'clock, rotated -90°
  - `#margin-right` — current time (`#time-display`), centered at 3 o'clock, rotated 90°
  - `#margin-bottom` — era display, event name (bold, accent), event description (regular, white)
- Position with `position: absolute; top/left/transform` to center within the margin band
- Update `updateDeepTimeDisplay()` and `updateTimeDisplay()` to target new elements
- Remove the SVG arcs (`#arc-ring-bottom`, `#arc-ring-top`) and their `<defs>`

**Event description relocation**:
- Move `#event-desc-center` from its current position to `#margin-bottom`
- Restyle: Space Grotesk Regular 10px (was Fraunces 18px)
- `#era-display` stays as text element (renamed/repositioned within bottom margin)
- Event name: new `#event-name` element, Space Grotesk Bold 10px, accent colour
- Event description: `#event-desc`, Space Grotesk Regular 10px, white

**Logo repositioning**:
- Move `#logo-clock` to top margin area (currently positioned above earth center; move to outer margin at 12 o'clock)

**SVG radius updates** (functions to modify):
- `drawEonRing()` (line 1876): `r = 178` → `r = 126`, pie slices drawn to new radius
- `drawClockHourMarkers()` (line 1958): minute ticks to outer ring zone (126–186), hour ticks to same zone
- `drawPositionIndicator()` (line 2076): orbit radius `156` → `126`
- `drawEventMarkers()` (line 1998): orbit radius `156` → `126`
- `updateEonReveal()` (line 1833): clip-path radius `250` → adjust to cover new eon ring
- Eon clip circle (line 322): `r="180"` → `r="128"` (slightly larger than outer ring to include edge dots)
- Ghost handle position (line 368): `cy="44"` → recalculate for r=126 orbit

**Earth shadow update**:
- Currently full clock diameter. Keep as-is (vignette behind earth still works).

**Haze/dark-haze sizing**:
- `calc(var(--earth-size) * 1.021)` — recalculates automatically since `--earth-size` changes.

**Scrubber handle size**:
- Currently r=22 visual, r=24 grab. May need adjustment relative to new ring width (60 SVG units). Keep r=22 for now; revisit after visual check.

---

### Phase 2: Ring System (CSS Conic Gradients)

**Goal**: Replace SVG pie-slice eon ring and minute-hand line with CSS gradient-filled annular rings.

**New HTML elements** (inside `.clock-container`, above SVG layers):
```html
<div id="eon-ring-bg"></div>        <!-- solid black backing circle -->
<div id="eon-ring-div"></div>       <!-- conic gradient eon ring -->
<div id="outer-ring-div"></div>     <!-- conic gradient outer ring (replaces minute hand) -->
<div id="ring-shadow-overlay"></div> <!-- radial shadow on both rings -->
<div id="minute-shadow"></div>      <!-- angular shadow on earth -->
```

**Eon ring (`#eon-ring-div`)**:
- Circular div, diameter = 2 × 126 SVG units (scaled to px)
- CSS `mask: radial-gradient(circle, transparent 52.4%, black 52.4%)` (52.4% = 66/126 inner/outer ratio)
- Background: single `conic-gradient(from -90deg at center, ...)` with stops for each eon
- Each eon segment: gradient from dark tint → lighter tint (colours derived from current accent)
- Per-eon opacity baked into RGBA: Hadean 40%, Archean 60%, Proterozoic 80%, Phanerozoic 100%
- Progressive reveal via CSS mask composition: `mask: [annular mask], [conic reveal mask]`
  - The conic reveal mask sweeps from 12 o'clock to the current handle position (same logic as current `updateEonReveal`)
- Updated each frame: `eonRingDiv.style.background = conic-gradient(...)` with new accent-derived colours

**Eon ring backing (`#eon-ring-bg`)**:
- Same diameter as eon ring outer edge
- Solid `#000000`, `border-radius: 50%`
- Prevents the outer ring gradient from bleeding through

**Outer ring (`#outer-ring-div`)**:
- Circular div, diameter = 2 × 186 SVG units (scaled to px)
- CSS `mask: radial-gradient(circle, transparent 67.7%, black 67.7%)` (67.7% = 126/186)
- Background: `conic-gradient(from Xdeg at center, ...)` where X = minute hand angle
- Stops: `rgba(accent-dark, 0) 0%, rgba(accent-dark, 0) 50%, rgba(accent-dark, 1) 88%, rgba(accent-dark, 1) 100%`
- "Minute hand" = the hard 100%→0% opacity jump at the gradient origin
- Rotates each second: update `from Xdeg` based on current minute+second

**Ring shadow overlay (`#ring-shadow-overlay`)**:
- Same diameter as outer ring outer edge (186 SVG units)
- `background: radial-gradient(circle closest-side, rgba(0,0,0,1) 70%, rgba(0,0,0,0) 100%)`
- Sits on top of both rings

**Minute shadow on earth (`#minute-shadow`)**:
- Same diameter as earth
- `background: conic-gradient(from Xdeg, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0) 25%, rgba(0,0,0,0) 100%)`
- X tracks minute position, hard stop at minute angle
- `border-radius: 50%`, positioned over earth

**Remove old ring rendering**:
- `drawEonRing()`: gutted — no longer draws SVG pie slices. May keep a simplified version that sets clip paths for event marker visibility, or remove entirely if CSS handles reveal
- Remove `#minute-hand` line element and central dot from clock-layer SVG
- Remove `#clock-hands` group
- Minute hand fade logic in `enterScrub()`/`exitScrub()` replaced by outer ring gradient opacity

**New per-frame update function**: `updateRings(ma, minuteAngle, accentRgb)` — called from `tick()`, updates:
1. Eon ring conic-gradient stops (accent-derived colours)
2. Eon ring reveal mask (progressive disclosure)
3. Outer ring gradient origin angle
4. Minute shadow angle

---

### Phase 3: Dot System

**Goal**: Replace line tick marks with circular dots. Progressive loading/unloading.

**Modify `drawClockHourMarkers()`** → rename to `drawClockDots()`:
- **60 minute dots**: SVG `<circle>` r=0.5 (1px diameter) at r=186 (outer ring edge)
  - Each dot: `fill: #ffffff`, `opacity: 0` initially
  - ID or data attribute for addressability: `data-minute-index="0..59"`
- **12 hour dots**: SVG `<circle>` r=1 (2px diameter) at r=186 (outer ring edge)
  - Each dot: `fill: #ffffff`, `opacity: 0` initially
  - ID or data attribute: `data-hour-index="0..11"`

**Progressive loading logic** — new function `updateDotVisibility(hours, minutes)`:
- **Minute dots**: At minute M of any hour, dots 0..(M-1) are visible (opacity 1). Dot at index i appears at the position for minute i on the clock face.
- **Hour dots (AM, hours 0–11)**: At hour H, dots 0..(H-1) are visible.
- **Hour dots (PM, hours 12–23)**: At hour H, dots 0..(23-H-1) are visible (unloading from top). Dot at 12 o'clock disappears first, then 1 o'clock, etc.
- Called each frame from `tick()` (but only when minute or hour changes — deduplicated).

**Event marker repositioning**:
- `drawEventMarkers()` (line 1998): orbit radius 156 → 126 (outer edge of eon ring)
- Hit area radius may need scaling relative to new ring width

**Handle-overlapping dots**:
- In `updateEventMarkerStates()`: dots within r=22 of scrubber handle center → `fill: #999999` (was: ignored or black)
- This replaces the current "active dot = black" logic for overlapping dots

---

### Phase 4: Colour System

**Goal**: Dynamic accent colour from globe state, replacing hardcoded `#E34E2A`.

**Add `accentColor` field to STATES** (lines 656–836):
- Each of the 14 STATES entries gets `accentColor: '#hex'` — a representative colour derived from the dominant palette colour
- e.g. Molten Hadean: warm red/orange; Hazy Archean: teal; Modern Earth: blue-green
- Pre-parsed to RGB at startup (alongside `hazeRgb`, `glowRgb`, `darkHazeRgb`)

**Compute interpolated accent each frame**:
- In `updateEarth()` (or a new helper), blend `accentColor` between states A and B using the same `t` blend factor
- Store result in a global `_currentAccentRgb` and `_currentAccentHex`
- Update CSS variable: `document.documentElement.style.setProperty('--accent', _currentAccentHex)`

**Derive ring tints from accent**:
- Dark tint for rings: scale accent RGB to #1–#3 range → `Math.round(channel * 0.15)` approximately
- Lighter tint: scale to #4–#6 range → `Math.round(channel * 0.35)`
- These are parameters to `updateRings()`

**Replace all `#E34E2A` references**:
- CSS `--accent` variable (line 40): now set dynamically from JS each frame
- Ghost handle stroke (line 368): changed to use CSS variable or set via JS
- `_cachedAccent` (line 2631): reads from the dynamically updated `--accent`
- `_applyHandleOutline()`: solid state fill = `#ffffff` (was accent). Handle is now always white.
- Active event marker overlay: fill = `_currentAccentHex` (was conditional accent/black)
- Event name text: accent colour

**Scrubber colour changes**:
- Handle fill at rest: `#ffffff` (was `#E34E2A`)
- Handle outlined (scrubbing): transparent fill + `#ffffff` stroke (unchanged — was white)
- Ghost handle stroke: `_currentAccentHex` (was `#E34E2A`)
- Hover colour: lighter white or no hover colour change (the orange hover is no longer needed since handle is white)

**Remove `body.future` accent override**:
- Currently `body.future { --accent: #7461EE; }` (line 100). No longer needed — accent comes from STATES.

**Eon ring colours**:
- All eon segments tinted based on `_currentAccentRgb`, not their own geological palette
- Dark → lighter gradient within each eon: darkTint at start → lighterTint at end
- Per-eon opacity: Hadean 40%, Archean 60%, Proterozoic 80%, Phanerozoic 100%

---

### Phase 5: Future Eons + Content

**Goal**: Define Greek-root future eons, extend Phanerozoic into PM, eon wiping behaviour.

**Consolidate past eras into Phanerozoic**:
- `pastSlices` in `drawEonRing()`: remove Paleozoic/Mesozoic/Cenozoic. Keep:
  - Hadean (4540–4000), Archean (4000–2500), Proterozoic (2500–538.8), Phanerozoic (538.8–0)
- `ERAS` array: keep for `getCurrentEra()` display but ring only shows 4 eons

**Define future eons** (new `FUTURE_EONS` array):
- Names TBD (Greek roots): ~4 future eons between the end of Phanerozoic and Earth's end
- Example structure:
  ```js
  const FUTURE_EONS = [
    { name: 'Phanerozoic', start: 0, end: -650 },     // continues past noon
    { name: '[Fading life]', start: -650, end: -1000 },
    { name: '[Ocean loss]', start: -1000, end: -2500 },
    { name: '[Dead Earth]', start: -2500, end: -3500 },
    { name: '[Fire return]', start: -3500, end: -4540 },
  ];
  ```
- Opacity reversal: each successive eon gets darker (100% → 80% → 60% → 40% → 16%)

**Phanerozoic extends into PM**:
- The Phanerozoic eon slice starts at 538.8 Ma (AM, near noon) and continues past noon into PM
- On the eon ring, this means the Phanerozoic arc sweeps past 12 o'clock and overlays the Hadean region
- Implementation: the future ring reveal system already supports this — Phanerozoic's future portion renders in the future ring group, revealed progressively as PM advances

**Eon wiping**:
- As PM progresses, new eon slices are revealed. Since the future ring has a black backing, the past ring eons are visually hidden behind it.
- The current `#future-eon-bg` (solid black circle behind future ring) already handles this.

**Timestamp decimal places**:
- `formatMa()` (lines 553–565):
  - `Math.round(ma)` → `ma.toFixed(2)` for MA values (e.g. "17.10 MA")
  - `Math.round(ma * 1000)` → `(ma * 1000).toFixed(2)` for KA values
  - GA already uses `.toFixed(2)`

---

### Phase 6: Polish + Pi Testing

**Scrub interaction updates**:
- Scrub handle detection radius: verify r=22 still works at new orbit r=126
- Ghost handle orbit: match new r=126
- Rotate-only drag: verify bounds checks against new geometry

**Return to now button**:
- Restyle with Space Grotesk, keep accent colour background

**Performance on Pi**:
- CSS conic-gradient updates each frame: test on Pi 5 at 30fps
- If too expensive: update rings only when colour or angle actually changes (dedup like existing haze updates)

## Verification

1. Start dev server / open `clock.html` in browser
2. Check layout: earth 33%, two thick rings, dots visible, correct proportions
3. Scrub through time: rings update, accent colour shifts with globe, eon reveal works
4. Verify AM→PM transition: Phanerozoic extends, future eons appear
5. Check event interaction: highlight with accent, description at bottom, dots #999 near handle
6. Test progressive dot loading: minute dots cycle per hour, hour dots load AM / unload PM
7. Timestamp shows decimals: 17.10 MA, +1.23 GA
8. SSH to Pi, `git pull && sudo reboot`, verify at 30fps on 1080×1080 display

## Open Items

- [ ] Future eon names (Greek roots) — user to decide
- [ ] End-of-Phanerozoic timestamp — user to decide (complex life end ~650 Ma from now)
- [ ] New logo file — user to provide
- [ ] Space Grotesk font files — need to download and bundle
- [ ] Accent colour values per STATES entry — iterate in colour lab
