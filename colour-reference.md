# Deep Time — Colour Reference

Each phase has a 5-stop palette ordered **lightest → darkest**:

| Slot | Role | Notes |
|------|------|-------|
| `c0` | Atmosphere / cloud highlight | Reserved for cloud layer — not visible on surface while clouds disabled |
| `c1` | Surface highlight / land | Painted over c2 — coverage set by `noiseThresh2` |
| `c2` | Surface primary / shallow ocean | Coverage = `(1 − noiseThresh1) × noiseThresh2` |
| `c3` | Surface shadow / deep ocean | Base layer — coverage = `noiseThresh1 × noiseThresh2` |
| `c4` | Silhouette | Near-black edge falloff only |

**Coverage maths** (fbm noise is roughly uniform in `[0, 0.9375]`, not `[0, 1]`):
```
c1 ≈ 1 − t2          (nominal)
c2 ≈ (1 − t1) × t2
c3 ≈ t1 × t2
```
In practice, t2=0.65 → ~20% land, t2=0.62 → ~25% land, t2=0.56 → ~44% land, t2=0.40 → ~60% land.
For 20/80: `t2=0.65, t1=0.50`. For 25/75: `t2=0.62, t1=0.50`.

> **Note on c0:** Clouds are currently disabled (`CLOUDS_ENABLED = false`). c0 is held for when clouds are re-enabled. It should never read on the main surface.

---

## Transition model

All blends use smoothstep easing (slow → fast → slow). `blendStart` on each state sets when it begins blending toward the next state:
- `blendStart == span[0]` → full-span drift (entire era is a continuous dissolve)
- `blendStart` close to `span[1]` → short ramp / snap

---

## 01 · Molten Hadean (early)
`4540–4420 Ma · 00:00–01:00`

```
c0  #FABF8A  warm peach        atmosphere (disabled)
c1  #E34E2A  deep orange-red   glowing magma surface — 60% coverage
c2  #8F220F  dark crimson      primary molten rock    — 30% coverage
c3  #3C0E04  near-black red    shadow / deep lava     — 10% coverage
c4  #1E0F01  almost black      silhouette
```

`noiseThresh1: 0.25, noiseThresh2: 0.40` · `blendStart: 4540` (full-span drift into late)

No clouds. Surface noise at full intensity (0.95). Pure procedural.

**Atmospheric glow:** `#8F220F` cherry red, strength 0.80.

**Haze:** `#6A2A1A` orange-brown · opacity 50%

**Dark haze:** `#2A0F08` deep brown · opacity 40%

---

## 01 · Molten Hadean (late)
`4420–4300 Ma · 01:00–01:15`

```
c0  #FABF8A  warm peach        atmosphere (disabled)
c1  #3C0E04  near-black red    cooled crust          — 60% coverage
c2  #8F220F  dark crimson      primary rock           — 30% coverage
c3  #E34E2A  deep orange-red   residual magma glow   — 10% coverage
c4  #1E0F01  almost black      silhouette
```

`noiseThresh1: 0.25, noiseThresh2: 0.40` · `blendStart: 4330` (30 Ma short ramp into Steam World)

Identical thresholds and seed to early — pure colour dissolve, no shape cross-fade.

**Atmospheric glow:** `#8F220F` cherry red, strength 0.55. Fades toward Steam World's 0.20.

**Haze:** `#6A2A1A` orange-brown · opacity 40%

**Dark haze:** `#2A0F08` deep brown · opacity 40%

---

## 02 · Steam World
`4300–4000 Ma · 01:15–03:00`

```
c0  #D9C6B8  warm cream-grey   dense steam atmosphere
c1  #3C0E04  near-black red    hot rock / minimal land — 20% coverage
c2  #2E473D  dark emerald      deep ocean primary      — 40% coverage
c3  #1C2B25  bottle green      deep ocean shadow       — 40% coverage
c4  #1E0F01  almost black      silhouette
```

`noiseThresh1: 0.50, noiseThresh2: 0.65` · `blendStart: 4060` (60 Ma short ramp into Hazy Archean)

Land/ocean ratio ~20/80. Pure procedural. Short ramp in (~30 Ma from Hadean late), short ramp out (60 Ma).

**Atmospheric glow:** `#8F220F` cherry red, strength 0.20. Residual from Hadean; fades to 0 during blend into Hazy Archean.

**Haze:** `#E6E8EA` grey-white · opacity 90%

**Dark haze:** `#B0B4B8` cool grey · opacity 100%

---

## 03 · Hazy Archean (early)
`4000–3200 Ma · 03:00–07:50`

```
c0  #F8D9AA  warm orange-peach  methane haze atmosphere
c1  #3F332E  muted brown-black  land / rock — 20% coverage
c2  #556B1A  deep olive green   ocean primary
c3  #2F3A0F  deeper olive green deep ocean shadow
c4  #060A0B  almost black       silhouette
```

`noiseThresh1: 0.50, noiseThresh2: 0.65` · `blendStart: 4000` (full-span drift into late)

Land/ocean ratio ~20/80. Pure procedural.

**Haze:** `#EBC39A` peach-orange · opacity 65%

**Dark haze:** `#D9A679` warm sand · opacity 75%

---

## 04 · Hazy Archean (late)
`3200–2500 Ma · 07:50–10:45`

```
c0  #F8D9AA  warm orange-peach  methane haze (same as early)
c1  #735454  dusty mauve        rock highlight — 20% coverage
c2  #389F79  emerald green      ocean primary
c3  #2A795C  deeper emerald     deep ocean shadow
c4  #060710  almost black       silhouette
```

`noiseThresh1: 0.50, noiseThresh2: 0.65` · `blendStart: 2510` (10 Ma short ramp into GOE)

Holds stable through most of span, then 10 Ma snap into Great Oxidation. Pure procedural.

**Haze:** `#EBC39A` peach-orange · opacity 60%

**Dark haze:** `#D9A679` warm sand · opacity 70%

---

## 05 · Great Oxidation (early)
`2500–2400 Ma · 10:45–11:23`

```
c0  #ECEEF0  pale blue          dissolving haze
c1  #A7572C  rust-brown         iron-stained land — 20% coverage
c2  #4E5F2A  olive-brown        ocean primary
c3  #2F3F1A  deep olive-brown   deep ocean shadow
c4  #3C0E04  near-black red     silhouette
```

`noiseThresh1: 0.50, noiseThresh2: 0.65` · `blendStart: 2500` (full-span drift into late)

Short ramp in from Hazy Archean (10 Ma). Continuous drift into GOE late. Pure procedural.

**Haze:** `#CFE2F1` pale blue · opacity 40%

**Dark haze:** `#6F8FA8` steel blue · opacity 50%

---

## 05 · Great Oxidation (late)
`2400–2300 Ma · 11:23–12:00`

```
c0  #E3EEF7  pale blue          clearing atmosphere
c1  #A7572C  rust-brown         iron-stained land — 20% coverage
c2  #2F6F9E  deep blue          ocean primary (oxygen building)
c3  #174663  dark navy-blue     deep ocean shadow
c4  #3C0E04  near-black red     silhouette
```

`noiseThresh1: 0.50, noiseThresh2: 0.65` · `blendStart: 2302` (2 Ma snap into Huronian snowball)

Oceans shift from olive-brown to deep blue as free oxygen rises. Pure procedural.

**Haze:** `#CFE2F1` pale blue · opacity 30%

**Dark haze:** `#6F8FA8` steel blue · opacity 40%

---

## 06 · Huronian Snowball
`2300–2100 Ma · 12:00–13:15`

```
c0  #EAF3FB  pale blue-white    ice atmosphere
c1  #DCE9F5  pale blue          ice surface — 20% coverage
c2  #C7D6E3  ice blue-grey      partially frozen ocean
c3  #D8D2D6  cool dusty pink    deeper ice / shadow
c4  #1A1410  near-black warm    silhouette
```

`noiseThresh1: 0.50, noiseThresh2: 0.65` · `blendStart: 2105` (5 Ma thaw into Boring Billion)

Short ramp in (2 Ma from GOE late), short ramp out (5 Ma thaw). Low surface intensity (0.32) — nearly flat-frozen. Pure procedural.

**Haze:** `#F2F3F5` blue-white · opacity 50%

**Dark haze:** `#AEBFCC` icy blue-grey · opacity 60%

---

## 07 · Boring Billion (early)
`2100–1500 Ma · 13:15–16:00`

```
c0  #F5DFA3  pale yellow-orange haze
c1  #4A4A4A  dark grey          land / rock — 25% coverage
c2  #3A584C  dark teal-green    ocean primary
c3  #2E473D  darker teal-green  deep ocean shadow
c4  #080612  almost black       silhouette
```

`noiseThresh1: 0.50, noiseThresh2: 0.62` · `blendStart: 2100` (full-span drift into mid)

Land/ocean ratio ~25/75. Pure procedural.

**Haze:** `#F5DFA3` pale yellow-orange · opacity 35%

**Dark haze:** `#8A6B3A` dusty warm brown · opacity 45%

---

## 08 · Boring Billion (mid)
`1500–1000 Ma · 16:00–18:40`

```
c0  #E3EEF7  pale blue-clear    clearing atmosphere
c1  #6C523F  brown              land / rock — 25% coverage
c2  #3F8B8F  teal-green         ocean primary
c3  #5F9EA0  cadet blue         ocean secondary
c4  #0A0D22  near-black navy    silhouette
```

`noiseThresh1: 0.50, noiseThresh2: 0.62` · `blendStart: 1500` (full-span drift into late)

Land/ocean ratio ~25/75. Pure procedural.

**Haze:** `#CFE2F1` pale blue · opacity 25%

**Dark haze:** `#6F8FA8` steel blue · opacity 35%

---

## 09 · Boring Billion (late)
`1000–720 Ma · 18:40–20:00`

```
c0  #E0C7B8  dusty brown-orange haze
c1  #8C6B5E  muted rose-brown   land / rock — 25% coverage
c2  #385955  murky green-grey   ocean primary
c3  #1F2A33  near-black blue    deep ocean shadow
c4  #06091E  almost black       silhouette
```

`noiseThresh1: 0.50, noiseThresh2: 0.62` · `blendStart: 722` (2 Ma snap into Cryogenian)

Land/ocean ratio ~25/75. Pure procedural.

**Haze:** `#E0C7B8` dusty warm · opacity 35%

**Dark haze:** `#7A5A4A` muted rose-brown · opacity 45%

---

## 10 · Cryogenian Snowball
`720–635 Ma · 20:00–20:40`

```
c0  #F2F3F5  near-white cool    ice / cloud
c1  #D6E4F2  pale blue          ice surface — 20% coverage
c2  #A9B5E0  muted blue-grey    partially frozen ocean
c3  #2F456F  dark slate blue    exposed ocean / deep shadow
c4  #0A1428  near-black navy    silhouette
```

`noiseThresh1: 0.50, noiseThresh2: 0.65` · `blendStart: 637` (2 Ma thaw into Hothouse World)

Short ramp in (2 Ma from BB late), short ramp out (2 Ma). Very low surface intensity (0.28). `useLandSea: 0.35` — continents faintly visible beneath ice. First phase with SDF paleo data.

**Haze:** `#F2F3F5` blue-white · opacity 55%

**Dark haze:** `#AEBFCC` icy blue-grey · opacity 65%

---

## 11 · Hothouse World
`635–400 Ma · 20:40–21:55`

```
c0  #E2C6A8  warm cream-tan     heavy atmosphere / cloud
c1  #7C6E60  barren brown-grey  sediment-heavy land
c2  #159F78  vivid emerald      shallow algal ocean
c3  #1E5A75  dark teal-blue     deep ocean
c4  #032832  near-black teal    silhouette
```

`noiseThresh1: 0.46, noiseThresh2: 0.56` · `blendStart: 470` (70 Ma ramp into Green World)

Full SDF paleo data (`useLandSea: 1.0`). Algal blooms dominate — mediterranean vibes. Cloud shape begins shifting (0.40).

**Haze:** `#E2C6A8` warm atmosphere · opacity 45%

**Dark haze:** `#8C5A2B` warm sienna · opacity 55%

---

## 12 · Green World
`400–66 Ma · 21:55–23:40`

```
c0  #CFEAF7  hazy blue          warm atmosphere / cloud
c1  #1E7A3D  dark mossy green   vegetation
c2  #13906B  deep emerald       ocean primary
c3  #0D664B  darker emerald     deep ocean
c4  #011F15  near-black green   silhouette
```

`noiseThresh1: 0.46, noiseThresh2: 0.56` · `blendStart: 400` (full-span drift into Modern Earth)

Full SDF paleo data. Swirled clouds (0.65). Continuous drift across the full 334 Ma span into Modern Earth.

**Haze:** `#CFEAF7` humid blue · opacity 30%

**Dark haze:** `#5F8FA8` muted teal-blue · opacity 40%

---

## 13 · Modern Earth
`66 Ma–now · 23:40–24:00`

```
c0  #F4F8FB  cool white         Apollo cloud + polar ice
c1  #5FAE55  mid green          land / vegetation
c2  #2F6F9E  medium blue        ocean primary
c3  #174663  dark navy-blue     deep ocean
c4  #041528  near-black navy    silhouette
```

`noiseThresh1: 0.46, noiseThresh2: 0.56` · `blendStart: 0` · `cloudDensity: 0.26`

Full SDF paleo data. Full Apollo swirl clouds (1.0) + polar ice caps (`polarIce: 0.85`). Cloud density matched to Green World to avoid a heavy overcast look. c0 is the only phase where the atmosphere colour is intentionally visible — shared between cloud and ice so they read as one family.

**Haze:** `#F4F8FB` minimal cool · opacity 8%

**Dark haze:** `#A8C0D6` pale cool blue · opacity 30%
