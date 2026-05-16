# Eona.Earth — Project Brief

A website that maps Earth's 4.5-billion-year history (and future) onto a clock face. When you look at it at 10:34am, you're seeing the Cambrian explosion. At 11:39, the dinosaurs go extinct. Humans appear in the last 3 seconds before noon.

The goal is visceral understanding — not education, but feeling. The "holy shit" moment when abstraction clicks into physical intuition.

Live at [eona.earth](https://eona.earth). Single HTML file (`eona.html`), vanilla JS + Three.js, no build step.

---

## What it is

A clock with three toggleable layers:
- **Globe** — WebGL sphere with a custom shader. Surface changes continuously through geological eras. Uses SDF (signed-distance field) paleogeographic maps for the last 635 Ma; procedural noise for everything older.
- **Eons ring** — SVG pie slices, one per geological eon, progressively revealed as the clock hand moves.
- **Clock face** — Minute hand + tick marks.

A scrubber handle on the clock ring lets you drag through geological time. Scrubbing shows event descriptions in the centre. Event dots mark significant moments on the ring.

### Visual language
- True black background. White/grey for structure. Single accent: `#E34E2A` (orange-red) for the scrubber handle, active events, and time display.
- **Space Mono** for all UI text. **Fraunces** for event descriptions.
- References: NASA worm logo, CMF/Nothing watch faces, Voyager Golden Record, Icinori illustration studio.

---

## Current state (May 2026)

**The 24-hour future extension is fully built and recently tuned.**

The clock now runs on a 24-hour cycle:
- **00:00–12:00** = 4,540 Ma ago → Present (past)
- **12:00–24:00** = Present → +4,540 Ma (future)

Both halves have:
- Globe visuals (STATES / FUTURE_STATES arrays, each ~12–14 waypoints)
- Event markers with descriptions
- Eon/phase ring segments with progressive reveal
- SDF continent data (past: 11 atlas slices back to 635 Ma; future: 7 slices forward to +250 Ma from Scotese reconstructions)

The most recent commit (today) reworked the past/future palette and cloud treatments.

### The six future phases

| Phase | Clock | What you see |
|-------|-------|--------------|
| Near Earth (+0 to +250 Ma) | 12:00–12:40 | Modern Earth getting hotter. Real SDF continent data. |
| Supercontinent (+250 to +600 Ma) | 12:40–13:35 | Continents merge into Pangaea Proxima, then break apart. SDF data ends at +250 Ma — certainty dissolves into procedural noise. |
| Dying Biosphere (+600 to +1,500 Ma) | 13:35–15:58 | Greens drain. Last plants, then last complex life. Pale tan. |
| Ocean Loss (+1,500 to +3,000 Ma) | 15:58–19:56 | Thick steam haze, then sulphur yellow as oceans boil away. |
| Terminal Earth (+3,000 to +4,300 Ma) | 19:56–23:22 | Dark reddish-brown. No clouds. No geography. |
| Red Giant (+4,300 to +4,540 Ma) | 23:22–24:00 | Globe remolten. Glowing red. Fades to black. |

Mirrors the past: Hadean chaos → life → Modern Earth → life ends → Red Giant chaos. Black → black.

---

## Key design decisions already made

**Dual-render cross-fade.** The shader renders two adjacent STATES per frame and blends between them. This lets each state have its own noise seed and surface approach, dissolving cleanly rather than morphing in noise space.

**SDF atlas for continents.** For the ~635 Ma where paleogeographic data exists, the shader uses signed-distance fields (Scotese PaleoMAP data). Pure procedural noise for everything older (and for the future beyond +250 Ma). The crossfade at +250–300 Ma is a deliberate design moment: certainty dissolving.

**Per-state surface and cloud approach.** Each STATES entry can specify:
- Surface: `screenprint` (hard-edged, Icinori riso) / `watercolor` (soft, early eras) / `topographic` (ridged, molten eras)
- Clouds: `warped_layers` (thick, heavy) / `warped_wisps` (brushstroke, modern) / `warped` (banded, transitional)

**Future accent colour.** Future half uses a slightly different accent (cooler orange) to distinguish past/future visually. The eon ring segments have mirrored opacity: high certainty phases are bright, speculative phases fade — ramps up through the past (Hadean dim → Cenozoic bright) then back down through the future.

**Cumulative angle scrubbing.** The scrubber tracks raw angle delta rather than position, so it can cross midnight/noon boundaries without getting stuck in a 12-hour window.

---

## Backlog

In rough priority order:

- **Eon/era labels** — curved text on the ring slices naming each eon.
- **Keyboard navigation** — jump between events with arrow keys.
- **Sound design** — ambient audio shifting with geological time.
- **Watch / mobile app**
- **Physical build** — Waveshare display + Raspberry Pi 4

---

## Technical snapshot

**File structure:**
- `eona.html` — everything (single file, ~5,000 lines)
- `colour-lab.html` — interactive per-phase colour/shader editor
- `cloud-compare.html`, `surface-compare.html` — render comparison labs
- `generate_future_sdf.py` — Python script that generated the future SDF atlas
- `colour-reference.md` — per-phase palette notes
- `FUTURE-EARTH.md` — full future phase spec
- `FUTURE-EARTH-BUILD-PLAN.md` — implementation plan (all phases now complete)
- `CLAUDE.md` — comprehensive technical reference for Claude Code

**Stack:** Vanilla JS + HTML + CSS. Three.js r128 (CDN) for WebGL. Google Fonts CDN. No build step. Deployed on Vercel.

**Key globals:** `_currentMa`, `_activeEventMa`, `_handleLatched`, `_handleHovered`, `scrub.cumulativeAngleDelta`

**Key constants:** `STATES` (14 past waypoints), `FUTURE_STATES` (13 future waypoints), `EVENTS` (past events), `FUTURE_EVENTS` (future events), `SDF_ATLAS_BASE64`, `FUTURE_SDF_ATLAS_BASE64`

---

## What makes this tricky

- The SDF atlas has two orientation gotchas that keep resurfacing: `flipY = false` and `atan(p.z, -p.x)` longitude. If continents look wrong, check these first.
- `timeToMa` uses `hours % 12` for the past (both AM and PM), now extended to distinguish the future half.
- Event dots at 12 o'clock are ambiguous — both 0 Ma (present) and 4540 Ma (Earth forms) map to the same position. Fixed with a Ma-proximity check (`|time - ma| < 300`).
- The shader does dual-render (A + B pass per pixel) — heavier when adjacent states use different `surfaceApproach` values.
