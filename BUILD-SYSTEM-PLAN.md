# Build System Plan — One Source, Three Targets

How to keep `eona.html` as the single source of truth while making every UI/globe
change apply cleanly to **web**, **Pi**, and the planned **desktop app** — without
duplicated blocks that drift apart. Plus one live deployment bug (Pi clock out of
sync after power-off), fixed first as Phase A.

---

## Review of the current approach

**What exists:** `eona.html` (3,140 lines / 851 KB — the bulk is two base64 SDF
atlas strings) preprocessed by `build.sh`, a 106-line awk script that includes or
strips `<!-- @if WEB/PI -->` blocks. There are 10 directive sites, all WEB/PI pairs:

| Site | Lines | Difference |
|---|---|---|
| `<head>` | 6–36 | meta/OG/CDN fonts/CDN three.js vs. local three.js |
| `@font-face` | 38–53 | Pi-only local fonts |
| `--clock-size` | 71–76 | responsive vs. 1080px fixed |
| mobile media query | 85–89 | web-only |
| `html, body` | 92–101 | flexbox-centred vs. 1080px fixed |
| `.clock-container` | 127–137 | relative/var-sized vs. absolute/1080px |
| renderer `antialias` | 1677–1682 | true vs. false |
| renderer size/DPR + `EDGE_ALPHA_START` | 1686–1704 | full-res/DPR≤2/0.97 vs. half-res/DPR1/0.88 |
| sphere geometry | 1707–1712 | 48×48 vs. 32×32 |
| resize handler | 1831–1839 | full-res vs. half-res |

**The verdict:** the single-file + preprocessor architecture is right for this
project and should be kept. It's what makes the Pi offline build possible (base64
atlases avoid `file://` WebGL texture tainting), and 3,140 lines is manageable.
The problems are all in the *mechanics*, and they compound exactly when a third
platform arrives:

### Problems found

1. **Pi clock out of sync after power-off (live bug).** The Pi 5 has no RTC
   battery; time is lost when unplugged and correction depends on NTP working.
   Diagnosis and fix in Phase A — notably, no `eona.html` change is needed.
2. **Asset copy bug (active right now).** `cp -r images dist/web/images` copies
   *into* the destination when it already exists. `dist/pi/fonts/fonts/` and
   `dist/pi/images/images/` currently exist from repeated builds — duplicate
   megabytes shipped to the Pi, and it compounds every rebuild.
3. **Platform names hardcoded in awk** (`build.sh:43` — `(WEB|PI)`). Adding
   DESKTOP means editing regex, and any future platform again.
4. **No OR syntax** (`@if WEB|DESKTOP`). Per DESKTOP-APP-PLAN.md, desktop is
   "same as WEB" at 4 of 6 sites and "same as PI" for fonts. Without OR lists,
   every one of those becomes a *copied* block — renderer config, resize handler,
   sphere geometry, container CSS would each exist twice and silently drift. This
   is the single biggest threat to "change once, apply everywhere."
5. **No validation.** A typo'd directive (`@if WEBB`, `@fi`) passes silently into
   production HTML; an unbalanced block can include the wrong platform's code
   with no error. Nothing checks the output.
6. **No "what did my edit touch" feedback.** After editing, there's no quick way
   to confirm a change landed in (only) the platforms you intended.
7. **No provenance.** No way to tell which commit the Pi, the web deploy, or a
   packaged desktop app is actually running.
8. **Scattered per-platform CSS.** One platform's presentation lives in 5
   separate paired blocks; understanding "what does Pi override" means reading
   the whole stylesheet.
9. **Raw `eona.html` is not runnable** (both platforms' `const EDGE_ALPHA_START`
   coexist → SyntaxError), so all testing goes through `dist/` — fine, but the
   edit→see loop is manual (`./build.sh web`, refresh) and undocumented.
10. **Minor:** the Pi `@font-face` block omits Space Mono 700 (the file is copied
    but no face is declared → synthetic bold for event names on Pi).

---

## Phase A — Pi boot time-sync bug fix

> **Status (2026-07-15): A1 complete and verified.** Actual root cause was one
> step upstream of the A1 hypotheses: NetworkManager had **no saved WiFi profile
> at all** (lost in the NVMe reflash), so the Pi had no path to NTP after power
> loss — timesyncd itself was already active. Fixed with a system-wide
> autoconnect profile; full command and verification in CLAUDE.md → Known Issues
> (Pi). **A2 (RTC battery) declined 2026-07-15 — no further hardware spend; the
> WiFi/NTP fix is the accepted solution. A3 skipped** — with WiFi restored, sync
> lands ~10 s after boot. Phase A is closed.

First because it's a live bug on the installed clock, and it's independent of
all the build-system work — nothing else in this plan depends on it or blocks it.

**Symptom:** after the Pi has been powered off, the clock shows the wrong local
time on boot.

### Diagnosis — the page is not the problem

The tick loop reads `new Date()` **every frame** (`eona.html:2997`), so the page
self-corrects the instant the OS clock is corrected — no reload needed. The one
load-time capture, `_initMa` (`eona.html:1211`), only seeds the first-paint
accent colour and is overwritten on the first frame. Nothing page-side latches a
stale time.

The stale time is the **Pi's system clock**. The Pi 5 has an RTC on board but
**no battery installed** — when wall power is removed, time is lost. On boot the
OS restores the last-saved timestamp (stale by however long the Pi was
unplugged), and correction then depends entirely on NTP: WiFi coming up *and*
`systemd-timesyncd` being enabled. If either fails — timesyncd disabled, the
WiFi connection saved as user-scoped instead of system-wide (so it only connects
after login), or no internet at the install location — the clock stays wrong
indefinitely.

### A1. Software fix (free — do first)

On the Pi:

```sh
timedatectl                      # expect "NTP service: active",
                                 # "System clock synchronized: yes"
sudo timedatectl set-ntp true    # enable systemd-timesyncd if it wasn't
nmcli connection show            # WiFi connection must be system-wide with
                                 # autoconnect, not user-scoped
```

`systemd-timesyncd` **steps** the clock on first sync (it doesn't slew large
offsets), and the page picks up the corrected time the same frame — Chromium
never needs restarting. This alone fixes the reported bug whenever the Pi has
network.

### A2. Hardware fix (declined — kept for reference only)

Official **Raspberry Pi 5 RTC battery** (rechargeable ML2020, plugs into the
board's J5 "BAT" connector, ~£5). The clock then survives power-off with no
network at all — the right property for a wall clock that gets unplugged and
moved. Enable trickle charging once:

```sh
sudo rpi-eeprom-config --edit    # add: rtc_bbat_vchg=3000000
```

Add the battery to the hardware components list in CLAUDE.md / PI-SETUP.md.

### A3. Optional: hold the kiosk until first sync

With only A1, there's a brief window after boot where Chromium renders the stale
time before the first NTP step. If that bothers, wrap the autostart `Exec` in a
script that waits up to ~15 s for
`timedatectl show -p NTPSynchronized --value` to report `yes`, then launches
Chromium regardless (so the clock still starts when offline). With A2 installed
this is unnecessary — skip it unless the boot-window flash proves annoying.

### Verification

Unplug the Pi for 5+ minutes, plug back in: the displayed local time must be
correct within ~a minute of boot (A1) or immediately (A2). `timedatectl` reports
synchronized. Document the fix and remove/annotate the bug in CLAUDE.md's Known
Issues (Pi).

---

## Phase B — Harden `build.sh` (output must stay byte-identical)

Pure infrastructure; web and Pi outputs must not change. This lands **before**
any desktop work so the desktop plan's "byte-identical" gate is trustworthy.

### B1. Fix the asset copy

```sh
copy_assets() {  # copy_assets <src-dir> <dest-dir>
  rm -rf "$2"
  mkdir -p "$(dirname "$2")"
  cp -R "$1" "$2"
}
```

Use it in every case branch. One-time cleanup: `rm -rf dist` locally **and on the
Pi** (`ssh pi@eona.local 'rm -rf ~/eona/dist'` before the next pull+build).

### B2. Token-agnostic directives with OR lists

- awk matches `@if [A-Z_|]+` generically — no platform list in the regex, no
  script edit per new platform.
- The token is split on `|`; the block is included if **any** listed platform
  matches the target: `<!-- @if WEB|DESKTOP -->`.
- Each token is checked against the known-platform list (passed from the shell
  case statement); an unknown token is a hard build failure — this converts
  silent typos into errors.

### B3. Output validation

After writing each output file:
- Fail if it still contains `@if`, `@else`, or `@endif` (catches malformed
  directives that slipped through the strip pass).
- Fail if awk's `END` block sees `depth != 0` (unbalanced `@if`/`@endif`).

### B4. `all` by default + a `check` mode

- Bare `./build.sh` builds **all** targets — makes "rebuild everything" the
  default habit, so no target quietly goes stale.
- `./build.sh check`: builds all targets to a temp dir, runs the B3 validations,
  and prints a per-target diffstat against the current `dist/`. This is the
  direct answer to "did my change apply to every app I meant it to?" — after any
  edit you see exactly which platforms' outputs changed, and by how much.

### B5. Verification

`./build.sh all`, then diff web and Pi outputs against pre-change builds — byte
identical (after the duplicate-directory cleanup, which only removes junk).

---

## Phase C — Collapse value-only differences into a platform config

Most directive sites don't guard *different code* — they guard *different
constants* flowing through identical code. Move the constants into data and share
the code. Directive sites drop from **10 to 4**, and a new platform becomes "add
one config object + one CSS block" instead of ten scattered edits.

### C1. One `PLATFORM` object per target

A single small `@if` block near the top of the `<script>`:

```js
<!-- @if WEB -->
const PLATFORM = { name: 'web', antialias: true,  renderScale: 1,   maxDPR: 2, sphereSegments: 48, edgeAlphaStart: 0.97 };
<!-- @endif -->
<!-- @if PI -->
const PLATFORM = { name: 'pi',  antialias: false, renderScale: 0.5, maxDPR: 1, sphereSegments: 32, edgeAlphaStart: 0.88 };
<!-- @endif -->
```

### C2. Shared renderer + resize path

The four JS directive sites (1677, 1686/1693, 1707, 1831) collapse into one code
path reading `PLATFORM`:

```js
earthRenderer = new THREE.WebGLRenderer({ canvas, antialias: PLATFORM.antialias, alpha: true });
earthRenderer.setClearColor(0x000000, 0);

function sizeRenderer(size) {
  earthRenderer.setSize(Math.floor(size * PLATFORM.renderScale), Math.floor(size * PLATFORM.renderScale));
  earthRenderer.setPixelRatio(Math.min(window.devicePixelRatio, PLATFORM.maxDPR));
  canvas.style.width = size + 'px';   // harmless on web; required for Pi's CSS upscale
  canvas.style.height = size + 'px';
}
sizeRenderer(size);
const EDGE_ALPHA_START = PLATFORM.edgeAlphaStart;

const geometry = new THREE.SphereGeometry(1, PLATFORM.sphereSegments, PLATFORM.sphereSegments);

window.addEventListener('resize', () => sizeRenderer(container.offsetWidth || 150));
```

(On Pi, `renderScale: 0.5` + `maxDPR: 1` reproduces the current half-res +
CSS-upscale behaviour exactly; explicit `canvas.style` sizing overrides the
default style that `setSize` writes, matching today's Pi code.)

### C3. Consolidate per-platform CSS into one block per platform

- Base rules become platform-neutral with **web values as the default** (web is
  the reference rendering).
- Each platform gets **one** override block at the end of `<style>` (cascade
  order does the work — no specificity games):

```css
<!-- @if PI -->
/* === Pi overrides: fixed 1080×1080 kiosk === */
:root { --clock-size: 1080px; }
html, body { width: 1080px; height: 1080px; }
body { display: block; background: #000000; }
.clock-container { position: absolute; inset: 0; }
.clock-container::before { background: var(--bg); }
<!-- @endif -->
```

The web mobile media query lives in web's block; the `@font-face` block is kept
separate and becomes `@if PI|DESKTOP` when desktop lands (it's "local-asset
platforms," not Pi-specific). Add the missing **Space Mono 700** face while
touching it (fixes problem 10).

### C4. What stays as structural directives (correctly)

- `<head>`: meta/OG/analytics/CDN vs. local script tags — genuinely different
  markup, stays `@if WEB` / `@if PI` (+ `PI|DESKTOP` sharing later).
- `@font-face` block.
- Per-platform CSS override block.
- `PLATFORM` const block.

### C5. Verification

Outputs are intentionally *not* byte-identical here (code moved), so verify
behaviourally: web via `server.js` (globe, clouds, haze alignment, scrub, events,
resize, mobile media query); Pi by opening `dist/pi/clock.html` in desktop Chrome
— the half-res render, 32-seg sphere, and wider edge fade are all observable
without hardware — then a real `git pull && ./build.sh pi && sudo reboot` on the
Pi.

---

## Phase D — Workflow: provenance + tight edit loop

### D1. Build stamp

`build.sh` replaces a `__BUILD_INFO__` token with `<platform> <git short-sha>
<iso-date>` — emitted as an HTML comment near the top and a one-line
`console.log`. Answers "what is this screen actually running?" for all three
targets: `grep built dist/pi/clock.html` after a Pi pull, view-source on
eona.earth, console in the desktop app.

### D2. Auto-rebuild in `server.js`

On each request for `/index.html`, if `eona.html` is newer than
`dist/web/index.html`, re-run `./build.sh web` before serving. The dev loop
becomes **edit → refresh** with no extra terminal, no watcher process, no new
dependencies. (A `./build.sh watch` fswatch loop is the alternative; the
server.js hook is less machinery.)

### D3. Document the canonical loop in CLAUDE.md

- Develop: edit `eona.html` → refresh `localhost:3000` (auto-rebuilds).
- Pre-commit: `./build.sh check` — confirms which targets the change touched and
  that no directive residue leaked.
- Deploy web: push (Vercel runs `./build.sh web`).
- Deploy Pi: `ssh pi@eona.local`, `git pull && ./build.sh pi && sudo reboot`.
- Deploy desktop (once built): `./build.sh desktop && cd desktop && npx electron-builder`.
  With the remote-content update design (preferred; see DESKTOP-APP-PLAN.md
  deferred list), this packaging step is only needed for shell changes — desktop
  *content* ships with the web push.
- Note explicitly: raw `eona.html` is not runnable — always test via `dist/`.

---

## Phase E — Source split (deferred, deliberately)

Splitting `eona.html` into `src/` parts (head, CSS, shader, JS, base64 atlas
data) concatenated by the build would shrink diffs and get the 800 KB atlas
strings out of the editing path — but it trades away the one-file simplicity,
grows the build script, and solves a pain (file size/diff noise) that isn't the
one blocking cross-platform changes. After Phase C the file has 4 directive
sites and changes flow to all targets by construction.

**Revisit triggers:** wanting to share shader source with `colour-lab.html`
(currently a fork that drifts), or the directive count creeping back past ~8.

---

## Impact on DESKTOP-APP-PLAN.md

Phases B–D should land **before** desktop Phase 1, as standalone commits. The
desktop plan then simplifies:

- **Phase 1a** mostly dissolves: no awk regex edit (B2 made it token-agnostic);
  the desktop case branch is `build DESKTOP dist/desktop/app/index.html` +
  `copy_assets` calls; `all` already includes it.
- **Phase 1b's six-row table collapses to ~4 small additions:**
  - *Renderer, resize, sphere geometry, `EDGE_ALPHA_START`* — **zero new
    blocks**. Desktop is one `PLATFORM` object: `{ name: 'desktop',
    antialias: true, renderScale: 1, maxDPR: 2, sphereSegments: 48,
    edgeAlphaStart: 0.97 }`.
  - *Fonts + local three.js* — flip existing blocks to `@if PI|DESKTOP`
    (mono-700 already added in C3).
  - *CSS* — one desktop override block (`--clock-size: min(100vw, 100vh)`;
    transparent `html`/`body`; `overflow: hidden`). `.clock-container` inherits
    the web-default base rule — no desktop copy.
  - *Head* — small `@if DESKTOP` block (title, favicon; no OG/analytics).
  - Desktop-only drag-ring/resize-ring CSS and the `window.eona` bridge script
    remain `@if DESKTOP` as planned.
- **Phase 6 checklist upgrades:** the "web/pi outputs byte-identical" gate is
  automated by `./build.sh check`; the D1 build stamp verifies the packaged app
  contains the intended build; and because the bridge script is guarded by
  `if (window.eona)`, `dist/desktop/app/index.html` is smoke-testable in plain
  Chrome — add that to the checklist.
- **Ongoing benefit — the actual goal:** a globe/shader/UI change touches shared
  code once and reaches all three apps on the next build; a per-platform tuning
  change (e.g. Pi drops to 24 segments, desktop caps DPR at 1.5 for battery) is
  a one-line edit to that platform's `PLATFORM` object or CSS block, invisible
  to the other two.

Once Phases B/C land, update DESKTOP-APP-PLAN.md Phase 1 to reference this
document (its current instructions — regex edit, per-site block table — will be
stale).

---

## Suggested order

| Step | Size | Gate |
|---|---|---|
| ~~A. Pi time-sync fix~~ **done 2026-07-15** (A2 battery declined) | — | verified: sync ~10 s after cold boot |
| B. build.sh hardening | small | web+pi outputs byte-identical |
| D1–D2. stamp + auto-rebuild | small | stamp visible in all outputs |
| C. PLATFORM config + CSS consolidation | medium | visual verification web + Pi-build-in-Chrome + on-device |
| D3. CLAUDE.md workflow docs | small | — |
| Desktop plan Phase 1+ | per its own plan | `./build.sh check` clean |

Each phase is its own commit; the repo stays deployable to web and Pi throughout.
