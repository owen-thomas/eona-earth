# Clock & Eona Performance Review — June 2026

Review of `clock.html` (Pi 5 build) and `eona.html` against CLAUDE.md and PI-SETUP.md. Ordered by impact. Each item is written so it can be handed to Claude Code as a discrete task.

-----

## 1. CRITICAL — Unbounded accumulators degrade the shader over multi-day uptime

`clock.html` runs 24/7. Three values grow without bound:

- `u.time.value += deltaTime` (line ~1843) — grows by 86,400 per day
- `u.cloudRotation.value` — grows by ~724 radians per day
- `earthSphere.rotation.y` — grows by ~603 radians per day

The fragment shader receives these as float32. `time` feeds the cloud drift offsets (`time * 0.004` etc.), which are added to noise sample coordinates. Inside `hash31`, coordinates are multiplied by ~443 before `fract()`. After roughly a week of uptime the multiplied values exceed float32’s exact-integer range and `fract()` starts returning quantised garbage. Symptoms: clouds will progressively band, jitter, or freeze in place after days of continuous running. `cos`/`sin` of very large rotation angles suffer the same argument-reduction precision loss.

This is almost certainly invisible in any test session and only appears on the wall after extended uptime.

**Fix (cheap, exact):**

```js
// In updateEarth, after the rotation updates:
const TWO_PI = Math.PI * 2;
earthSphere.rotation.y %= TWO_PI;          // rotateY is periodic — modulo is identity
u.cloudRotation.value %= TWO_PI;
```

For `time`: the globe fades to black at the cycle endpoints (`FADE_MA = 30`, i.e. the ~4.7 minutes around local midnight). Reset `u.time.value = 0` once per day while `earthOpacity === 0` near midnight. The clouds will re-seed during the blackout and nobody ever sees the jump. Guard with a `_timeResetDone` flag so it fires once per blackout window.

-----

## 2. File size — the future SDF atlas is 16× larger than intended

The embedded `FUTURE_SDF_ATLAS_BASE64` is a **2048×7168** PNG (1.36 MB decoded, 1.81 MB as base64). The code comment at the texture load site already says “7-slice 512×1792 PNG” — the data was evidently exported at 4× the intended scale. The historical atlas is 512×256 per slice and renders perfectly at the globe’s actual canvas resolution (273×273 px after the half-res optimisation), so the extra resolution buys nothing.

Verified by resampling to 512×1792 (BOX/area filter — correct for SDF downsampling, no ringing) and comparing the smoothstepped landness masks at display resolution: worst-case mean difference 0.005. Visually identical.

**Impact:**

- `clock.html`: 2.38 MB → ~0.88 MB (63% smaller; same applies to `eona.html`)
- GPU texture memory: ~57 MB → ~3.6 MB uploaded (RGBA) — significant on a 2 GB Pi with shared memory
- Much better texture-cache behaviour per fetch in the fragment shader

**Fix:** a resampled `future-sdf-atlas-512.png` is supplied alongside this document. Re-encode to base64 and replace the constant in both files:

```python
import base64
data = base64.b64encode(open('future-sdf-atlas-512.png','rb').read()).decode()
# splice into FUTURE_SDF_ATLAS_BASE64 in clock.html and eona.html
```

No shader or JS changes needed — `FUTURE_ATLAS_N = 7.0` and the v-coordinate maths are resolution-independent. Update the stale dimension comments while in there.

-----

## 3. Energy — quantise the per-frame DOM and SVG churn

Almost everything outside the WebGL canvas moves slower than 0.1°/second, yet the tick loop invalidates SVG layers and styles at full frame rate. On the Pi this is wasted compositor and style-recalc work every frame, 24/7. Specific offenders, all in the 60 fps path:

**a. Minute hand updates at 60 fps** (`updateClockHands` with `smoothSeconds`). The hand moves 0.1°/s. Snap to whole seconds so the clock layer repaints once per second instead of sixty times:

```js
const minuteAngle = (minutes * 6) + Math.floor(seconds) * 0.1;
```

Skip the `setAttribute` entirely when the computed angle hasn’t changed.

**b. Eon reveal path rewritten every frame** (`updateEonReveal`). The reveal edge moves 0.0083°/s. Rewriting the clip path `d` invalidates the clipped group, including the feTurbulence noise rect. Quantise the angle to 0.05° steps and only write on change (~one update every 6 seconds):

```js
const q = Math.round(deg / 0.05) * 0.05;
if (q === _lastRevealDeg) return;
_lastRevealDeg = q;
```

**c. Scrubber handle position written every frame** (`drawPositionIndicator`). Same speed as the reveal edge. Round `pos.x/pos.y` to 2 dp and skip the four `setAttribute` calls when unchanged. (During scrub it changes every frame legitimately — the dedupe handles both cases for free.)

**d. Haze and dark-haze gradient strings rebuilt and reassigned every frame** (`updateEarth`). Colours only change during state blends. Cache the last assigned string per element and only write on change. Same for `earthEl.style.filter` (currently assigns `''` every frame outside glow phases) and `earthEl.style.opacity`.

**e. `getComputedStyle(document.body)` called every frame** in `updateEventMarkerStates` (and in `_applyHandleOutline`). Forces style recalc. Cache the accent values and refresh only when `body.future` toggles (once per 12 hours, plus scrub crossings).

**f. `querySelectorAll` + attribute parse on all ~45 event dots every frame** in `updateEventMarkerStates`. Build a cached array of `{el, x, y, time, isFuture}` once in `drawEventMarkers` and iterate that. Also skip the whole function in live (non-scrub) mode unless the handle is within ~30 px of the nearest dot — precompute the next dot crossing if you want to be thorough, but the cached array alone removes most of the cost.

**g. Cache element refs.** `tick` and `updateEarth` call `getElementById` for the same handful of elements every frame. Hoist them to module-level constants set in `init()`.

Together these reduce the steady-state per-frame work to: one WebGL render, one time-display text write per second, and nothing else most frames.

-----

## 4. Energy — cap the frame rate at 30 fps

The 15 fps cap was removed when SwiftShader went away, so the Pi now renders at full vsync (likely 60 fps). Nothing on this clock needs 60: the globe rotates at 6°/s and clouds drift far slower. 30 fps halves GPU fragment work (the dominant SoC load) with no perceptible difference on a wall clock. Lower fan duty follows.

```js
const FRAME_INTERVAL = 1000 / 30;
function tick() {
  requestAnimationFrame(tick);
  const now = performance.now();
  if (now - lastTime < FRAME_INTERVAL - 1) return;
  // ... existing body
}
```

Worth testing 24 fps as well — the globe rotation step at 24 fps is 0.25°/frame, still smooth at viewing distance. Keep 30 as the safe default.

(Backlog note: display auto-dim remains the single biggest energy lever for the physical build — the backlight dwarfs SoC power. The items above mainly cut heat and fan noise.)

-----

## 5. Shader — skip SDF texture fetches when they contribute nothing

`main()` unconditionally performs four texture fetches per pixel (two past slices, two future slices) plus the lat/lon trig, then throws the result away whenever `useLandSea` is 0 — which is true from 4540 Ma to 720 Ma (midnight to ~10:06) and for most future states. The existing `stateBlend > 0.001` guard proves uniform-conditional branching is safe on V3D.

```glsl
float sdfSample = 0.0;
if (aUseLandSea > 0.001) {
  float sdfSamplePast = 0.0;
  if (futureSdfWeight < 0.999) {
    sdfSamplePast = mix(sampleSdf(p, sdfIndexA), sampleSdf(p, sdfIndexB), sdfBlend);
  }
  float sdfSampleFuture = 0.0;
  if (futureSdfWeight > 0.001) {
    sdfSampleFuture = mix(sampleFutureSdf(p, futureSdfIndexA), sampleFutureSdf(p, futureSdfIndexB), futureSdfBlend);
  }
  sdfSample = mix(sdfSamplePast, sdfSampleFuture, futureSdfWeight);
}
```

Note: in Pi mode `aUseLandSea` snaps per state, so the branch is fully coherent. This removes the only texture traffic in the shader for most of every 12-hour cycle. Verify on the Pi before merging (uniform branches have been stable on V3D so far, but the budget history says always confirm).

-----

## 6. Bug — hidden wrong-half dots latch the scrub handle

In `updateEventMarkerStates`, the overlap check runs **before** the half filter:

```js
if (dist < OVERLAP_ZONE) scrubOverMarker = true;   // runs for ALL dots
const isFuture = dot.dataset.eventFuture === 'true';
if (isFuture !== isMaFuture) return;                // filter comes too late
```

Scrubbing in the future half past the position of a hidden past-event dot (or vice versa) latches the handle into outline state with no visible dot anywhere near it. Move the half check above the overlap check. (Folding into the cached-array refactor from 3f handles this naturally.)

-----

## 7. eona.html — remove the leftover 15 fps cap

`eona.html` still carries `TARGET_FPS = 15` / `FRAME_BUDGET` and the throttle in `tick()` (lines ~2867 and ~2901). That cap existed for SwiftShader on the Pi 4 and now lives in the wrong file: the live site is throttling every visitor’s browser to 15 fps. Globe rotation steps visibly and scrub-drag latency is up to 66 ms. Remove the throttle from `eona.html` entirely (desktop GPUs are idling), or if the site should also be energy-considerate, set it to 30.

-----

## 8. Dead code — clock.html

Safe to delete (verified no call sites):

- `angleToMa()` — never called
- `drawLifeRing()`, `drawHourMarkers()`, `createArc()`, the `LIFE` constant, and the `#hour-markers` / `#life-ring` SVG groups
- The tooltip system: `showTooltip` (returns immediately), `hideTooltip`, the `.tooltip` markup and CSS, the `mouseover`/`mouseout` listeners that exist only to drive it, and `_hoveredEventIndex`
- `#rotate-background` circle — pointer handling is geometric on `.clock-container`, so verify with a quick manual test, then remove
- The unused `initialAngle` parameter on `enterScrub()`
- Comment fix: `scrub.lastAngle` is documented as radians; it holds degrees

Roughly 4–5 KB and, more usefully, less surface area for the next refactor.

-----

## 9. Verification checklist after changes

1. Pi: confirm shader compiles and renders (item 5 touches GLSL — V3D budget check)
1. Pi: leave running 48 h+; confirm clouds still animate cleanly (item 1)
1. Scrub across midnight in both directions; confirm handle latch only triggers on visible dots (item 6)
1. Confirm future continents (+50 to +250 Ma) look unchanged after the atlas swap (item 2)
1. Browser: confirm eona.earth scrubbing feels immediate after removing the cap (item 7)
1. Measure: `vcgencmd measure_temp` before/after on the Pi as a cheap proxy for the energy wins (items 3–5)