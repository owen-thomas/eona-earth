# Future Earth — Build Plan

Five phases, each independently testable. Each phase builds on the previous one.

---

## Phase 1 — SDF Atlas Generation

**Goal:** Produce `FUTURE_SDF_ATLAS_BASE64` from the 5 source images.

**Steps:**
1. Write a Python script (`generate-future-atlas.py`) that:
   - Reads `images/future/{50,100,150,200,250}.png`
   - Thresholds each to pure binary (cutoff 128)
   - Generates SDF via Euclidean distance transform (same convention as past atlas: 128 = coast, >128 = land, <128 = sea)
   - Stacks into a single 512x1280 PNG (top to bottom: +50, +100, +150, +200, +250)
   - Outputs base64 string
2. Embed `FUTURE_SDF_ATLAS_BASE64` in `eona.html` alongside the existing atlas constant.

**Verify:** Decode the base64 back to PNG and visually confirm coastlines match the source images. Check SDF gradient looks correct (smooth falloff from coastlines, not just binary).

**Dependencies:** Python with PIL/Pillow, scipy (for distance transform). Same toolchain used for the existing past atlas.

---

## Phase 2 — Time Model + Display

**Goal:** The clock runs on a 24-hour cycle. Morning = past, afternoon = future. Scrubbing works across the 12:00 boundary.

**Changes to `timeToMa`:**
- Currently: `(hours % 12) / 12` maps both AM and PM to 0–4540 Ma (past).
- New: hours 0–11 return past Ma (4540→0, same as current). Hours 12–23 return a future Ma object or use a convention to distinguish future values (e.g. negative Ma, or a separate function).
- Decision needed during implementation: simplest approach is likely a `{ma, isFuture}` return, or keep Ma positive and add `isFutureHalf(hours)` as a separate check.

**Changes to display formatting:**
- Past: `250 million years ago` (unchanged)
- Future: `+250 million years from now`
- The `updateDeepTimeDisplay()` function needs a future branch.

**Changes to scrub system:**
- Cumulative angle tracking already supports crossing 12-hour boundaries. Needs to support the full 24-hour range: `% 86400` wrapping stays, but the geological interpretation of positions 12:00–24:00 now maps to future Ma instead of repeating past Ma.
- `scrub.ma` needs to be able to hold future Ma values (or a future flag).
- Time display during scrub: hours 12–23 show future geological time.

**Changes to era display:**
- `getCurrentEon(ma)` and `getCurrentEra(ma)` need future equivalents.
- For past Ma these are unchanged. For future Ma, return the phase name (Near Earth, Supercontinent, etc.).

**Verify:** Scrub from 11:50 through 12:00 to 12:10 — should transition smoothly from "65 million years ago" through "Present day" to "+50 million years from now". Time display in the bottom-right should show 24-hour time when in the future half.

---

## Phase 3 — FUTURE_STATES + Shader

**Goal:** The globe renders the future. All 12 future states are in place with working SDF blending.

### 3a — FUTURE_STATES array

Add the 12 states from FUTURE-EARTH.md as a `FUTURE_STATES` constant:

| # | Name | Span (future Ma) | Surface | Clouds |
|---|------|-------------------|---------|--------|
| 0 | Near Earth | 0–250 | screenprint | warped_wisps |
| 1 | Supercontinent | 250–400 | screenprint | warped_wisps |
| 2 | Supercontinent breakup | 400–500 | screenprint | warped_wisps |
| 3 | Late breakup | 500–600 | screenprint | warped_wisps |
| 4 | Dying biosphere (early) | 600–800 | screenprint | warped |
| 5 | Dying biosphere (mid) | 800–1150 | screenprint | warped |
| 6 | Dying biosphere (late) | 1150–1500 | screenprint | warped |
| 7 | Moist greenhouse | 1500–2250 | screenprint | warped_layers |
| 8 | Dry aftermath | 2250–3000 | screenprint | warped |
| 9 | Terminal Earth (early) | 3000–3650 | screenprint | warped |
| 10 | Terminal Earth (late) | 3650–4300 | screenprint | warped |
| 11 | Red Giant | 4300–4450 | topographic | warped_layers |
| 12 | Earth destroyed | 4450–4540 | topographic | warped_layers |

### 3b — `getVisualState()` for future Ma

When the current time is in the future half, `getVisualState()` looks up `FUTURE_STATES` instead of `STATES`. The blend logic (finding adjacent entries, computing `t`, smoothstep easing) is identical — just a different array.

### 3c — Future SDF in shader

- Add `uniform sampler2D uFutureSdfAtlas` to the Earth material.
- Write `sampleFutureSdf()` mirroring `sampleSdf()` but addressing the 5-slice future atlas.
- Extend `getSdfBlend()`: for future Ma 0–50, blend past atlas index 0 (Modern Earth) → future atlas index 0. For +50 to +250, blend between future atlas slices. Past +250, SDF is not used.
- `flipY = false` and `atan(p.z, -p.x)` longitude — same rules as past atlas.

### 3d — `useLandSea` crossfade

Between future Ma +250 and +300: `useLandSea = 1.0 - ((futureMa - 250) / 50)`. Past +300: `useLandSea = 0.0`. This dissolves the last traced continent into procedural noise.

### 3e — Fade to/from black

- **00:00 (Earth forms):** Globe opacity ramps 0→1 over the first ~30 Ma of Hadean (past Ma 4540→4510).
- **24:00 (Earth destroyed):** Globe opacity ramps 1→0 over the last ~30 Ma of F6 (future Ma 4510→4540).
- Implementation: multiply the earth canvas opacity by a ramp factor. Could use `earthCanvas.style.opacity` or a shader uniform. CSS opacity is simpler and doesn't require a shader change.

**Verify:** At 3pm local time (+1135 future Ma), the globe should show a pale tan dying biosphere. At 11pm (+4300 future Ma), it should glow red like the Hadean. At 11:59pm, it should be fading to black.

---

## Phase 4 — Events + Infographic Ring

### 4a — Future events

Add `FUTURE_EVENTS` array (10 events from FUTURE-EARTH.md). The event system needs to know whether a `time` value is past Ma or future Ma:
- Option A: Separate arrays (`EVENTS` for past, `FUTURE_EVENTS` for future), selected based on which half of the clock the scrubber is on.
- Option B: Merged array with a `future: true` flag.

Option A is cleaner — keeps the existing `EVENTS` array untouched.

`drawEventMarkers()` needs to place dots for both arrays. `updateEventMarkerStates()` needs to check the correct array based on current Ma. `showEventDescription()` / `hideEventDescription()` work the same.

The Ma-proximity check (currently `|EVENTS[i].time - currentMa| < 300`) needs adjustment: future events compare against future Ma, past events against past Ma.

### 4b — Future infographic ring

Add 6 future phase slices to `drawEonRing()`. These sit in the 12:00–24:00 arc (the bottom half of the ring, currently empty).

**Opacity values** (Cenozoic = 0.96, Hadean = 0.16):

| Phase | Opacity | Rationale |
|-------|---------|-----------|
| Near Earth | 0.96 | Matches Cenozoic — high certainty, SDF data |
| Supercontinent | 0.80 | SDF data fades out here; matches Mesozoic |
| Dying Biosphere | 0.64 | Long phase, decreasing certainty; matches Paleozoic |
| Ocean Loss | 0.48 | Speculative; matches Proterozoic |
| Terminal Earth | 0.32 | Very speculative; matches Archean |
| Red Giant | 0.16 | Stellar physics is well-modelled but extreme; matches Hadean |

This gives a clean mirror: the opacity ramps up through the past (Hadean 0.16 → Cenozoic 0.96) then ramps back down through the future (Near Earth 0.96 → Red Giant 0.16).

**Progressive reveal for the future half:** Reveals clockwise from 12:00 as the scrubber moves into future time. `updateEonReveal()` needs a future-aware clip path — currently it draws a conic sector from 12 o'clock to the current hour position; the future version extends from the current position toward 12 o'clock (midnight) going the other way.

### 4c — Angle mapping for future Ma

`maToAngle()` currently maps 4540 Ma → 12 o'clock, 0 Ma → 12 o'clock (full circle). For future Ma, need a `futureMaToAngle()`: 0 future Ma → 6 o'clock (12:00 position), +4540 future Ma → 6 o'clock (24:00 = 0:00 position, full circle). Or extend `maToAngle` to handle a future flag.

**Verify:** Scrub through the future half. Event dots appear at correct clock positions. Eon ring reveals progressively. Events trigger descriptions when scrubbed past.

---

## Phase 5 — Colour Lab + Tuning

### 5a — Extend colour lab for future states

- Add tab navigation at the top of the colour lab UI: **Past** | **Future**.
- Past tab shows the existing 14 states (unchanged).
- Future tab shows the 12 future states with the same editing controls.
- The future tab needs the future SDF atlas loaded for states that use `useLandSea > 0` (only Near Earth and early Supercontinent).
- The globe preview in the colour lab needs to render future states with the future shader path.
- "Copy Palette JS" exports both past and future state arrays.

### 5b — Palette tuning

All palette values in FUTURE-EARTH.md are starting points. Tune in the colour lab:
- Check transitions between adjacent states look smooth
- Verify the `useLandSea` crossfade at +250–300 Ma reads as "certainty dissolving"
- Ensure the Red Giant ↔ Molten Hadean symmetry feels intentional but not identical
- Confirm the fade-to-black at 24:00 looks clean
- Check that the 12:00 boundary (Modern Earth → Near Earth) is seamless

---

## Cross-cutting concerns

**Testing the 12:00 boundary:** The transition from past to future at 12:00 is the highest-risk seam. Modern Earth (past state 14) must blend seamlessly into Near Earth (future state 0). Both use `useLandSea: 1.0` with the same SDF slice (past atlas index 0). The palette shift should be imperceptible at the boundary and only become noticeable 5–10 minutes into the future.

**Performance:** The future half adds a second SDF texture uniform. The shader already does dual-render (A/B blend), so the GPU cost of sampling a second atlas is marginal. The future states are mostly screenprint with low cloud density, which is lighter than the past's warped_layers phases.

**Scrub handle at 12 o'clock ambiguity:** Currently both 0 Ma (present) and 4540 Ma (Earth forms) map to 12 o'clock. In the 24-hour model, 0 Ma maps to 6 o'clock (12:00 position) and the ambiguity shifts: 12 o'clock = both 4540 Ma past and +4540 Ma future (both "Earth forms" and "Earth destroyed"). The Ma-proximity check handles this, but worth testing.

**CLAUDE.md updates:** Once the build is complete, CLAUDE.md needs updating to document the 24-hour time model, FUTURE_STATES, future SDF atlas, and the extended event/ring system.
