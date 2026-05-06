# Future Earth — Build Context

The second 12 hours of the clock (12:00–24:00) maps 4,540 Ma of Earth's future. This document gives Claude Code everything it needs to implement the future half of the clock. It assumes full familiarity with the existing architecture documented in `CLAUDE.md`.

---

## Time Model Change

The current build repeats the same 12-hour past sequence twice per day. The new model uses a full 24-hour cycle:

- **00:00** = 4,540 Ma ago (Earth forms)
- **12:00** = Present day
- **24:00** = +4,540 Ma from now (Earth destroyed)

The first 12 hours (00:00–12:00) are unchanged — same 15 STATES, same SDF atlas, same everything. The second 12 hours (12:00–24:00) run the future sequence described below.

### Ma Convention

The future uses positive values representing **millions of years from now**: +50 Ma, +250 Ma, +4540 Ma. This mirrors how the scientific literature writes future projections. Internally these are plain positive numbers — the code just needs to know whether it's on the past or future side of the 12:00 boundary.

Display formatting:
- Full: `+250 million years from now`
- Compact: `+250 Ma`

### What changes in `timeToMa`

Currently `timeToMa` uses `hours % 12`, so both AM and PM map to 0–4540 Ma (past). The new version needs to distinguish the two halves:

- **Hours 0–11 (past)**: `ma = EARTH_AGE * (1 - fraction)` where fraction = totalHours / 12. Ma counts down from 4540 to 0. Same as current.
- **Hours 12–23 (future)**: Returns a future Ma value (0 at 12:00, 4540 at 24:00). The `getVisualState()` function uses a separate `FUTURE_STATES` array when it receives a future Ma.

---

## Future SDF Atlas

Five continent images have been traced from Scotese's 2018 Atlas of Future Plate Tectonic Reconstructions. They are black-and-white equirectangular land/sea masks, already at the correct 512×256 dimensions.

**Source images** (in `images/future/`):
- `50.png` — +50 Ma
- `100.png` — +100 Ma
- `150.png` — +150 Ma
- `200.png` — +200 Ma
- `250.png` — +250 Ma

### Processing pipeline

1. **Threshold** to pure binary (0 or 255, no antialiased grey). Use 128 as the cutoff.
2. **Generate SDF** via Euclidean distance transform. Value 128 = coastline, >128 = land, <128 = sea. Same convention as the existing past atlas.
3. **Stack** into a single atlas PNG (512 wide, 256 × 5 tall = 512×1280). The +0 Ma slice is NOT included — the shader shares the existing past atlas's index 0 (Modern Earth) as the starting point.

Atlas layout (top to bottom):

| Index | Future Ma |
|-------|-----------|
| 0     | +50       |
| 1     | +100      |
| 2     | +150      |
| 3     | +200      |
| 4     | +250      |

Embed as base64 alongside the existing `SDF_ATLAS_BASE64`, e.g. `FUTURE_SDF_ATLAS_BASE64`.

### Shader integration

Add a second `uniform sampler2D uFutureSdfAtlas` to the Earth material. Write a `sampleFutureSdf()` function mirroring the existing `sampleSdf()` but addressing the future atlas. The 5-slice atlas covers +50 to +250 Ma at 50 Ma intervals.

**Critical**: the +0 Ma starting point uses the existing past atlas index 0 (Modern Earth), NOT a slice from the future atlas. This guarantees no visual seam at 12:00:00. The future atlas's first slice (+50 Ma) blends in from there.

So `getSdfBlend()` for future Ma works like:
- 0 to +50 Ma: blend from past atlas index 0 → future atlas index 0
- +50 to +100 Ma: blend future atlas index 0 → index 1
- +100 to +150 Ma: blend future atlas index 1 → index 2
- +150 to +200 Ma: blend future atlas index 2 → index 3
- +200 to +250 Ma: blend future atlas index 3 → index 4

Same `flipY = false` rule applies. Same `atan(p.z, -p.x)` longitude convention.

---

## Future STATES

Six phases, expanding into ~12 STATES waypoints. Phase boundaries are driven by scientifically meaningful Ma values — the clock times are derived.

### Clock maths reference

1 hour ≈ 378 Ma · 1 minute ≈ 6.3 Ma · 1 second ≈ 105,000 years

| Future Ma | Clock time | Event / boundary |
|-----------|------------|------------------|
| 0         | 12:00      | Present day |
| +50       | 12:08      | Mediterranean closes |
| +250      | 12:40      | Pangaea Proxima assembled (end of SDF data) |
| +400      | 13:04      | Supercontinent breakup |
| +600      | 13:35      | Last plants die |
| +800      | 14:07      | Complex life ends |
| +1,500    | 15:58      | Moist greenhouse begins |
| +3,000    | 19:56      | Oceans gone, desert planet |
| +3,500    | 21:16      | Plate tectonics stops |
| +4,300    | 23:22      | Red giant phase |
| +4,540    | 24:00      | Earth destroyed |

### F1 · Near Earth — +0 to +250 Ma (12:00–12:40)

Full SDF continents throughout (`useLandSea: 1.0`). This is the only future phase with real paleogeographic data. Visually it's a warming Modern Earth — not a different era, just the same planet getting hotter.

```js
// F1: Near Earth (+0 to +250 Ma)
// Single state — slow drift from Modern Earth palette toward warmer tones.
// Solar luminosity ~2.5% higher by +250 Ma.
{
  name: 'Near Earth',
  span: [0, 250], blendStart: 0,  // full-span drift
  // Palette: Modern Earth but greens shift yellow-green, atmosphere warms
  palette: ['#FAF5E8', '#6AAE5A', '#0078B8', '#006A9E', '#041520'],
  hazeColor: '#E8DCC8', hazeOpacity: 0.12,
  darkHazeColor: '#0A0804', darkHazeOpacity: 0.30,
  noiseThresh1: 0.46, noiseThresh2: 0.56, surfaceIntensity: 0.82,
  cloudDensity: 0.50, cloudShape: 1.00,
  polarIce: 0.0,  // ice age is over
  useLandSea: 1.0, coastSoftness: 0.03,
  surfaceApproach: 'screenprint', cloudApproach: 'warped_wisps',
  seed: 7.0
}
```

Key details:
- `polarIce` ramps from 0.85 (Modern Earth value) → 0 across this phase
- Cloud density stays similar, maybe slightly increasing
- This is NOT an "Early Oxidation" palette — that was the GOE at 2500 Ma ago, completely different chemistry

### F2 · Supercontinent — +250 to +600 Ma (12:40–13:35)

The SDF data ends here. `useLandSea` crossfades from 1.0 → 0.0 over the first ~50 Ma (+250 to +300), dissolving the last traced continent (Pangaea Proxima) into procedural noise. This is a deliberate design moment: scientific certainty fading into speculation.

Split into 3 waypoints:

```js
// F2a: Supercontinent peak (+250 to +400 Ma)
// useLandSea fades 1.0 → 0.0 over first 50 Ma, then pure procedural.
// Huge desert interior, monsoon edges. Hotter than past Pangaea (5-10% higher solar).
// Think: Hothouse palette but drier, more bleached.
{
  name: 'Supercontinent',
  span: [250, 400], blendStart: 250,
  palette: ['#F0E0C0', '#B8865A', '#1A7A8A', '#105868', '#081820'],
  hazeColor: '#E0CCA0', hazeOpacity: 0.20,
  darkHazeColor: '#1A1008', darkHazeOpacity: 0.40,
  noiseThresh1: 0.46, noiseThresh2: 0.70,  // high thresh2 = large landmass
  surfaceIntensity: 0.80,
  cloudDensity: 0.35, cloudShape: 0.60,
  useLandSea: 1.0,  // fades to 0.0 — needs interpolation logic
  coastSoftness: 0.03,
  surfaceApproach: 'screenprint', cloudApproach: 'warped_wisps',
  seed: 7.5
}

// F2b: Breakup (+400 to +500 Ma)
// Rift systems, volcanic haze. Procedural landmass fragmenting.
{
  name: 'Supercontinent breakup',
  span: [400, 500], blendStart: 400,
  palette: ['#E8D0A8', '#A07848', '#187080', '#0E4850', '#061418'],
  hazeColor: '#D0B888', hazeOpacity: 0.30,  // volcanic haze bump
  darkHazeColor: '#1A0E06', darkHazeOpacity: 0.45,
  noiseThresh1: 0.48, noiseThresh2: 0.58,  // land scattering
  surfaceIntensity: 0.75,
  cloudDensity: 0.40, cloudShape: 0.50,
  useLandSea: 0.0, coastSoftness: 0.03,
  surfaceApproach: 'screenprint', cloudApproach: 'warped_wisps',
  seed: 8.0
}

// F2c: Late breakup (+500 to +600 Ma)
// Dispersed continents. Green already fading — transition toward dying biosphere.
{
  name: 'Late breakup',
  span: [500, 600], blendStart: 500,
  palette: ['#E0D0B0', '#7A8850', '#1A6870', '#0E4048', '#061210'],
  hazeColor: '#C8C0A0', hazeOpacity: 0.25,
  darkHazeColor: '#141008', darkHazeOpacity: 0.40,
  noiseThresh1: 0.48, noiseThresh2: 0.56,
  surfaceIntensity: 0.72,
  cloudDensity: 0.35, cloudShape: 0.40,
  useLandSea: 0.0, coastSoftness: 0.03,
  surfaceApproach: 'screenprint', cloudApproach: 'warped_wisps',
  seed: 8.5
}
```

**`useLandSea` crossfade implementation**: Between +250 and +300 Ma, `useLandSea` should interpolate from 1.0 to 0.0. This can be handled as a special case in the blend logic — when the current future Ma is between 250 and 300, compute `useLandSea = 1.0 - ((futureMa - 250) / 50)`. Past +300, it stays at 0.0 for all remaining future states.

### F3 · Dying Biosphere — +600 to +1,500 Ma (13:35–15:58)

Long slow fade. Split into 3 waypoints to get continuous palette drift (like the Boring Billion). All procedural (`useLandSea: 0.0`).

```js
// F3a: Early decline (+600 to +800 Ma)
// Greens drain from c1. Last complex life dies. Cloud thinning begins.
{
  name: 'Dying biosphere (early)',
  span: [600, 800], blendStart: 600,
  palette: ['#D8C8A8', '#6A7040', '#286068', '#183840', '#08100C'],
  hazeColor: '#B8B090', hazeOpacity: 0.22,
  darkHazeColor: '#100C06', darkHazeOpacity: 0.38,
  noiseThresh1: 0.48, noiseThresh2: 0.56,
  surfaceIntensity: 0.68,
  cloudDensity: 0.28, cloudShape: 0.30,
  useLandSea: 0.0,
  surfaceApproach: 'screenprint', cloudApproach: 'warped',
  seed: 9.0
}

// F3b: Mid decline (+800 to +1150 Ma)
// Ochre/tan land. Only microbes. Thin wispy clouds.
// Think: Boring Billion (mid) palette but with less ocean coverage.
{
  name: 'Dying biosphere (mid)',
  span: [800, 1150], blendStart: 800,
  palette: ['#D0C0A0', '#8A7850', '#406870', '#284048', '#0A1210'],
  hazeColor: '#C0B090', hazeOpacity: 0.20,
  darkHazeColor: '#0E0A06', darkHazeOpacity: 0.35,
  noiseThresh1: 0.50, noiseThresh2: 0.60,  // ocean coverage shrinking
  surfaceIntensity: 0.60,
  cloudDensity: 0.20, cloudShape: 0.20,
  useLandSea: 0.0,
  surfaceApproach: 'screenprint', cloudApproach: 'warped',
  seed: 9.5
}

// F3c: Late decline (+1150 to +1500 Ma)
// Pale tan, bleached. Oceans visibly smaller. Atmosphere thinning.
{
  name: 'Dying biosphere (late)',
  span: [1150, 1500], blendStart: 1150,
  palette: ['#C8B898', '#9A8A6A', '#587078', '#384850', '#0C1418'],
  hazeColor: '#B8A888', hazeOpacity: 0.18,
  darkHazeColor: '#0C0804', darkHazeOpacity: 0.32,
  noiseThresh1: 0.52, noiseThresh2: 0.64,  // more land exposure
  surfaceIntensity: 0.52,
  cloudDensity: 0.14, cloudShape: 0.10,
  useLandSea: 0.0,
  surfaceApproach: 'screenprint', cloudApproach: 'warped',
  seed: 10.0
}
```

Palette arc across F3: dusty green → brown → ochre → pale tan.

### F4 · Ocean Loss — +1,500 to +3,000 Ma (15:58–19:56)

Haze takes over as the primary visual feature. Split into 2 waypoints.

```js
// F4a: Moist greenhouse (+1500 to +2250 Ma)
// Thick steam atmosphere. White haze. Globe looks foggy.
{
  name: 'Moist greenhouse',
  span: [1500, 2250], blendStart: 1500,
  palette: ['#D0C8C0', '#A09080', '#708088', '#485860', '#101820'],
  hazeColor: '#E0D8D0', hazeOpacity: 0.45,  // ramping up
  darkHazeColor: '#1A1410', darkHazeOpacity: 0.50,
  noiseThresh1: 0.54, noiseThresh2: 0.68,
  surfaceIntensity: 0.40,  // steam obscures surface
  cloudDensity: 0.10, cloudShape: 0.00,
  useLandSea: 0.0,
  surfaceApproach: 'screenprint', cloudApproach: 'warped_layers',
  seed: 10.5
}

// F4b: Dry aftermath (+2250 to +3000 Ma)
// Steam clears. Haze shifts yellow. Exposed salt flats, mineral crusts.
// No blue anywhere.
{
  name: 'Dry aftermath',
  span: [2250, 3000], blendStart: 2250,
  palette: ['#C8B890', '#B0986A', '#908068', '#685848', '#181010'],
  hazeColor: '#C8B870', hazeOpacity: 0.55,  // sulphur yellow
  darkHazeColor: '#1A1408', darkHazeOpacity: 0.55,
  noiseThresh1: 0.56, noiseThresh2: 0.72,  // high = exposed basins
  surfaceIntensity: 0.45,
  cloudDensity: 0.05, cloudShape: 0.00,
  useLandSea: 0.0,
  surfaceApproach: 'screenprint', cloudApproach: 'warped',
  seed: 11.0
}
```

Key visual details:
- Haze ramps from ~0.3 → 0.7 across this phase
- Haze colour transitions from steamy white (`#E0D8D0`) to sulphur yellow (`#C8B870`)
- High `noiseThresh2` = exposed ocean basins as salt flats / mineral crusts
- Pale mineral palette for c1 (land)

### F5 · Terminal Earth — +3,000 to +4,300 Ma (19:56–23:22)

The "Boring Billion in reverse" — geologically quiet, palette converging to a narrow tonal range. Split into 2 waypoints.

```js
// F5a: Terminal early (+3000 to +3650 Ma)
// Tan → burnt sienna. Plate tectonics ceasing.
{
  name: 'Terminal Earth (early)',
  span: [3000, 3650], blendStart: 3000,
  palette: ['#B0987A', '#987858', '#786050', '#584038', '#140C08'],
  hazeColor: '#A89068', hazeOpacity: 0.45,
  darkHazeColor: '#1A1008', darkHazeOpacity: 0.50,
  noiseThresh1: 0.54, noiseThresh2: 0.65,
  surfaceIntensity: 0.35,
  cloudDensity: 0.03, cloudShape: 0.00,
  useLandSea: 0.0,
  surfaceApproach: 'screenprint', cloudApproach: 'warped',
  seed: 11.5
}

// F5b: Terminal late (+3650 to +4300 Ma)
// Dark reddish-brown. Minimal tonal range. Land/sea boundary dissolving.
// noiseThresh values converge — just crust, no distinct geography.
{
  name: 'Terminal Earth (late)',
  span: [3650, 4300], blendStart: 3650,
  palette: ['#8A7060', '#704838', '#5A3828', '#3A2018', '#100808'],
  hazeColor: '#806040', hazeOpacity: 0.35,
  darkHazeColor: '#1A0C06', darkHazeOpacity: 0.55,
  noiseThresh1: 0.52, noiseThresh2: 0.58,  // converging = less distinction
  surfaceIntensity: 0.28,
  cloudDensity: 0.00, cloudShape: 0.00,
  useLandSea: 0.0,
  surfaceApproach: 'screenprint', cloudApproach: 'warped',
  seed: 12.0
}
```

### F6 · Red Giant — +4,300 to +4,540 Ma (23:22–24:00)

Hadean in reverse. Surface melts again. Ends with fade to black.

```js
// F6a: Red giant onset (+4300 to +4450 Ma)
// Glow returns. Surface remolten. Rising intensity.
{
  name: 'Red Giant',
  span: [4300, 4450], blendStart: 4300,
  palette: ['#2D2D2D', '#C84020', '#6A1808', '#3A0C04', '#1A0800'],
  hazeColor: '#C84020', hazeOpacity: 0.50,
  darkHazeColor: '#1A0808', darkHazeOpacity: 0.50,
  glowStrength: 0.40,
  glowColor: '#E04020',
  noiseThresh1: 0.75, noiseThresh2: 0.78,
  surfaceIntensity: 0.80,
  cloudDensity: 0.00, cloudShape: 0.00,
  useLandSea: 0.0,
  surfaceApproach: 'topographic', cloudApproach: 'warped_layers',
  seed: 12.5
}

// F6b: Destruction / fade to black (+4450 to +4540 Ma)
// Mirror of Molten Hadean (early) but ending in black rather than starting from it.
{
  name: 'Earth destroyed',
  span: [4450, 4540], blendStart: 4450,
  palette: ['#1A1A1A', '#8A2010', '#3A0C04', '#1A0600', '#0A0200'],
  hazeColor: '#6A1808', hazeOpacity: 0.40,
  darkHazeColor: '#0A0404', darkHazeOpacity: 0.70,
  glowStrength: 0.55,
  glowColor: '#C83010',
  noiseThresh1: 0.80, noiseThresh2: 0.79,
  surfaceIntensity: 0.60,
  cloudDensity: 0.00, cloudShape: 0.00,
  useLandSea: 0.0,
  surfaceApproach: 'topographic', cloudApproach: 'warped_layers',
  seed: 13.0
}
```

**Fade to/from black**: At 24:00:00 (+4540 Ma), the globe should fade to black. Symmetrically, at 00:00:00 (4540 Ma ago), the Hadean should fade *from* black. This creates a seamless loop: black → molten → life → death → molten → black. Implementation: a global opacity multiplier on the earth canvas, ramping 0→1 over the first ~30 Ma of the Hadean and 1→0 over the last ~30 Ma of F6. Could also be done with a darkHazeOpacity ramp to 1.0.

---

## Future Events

Equivalent of the `EVENTS` array for the future half. These display on the infographic ring and trigger descriptions when scrubbed past.

```js
const FUTURE_EVENTS = [
  { name: 'Mediterranean closes', time: 50,
    desc: 'Africa collides with Europe. The Mediterranean Sea disappears.' },
  { name: 'Pangaea Proxima', time: 250,
    desc: 'The continents merge into a new supercontinent.' },
  { name: 'Supercontinent breaks up', time: 400,
    desc: 'Rifting tears the supercontinent apart. Volcanic chains line the fractures.' },
  { name: 'Last plants die', time: 600,
    desc: 'Rising solar heat strips CO₂ from the air. Photosynthesis becomes impossible.' },
  { name: 'Complex life ends', time: 800,
    desc: 'Only microbes survive. A billion years of evolution, undone by a brightening star.' },
  { name: 'Oceans begin to boil', time: 1500,
    desc: 'A runaway greenhouse turns the surface to steam.' },
  { name: 'Last water lost', time: 3000,
    desc: 'The oceans are gone. Earth becomes a desert world.' },
  { name: 'Plate tectonics stops', time: 3500,
    desc: 'The mantle cools. The crust freezes. Earth goes geologically silent.' },
  { name: 'Red giant', time: 4300,
    desc: 'The Sun swells to consume Mercury and Venus. Earth\'s surface melts.' },
  { name: 'Earth destroyed', time: 4540,
    desc: 'The Sun engulfs or sterilises the Earth.<br>The story ends where it began.' }
];
```

Note: these `time` values are future Ma (positive, millions of years from now), not past Ma. The event system needs to distinguish past events (where `time` = Ma ago) from future events (where `time` = Ma from now).

---

## Infographic Ring

The eon ring currently shows 6 eons for the past half. The future half needs its own ring segments. There are no formal geological eons for the future, so use the phase names:

| Phase | Future Ma | Clock |
|-------|-----------|-------|
| Near Earth | 0–250 | 12:00–12:40 |
| Supercontinent | 250–600 | 12:40–13:35 |
| Dying Biosphere | 600–1500 | 13:35–15:58 |
| Ocean Loss | 1500–3000 | 15:58–19:56 |
| Terminal Earth | 3000–4300 | 19:56–23:22 |
| Red Giant | 4300–4540 | 23:22–24:00 |

The progressive reveal should work in reverse for the future half — revealing clockwise from 12:00 as the scrubber moves into the future, mirroring how the past reveals clockwise from 00:00.

Suggested opacity treatment: decreasing opacity as certainty decreases. Near Earth ≈ Cenozoic opacity, Terminal Earth much lower, Red Giant back up to match Hadean.

---

## Implementation Checklist

1. **SDF processing**: Threshold and distance-transform the 5 future continent PNGs (already 512×256). Stack into `FUTURE_SDF_ATLAS_BASE64`. Script should read from `images/future/`.
2. **Time model**: Extend `timeToMa` for 24-hour cycle. Positive future Ma for hours 12–23.
3. **Display formatting**: `formatMa()` needs a future branch — `+250 million years from now` instead of `250 million years ago`.
4. **FUTURE_STATES array**: Add the ~12 states above. Wire into `getVisualState()` for future Ma values.
5. **Future SDF sampling**: Add `uFutureSdfAtlas` uniform. Write `sampleFutureSdf()`. Wire into `getSdfBlend()` for future Ma. Remember: the +0 Ma starting point reads from the existing past atlas index 0.
6. **useLandSea crossfade**: Between +250 and +300 Ma (future), interpolate useLandSea 1.0 → 0.0.
7. **Future events**: Add `FUTURE_EVENTS` array. Wire into event marker system. Event system must distinguish past vs future events.
8. **Infographic ring**: Add future phase segments. Progressive reveal for the future half.
9. **Fade to/from black**: Opacity ramp at 00:00 (fade in) and 24:00 (fade out).
10. **Scrub + time display**: Ensure scrubbing works across the 12:00 boundary in both directions. Time display should show 12:00–23:59 for the future half.
11. **Palette tuning**: All palette values above are starting points. Final tuning happens in colour-lab.html after the structure is in place.

---

## Design Principles for the Future Half

- **The past earns its detail through evidence. The future should feel different — more abstract, more atmospheric.**
- SDF data provides certainty for 40 minutes. After that, procedural noise is honest.
- The `useLandSea` crossfade at +250–300 Ma is a deliberate design moment: certainty dissolving.
- The visual arc is *stripping complexity away*: richness → simplification → sterility.
- Haze and atmosphere become the dominant storytelling tools as surface detail fades.
- By 20:00 (+3000 Ma) the Earth should feel like a *thing* rather than a *world*.
- The symmetry with the past is deliberate: Hadean chaos → life → Modern Earth → life ends → Red Giant chaos. Black → black.
