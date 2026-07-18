# Eona Desktop App — Implementation Plan

A floating, always-on-top, circular desktop widget version of the clock. Built from the
same `eona.html` source via the same `build.sh` preprocessing used for web and Pi.
Distributed as a download from eona.earth.

**Framework: Electron.** Guarantees the exact Chromium rendering path the web build
already uses — the WebGL shader, SDF atlas sampling, and CSS blend-mode haze layers
behave identically. Tauri would be ~10 MB instead of ~150 MB but runs on system
webviews (WKWebView / WebView2), where `mix-blend-mode: multiply` over WebGL and
transparent-window compositing are less predictable.

---

## Phase 0 — Decisions (all settled 2026-07-18)

1. **Window-drag zone vs. clock gestures — settled: margin ring.** The entire
   `.clock-container` owns pointer events (scrub handle, drag-to-rotate-globe),
   so a whole-face `-webkit-app-region: drag` would swallow all of those:
   - **Margin ring** (SVG r 174–200, the outer 13% band holding the logo/arc text
     margin) → window drag. *Accepted tradeoff: drag-to-rotate-globe no longer
     works when started in this band. Everything inside r 174 behaves exactly as
     on web.*
   - **Outermost ~8 px of the circle edge** → resize zone (see Phase 4).
2. **Minimum / default window size — settled: default 600×600, minimum 320×320.**
   (Owner's call, revisable once it's on screen. Comfortably above the ~220 px
   floor where the 8 px-SVG arc text turns unreadable.)
3. **macOS Spaces behaviour — settled: stays on its Space.**
   `visibleOnAllWorkspaces` stays **false** — conventional window behaviour, no
   cross-desktop following. (Could become a preferences toggle when the tray
   icon lands post-v1.)
4. **Code signing — settled: sign from day one.** macOS unsigned apps are blocked
   by Gatekeeper ("damaged / unidentified developer"), so distribution from
   eona.earth realistically requires an Apple Developer ID ($99/yr) +
   notarization regardless — and shell auto-update ships in v1 (Phase 5c), which
   hard-requires signed builds on macOS (Squirrel.Mac refuses unsigned updates).
   Windows signing stays optional for v1 (SmartScreen warning is dismissible;
   unsigned auto-update works).

---

## Phase 1 — Build-step integration (`DESKTOP` target)

### 1a. Extend `build.sh`

- The awk directive regex on line 43 hardcodes platforms:
  `/@if[[:space:]]+(WEB|PI)/` → change to `(WEB|PI|DESKTOP)`.
- Add case branch:
  ```sh
  desktop)
    build DESKTOP "dist/desktop/app/index.html"
    cp -r images dist/desktop/app/images
    cp -r fonts  dist/desktop/app/fonts
    cp -r lib    dist/desktop/app/lib
    ;;
  ```
- Add `desktop` to the `all` branch and the usage string.
- Note: `dist/desktop/app/` (not `dist/desktop/`) so Electron packaging metadata can
  live beside the built page without being served/copied confusion.
- `do_check()`'s per-target pair list (`"web:$WEB_OUT:...", "pi:$PI_OUT:..."`)
  is hand-written, not derived from `PLATFORMS` — POSIX `sh`/dash has no
  arrays, so there's no cheap generic derivation. Add a third `"desktop:..."`
  entry by hand here too.

> This whole section (1a/1b) predates Phases B and C of `BUILD-SYSTEM-PLAN.md`
> and is stale in its specifics — the awk regex and `cp -r` calls it
> describes no longer exist (replaced by `PLATFORMS`/token validation and
> `copy_assets()`), and Phase C collapsed most of 1b's six-row table into a
> shared `PLATFORM` object. Re-derive this section from the current
> `build.sh` and `eona.html` before starting Phase 1, rather than following
> these specifics literally.

### 1b. Add `<!-- @if DESKTOP -->` blocks to `eona.html`

Desktop is "web rendering quality + Pi offline assets + transparency". Blocks needed
at each existing `@if` site:

| Site (current line) | WEB | PI | DESKTOP |
|---|---|---|---|
| `<head>` (~6–36) | meta/OG/CDN fonts/CDN three.js/Vercel insights | local three.js | local three.js + local fonts (`@font-face` like Pi), no analytics, no OG meta |
| `--clock-size` (~72–76) | `min(100vw−96px, 100vh−96px)` | `1080px` | `min(100vw, 100vh)` — clock fills window exactly, resizes with it |
| `html, body` (~93–101) | `#0e0e0e` page bg | 1080px fixed, black | `background: transparent` on html AND body; `overflow: hidden`. The black circle comes from `.clock-container::before` (`var(--bg)`, unconditional — same rule for all three platforms as of Phase C; there is no longer a web-only `::before` override to avoid copying) |
| `.clock-container` (~127–137) | relative, `var(--clock-size)` | absolute 1080px | same as WEB |
| Renderer (~1677–1712) | antialias, DPR ≤2, 48×48 sphere | half-res, 32×32 | same as WEB |
| Resize handler (~1831–1839) | setSize + DPR | half-res | same as WEB |

Plus desktop-only additions (inside `@if DESKTOP`):

- CSS for the drag ring and resize ring (Phase 3/4).
- A small `<script>` for renderer-side window logic: hover-based click-through
  toggling, resize-drag IPC calls (Phase 2–4). Communicates with the main process
  via the `window.eona` bridge exposed by `preload.js`.

Font note: reuse the Pi `@font-face` block content (`space-grotesk-variable.woff2`,
`space-mono-400.woff2`); add `space-mono-700.woff2` if the bold arc-text weight is
used (Pi block currently omits it — verify rendering).

---

## Phase 2 — Electron shell

New top-level `desktop/` directory (checked in; `dist/` stays git-ignored build output):

```
desktop/
  package.json        # electron + electron-builder devDeps, build config
  main.js             # window creation, IPC handlers
  preload.js          # contextBridge → window.eona API
  icons/              # icon.icns, icon.ico, icon.png (from logo/favicon art)
```

### `main.js` — BrowserWindow config

```js
new BrowserWindow({
  width: 600, height: 600,       // Phase 0.2
  minWidth: 320, minHeight: 320,
  frame: false,
  transparent: true,
  backgroundColor: '#00000000',
  hasShadow: false,            // macOS square shadow would betray the bounding box
  alwaysOnTop: true,           // level 'floating' on macOS so it sits above normal windows but below panels
  resizable: false,            // native resize off — we own resize (Phase 4)
  fullscreenable: false,
  skipTaskbar: false,          // decide: widget-like (true) vs app-like (false)
  webPreferences: { preload, contextIsolation: true, nodeIntegration: false }
})
win.setAspectRatio(1)          // keep square even through our custom resize
// visibleOnAllWorkspaces stays false per Phase 0.3 — window lives on one Space
win.loadFile('../dist/desktop/app/index.html')  // resolved relative to app root in dev; packaged path via app.getAppPath()
```

Gotchas to handle:

- **Transparent windows disable native resize on Windows** — that's fine, custom
  resize is the plan regardless; just ensure `resizable: false` everywhere so
  behaviour matches across platforms.
- **`transparent: true` requires the window be created after `app.whenReady()`**
  and on some Linux WMs needs `--enable-transparent-visuals`; Linux is explicitly
  out of scope for v1 (macOS + Windows only).
- App lifecycle: quit on window close (no dock-lurking), single-instance lock.

### `preload.js` — bridge API

```js
contextBridge.exposeInMainWorld('eona', {
  version: 1,   // bump on every addition/change to this API
  setIgnoreMouse: (ignore) => ipcRenderer.send('ignore-mouse', ignore),
  beginResize:    ()       => ipcRenderer.send('begin-resize'),
  resizeDelta:    (d)      => ipcRenderer.send('resize-delta', d),
  quit:           ()       => ipcRenderer.send('quit'),
})
```

### Bridge guard convention (version skew)

With remote-content updates (see Deferred), the HTML evolves faster than the
installed shells running it — a user's shell may be months old. The HTML must
therefore never assume a bridge method exists:

- Guard every call site: `window.eona?.setIgnoreMouse(...)` — never bare
  `window.eona.method(...)`. This also covers the same built HTML opened in a
  plain browser for debugging (no bridge at all), and the web/Pi builds if any
  shared code path touches desktop features.
- Gate whole features on capability, not platform: `if (window.eona?.beginResize)`
  around the resize-ring wiring, not `if (PLATFORM.name === 'desktop')` — old
  shells then degrade gracefully (feature absent) instead of throwing.
- `version` is exposed for coarse checks and diagnostics (e.g. logging shell
  version alongside the build stamp), but per-method feature detection is the
  primary mechanism — it can't drift out of sync with reality.
- Never remove or change the signature of a shipped bridge method; add new
  methods instead. Removal requires being confident no live HTML calls it.

---

## Phase 3 — Round window: transparency, click-through, drag

### 3a. Circle rendering

Nothing new needed — `.clock-container::before` already draws the black disc with
`border-radius: 50%`. With html/body transparent, the corners of the square window
are genuinely transparent.

### 3b. Click-through on transparent corners

Without this, the invisible corners steal clicks from windows underneath — the #1
"feels broken" bug for circular widgets.

- Renderer listens to `mousemove` on `document`; computes whether the pointer is
  inside the circle (distance from window centre ≤ half of `min(innerWidth,
  innerHeight)`, plus a few px of slack for the resize ring).
- On transition in/out: `window.eona.setIgnoreMouse(outside)` → main calls
  `win.setIgnoreMouseEvents(outside, { forward: true })`. The `forward: true` is
  essential — it keeps mousemove flowing while ignored, so we can detect re-entry.
- Throttle the IPC (only send on state *change*, not every move).

### 3c. Window dragging

- Add a desktop-only overlay div: a ring covering SVG radii 174–200 (in CSS:
  absolutely positioned full-size circle with a transparent centre via
  `mask: radial-gradient(...)` or simply a `::after` ring), with
  `-webkit-app-region: drag`.
- Everything inside r 174 gets `-webkit-app-region: no-drag` (the default; just
  ensure the drag ring doesn't cover it — use the mask so the ring's hit area
  really is annular, since `app-region` respects element hit-testing).
- Verify: scrub handle drag, globe rotate, and event-dot hover all still work
  (their pointer events live on `.clock-container` inside the ring).

---

## Phase 4 — Custom edge resize

Frameless + transparent means no native resize affordance. Implement in the renderer:

1. **Resize ring**: outermost ~8 px annulus of the circle. On `mousemove` within it,
   set `cursor: nwse-resize` (or compute direction-appropriate cursor from angle).
   This ring must be `-webkit-app-region: no-drag` (it sits inside the drag ring's
   outer edge — order the hit zones: 0–174 clock, 174–196 drag, 196–200 resize).
2. **Drag to resize**: on `pointerdown` in the ring, capture pointer;
   `beginResize()` records the window's current bounds in main. Each `pointermove`
   sends the screen-space delta; main computes the new square size
   (`size + delta·direction`, clamped to min 320) and calls `win.setBounds()`
   **resizing around the window centre** (adjust x/y by half the size delta) so the
   clock grows/shrinks in place instead of from the top-left corner.
3. **Renderer follows automatically**: `--clock-size: min(100vw, 100vh)` re-derives
   everything from the viewport; the existing `resize` listener (line ~1829) already
   re-sizes the WebGL canvas. Verify the drop-shadow glow and haze layers track,
   since they're sized in `calc()` off `--clock-size` — they should be free.
4. **Performance**: `setBounds` per mousemove can jitter; coalesce with
   `requestAnimationFrame` on the renderer side before sending deltas.

---

## Phase 5 — Packaging & distribution

### 5a. electron-builder

Config in `desktop/package.json`:

- `files`: `main.js`, `preload.js`, plus `extraResources` (or `files` glob) pulling
  in `../dist/desktop/app/**` — the build script order is therefore
  `./build.sh desktop && cd desktop && npx electron-builder`.
- Targets: macOS `dmg` + `zip` (universal or separate arm64/x64 — propose
  **universal** for one download link), Windows `nsis`.
- App identity: `appId: earth.eona.clock`, product name "Eona", icons from
  `desktop/icons/`.

### 5b. Signing / notarization (required — Phase 0.4, settled)

- macOS: Developer ID cert + `notarize` config in electron-builder
  (`@electron/notarize`, App Store Connect API key). Without it, downloads are
  effectively broken for non-technical users.
- Windows: optional for v1; SmartScreen warning is dismissible.

### 5c. Shell auto-update (`electron-updater`) — in v1

The updater is the one capability that cannot be retrofitted remotely: every
other feature can reach installed shells later *through* it, but a shell shipped
without it is permanently manual. So it ships in v1, small as it is:

- `electron-updater` with the GitHub Releases provider (matches 5d hosting).
  In `main.js`: check on launch + every ~4 hours (the app runs for weeks),
  download silently, `autoInstallOnAppQuit` — the update applies on next
  relaunch, no prompts. An ambient widget should never nag.
- electron-builder `publish` config generates and uploads the update metadata
  (`latest-mac.yml`, `latest.yml`) with the artifacts; macOS auto-update
  requires publishing the `zip` target alongside the `dmg` (already in 5a).
- Requires macOS signing + notarization (Phase 0.4 — settled).
- Steady-state: shell releases are rare (Electron security bumps, new
  `window.eona` bridge methods) and now reach the whole installed base
  automatically.

### 5d. Hosting on eona.earth

- Publish installers as **GitHub Releases** on `owen-thomas/eona-earth` (keeps
  100+ MB binaries out of the Vercel deploy).
- Add a download link/section to the web build pointing at
  `github.com/owen-thomas/eona-earth/releases/latest/download/Eona.dmg` (stable
  "latest" URLs), or a `/download` redirect in `vercel.json`.
- Note: `vercel.json` currently rewrites `/(.*) → /index.html`; a redirect entry
  must be added *before* the catch-all rewrite.

---

## Phase 6 — Verification checklist

- [ ] `./build.sh web && ./build.sh pi` outputs are **byte-identical to before** the
      `@if DESKTOP` blocks were added (the whole point of the directive approach) —
      diff against pre-change builds.
- [ ] Globe, clouds, haze, dark-haze wipe, glow all render identically to web build.
- [ ] Corners click through to windows underneath; circle interior does not.
- [ ] Scrub, drag-to-rotate, event dots, "Return to now" all work inside r 174.
- [ ] Window drags from the margin ring; resizes from the edge ring; stays square;
      resizes around centre; respects 320 px minimum.
- [ ] WebGL canvas + haze layers re-derive cleanly at min and large sizes
      (check the 1.021 haze sizing factor still aligns at both extremes).
- [ ] Always-on-top over normal windows; stays on its own Space (macOS, per Phase 0.3).
- [ ] Quit path exists (right-click menu or ⌘Q — frameless windows have no close
      button; add a minimal context menu: "Return to now / Quit").
- [ ] Packaged app launches from a fresh macOS account (Gatekeeper pass) and a
      fresh Windows VM.
- [ ] Auto-update path: install release N−1, publish N (throwaway version bump),
      confirm silent download and apply-on-relaunch on both macOS and Windows.

---

## Deferred (explicitly out of v1)

- **Remote-content updates (preferred design for content).** Shell auto-update
  ships in v1 (Phase 5c) — which is exactly what makes deferring this safe: the
  remote-content loader can be delivered to the whole installed base later as a
  shell update. The shell is a thin
  frame; all product changes live in the HTML. Instead of shipping new binaries,
  the shell loads the desktop build from eona.earth, so a git push updates web,
  Pi (after pull), *and* desktop content — one deploy path for everything.
  - Serve `dist/desktop/app/` on the site (e.g. `eona.earth/desktop/` — add the
    route in `vercel.json` *before* the catch-all rewrite, and extend the Vercel
    `buildCommand` to build the desktop target too).
  - Load order: cached last-fetched copy (instant start, works offline) →
    background fetch with short timeout → if newer (compare the build stamp),
    cache and apply on next launch. First-run fallback: the packaged copy.
  - Performance: zero rendering impact — identical HTML/WebGL once loaded; the
    only addition is a background fetch of one ~850 KB file at launch.
  - Security hygiene: HTTPS only, keep `contextIsolation: true` /
    `nodeIntegration: false` (already the plan), and lock navigation to the
    eona.earth origin (`will-navigate` handler). The `window.eona` preload
    bridge works the same for remote URLs.
  - Net effect: binary releases only when the Electron shell itself changes —
    expected to be rare after v1.
- System tray / menu bar icon with preferences.
- Linux builds.
- Opacity/ghost mode (semi-transparent clock over work).
- Launch-at-login option.

## Suggested implementation order

1. Phase 1 (build target) → verify web/pi builds unchanged, desktop HTML opens in a browser.
2. Phase 2 (Electron shell) → clock running in a square frameless window.
3. Phase 3 (round + click-through + drag) → feels like a widget.
4. Phase 4 (resize) → feature-complete.
5. Phase 5 (packaging) → downloadable.

Each phase lands as its own commit; the repo stays deployable to web/Pi throughout.
