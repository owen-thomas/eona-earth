# Raspberry Pi Physical Clock — Setup Notes

## Hardware

### Components
- **Raspberry Pi 5 (2GB RAM)** ← upgraded from Pi 4 (4GB); VideoCore VII GPU handles WebGL shader without crashing
- Waveshare round display (1080×1080, 8" diameter)
- Micro-HDMI to HDMI cable/adapter
- Waveshare M.2 Adapter with Active Cooler (PCIe via FFC connector; temperature-controlled blower fan)
- Kingston 256GB 2230 NVMe SSD (boots via M.2 adapter — replaces SD card)
- Raspberry Pi 27W USB-C Power Supply (Pi 5 requires 27W; Pi 4's 15W supply retired)

### Wiring

| Display port | Connects to |
|---|---|
| HDMI | Pi 5 **HDMI0** (micro-HDMI closest to USB-C power port) |
| USB-C (touch) | Pi USB 3 port (blue) — USB 2 underpowers it |
| USB-C (power) | Pi USB 2 port (black) — 300mA draw, no data needed |

Single wall cable: only the Pi's own USB-C power supply runs to the wall. The display is powered from the Pi.

### Mounting
- Pi fastened to back of display via hex standoffs + tiny screws
- Busy side of the board (chips, ports) faces inward toward the display
- Flat underside faces outward
- Current assembly depth: ~41mm (may increase slightly with M.2 adapter + cooler)
- ~20–25mm standoff clearance between display and Pi — sufficient for M.2 + active cooler stack (SSD mounts flat alongside heatsink, does not add height)

### Enclosure (TBD)
Display outer diameter: 203mm (8"). Currently unmounted on wall — enclosure design pending.
- Target aesthetic: black or brushed metal, space vibes
- Needs ~45–50mm internal depth, ventilation for active cooler fan
- Options under consideration: SLS 3D print (matte black nylon), laser-cut aluminium rings, local metal fabricator
- Note: ventilation pattern on back plate can be a design feature (perforated circle motif)

### Audio (deferred)
Display board has an NS4263 mono 3W amp with a 4-pin PH1.25 JST "Speaker" connector and a 3.5mm audio input jack. Audio signal likely comes from HDMI.

- Speaker needed: 8Ω 2W, 4-pin PH1.25 connector — Waveshare 2030 Cavity Speaker is the correct part
- Supply currently low; revisit when available (eBay ~£6, Amazon ~£8)
- Confirm HDMI audio routing works before purchasing: `aplay -l` should list an HDMI audio device

---

## Software

### OS
- Raspberry Pi OS (Debian-based, Trixie)
- Display server: **Wayland** (not X11) — important for launch commands
- Hostname: `eona` (`eona.local` on the network)
- User: `pi`

### Repo
- Public GitHub repo: `https://github.com/owen-thomas/eona-earth.git`
- Cloned to `~/eona` on the Pi
- `clock.html` is served directly from `~/eona/clock.html`

### Offline assets
Three.js and fonts are bundled locally so the clock works without internet:
- `lib/three.r128.min.js` — Three.js r128
- `fonts/space-mono-400.woff2`, `fonts/space-mono-700.woff2`, `fonts/fraunces-400.woff2`
- Logo is inlined as a base64 data URI in `clock.html`

### Auto-update (removed)
The cron-based auto-pull has been removed. Updates are applied manually via SSH:
```bash
cd ~/eona && git pull && sudo reboot
```
The cron approach was also broken on Wayland — `xdotool key F5` does nothing, so Chromium never refreshed after a pull.

### Autostart
Chromium is launched on boot via:
```
~/.config/autostart/clock.desktop
```

Current contents (Pi 5 — no SwiftShader flags needed):
```ini
[Desktop Entry]
Type=Application
Name=Clock
Exec=chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --password-store=basic file:///home/pi/eona/clock.html
```

### Key Chromium flags
| Flag | Reason |
|------|--------|
| `--password-store=basic` | Suppresses keyring password prompt on launch |
| `--kiosk` | Full-screen, no browser UI |

`--disable-gpu` and `--enable-unsafe-swiftshader` are **not needed on Pi 5** — VideoCore VII handles the WebGL shader with hardware rendering.

### Long-term stability
- **Memory**: The clock app loads once and runs a fixed animation loop with no dynamic content. Memory should reach a stable plateau quickly. No nightly reboot needed — monitor over first week and only add a cron reboot if instability is observed.
- **Storage**: NVMe SSD replaces SD card, removing the main long-term wear concern for always-on operation.
- **Cooling**: M.2 active cooler handles sustained WebGL rendering load. Pi 5 runs hotter than Pi 4 — cooler is essential for 24/7 operation.

---

## Connecting via SSH (from Mac)

```bash
ssh pi@eona.local
```

### Manually relaunching Chromium from SSH
The Pi runs Wayland, so `DISPLAY=:0` does **not** work from SSH. To apply updates:

```bash
cd ~/eona && git pull && sudo reboot
```

---

## Known Issues

### ~~White square / GPU crash~~ (resolved)
On Pi 4, VideoCore VI crashed the GPU process with the Three.js WebGL shader (`exit_code=512`). Falling back to SwiftShader (CPU rendering) also failed.

**Root cause (Pi 4):** VideoCore VI is not capable of compiling/running this shader under Chromium. Dead end — no fix possible.

**Root cause (Pi 5):** Same `exit_code=512` GPU crash initially. After binary-search isolation, the culprit was `computeCloudMask()`. V3D inlines the full function body, exceeding its shader instruction limit — even with `CLOUDS_ENABLED = false` and an early `return 0.0`, because the early return does not prevent compilation of the inlined body.

**Resolution:** Two changes combined:
1. `computeCloudMask()` is wrapped in a JS template literal conditional (`${CLOUDS_ENABLED ? \`...\` : ''}`). When `CLOUDS_ENABLED = false`, the function is absent from the GLSL string entirely — V3D never sees it.
2. With `CLOUDS_ENABLED = true`: the multi-branch cloud function (`warped` + `warped_layers`) still exceeded V3D's limit. Collapsed to a single **warped_wisps** branch. `ridgedFbm2` was initially 2-octave to stay within budget; subsequently upgraded to 5-octave after confirming ~20 calls is within V3D's limit on Pi 5.

### ~~Performance / 15fps cap~~ (resolved)
The 15fps cap (`TARGET_FPS` / `FRAME_BUDGET` throttle) was set for SwiftShader CPU rendering on Pi 4. Removed — Pi 5 hardware rendering runs at full rAF frame rate.

### ~~Future states broken~~ (resolved)
The Pi simplification pass had removed the `isFuture` dispatch in `updateEarth()`, causing the future half of the clock to show Modern Earth throughout. Fixed — future SDF atlas restored, dispatch reinstated, `FUTURE_STATES` `useLandSea` values corrected.

### SSH password locked out
After rebooting, SSH password authentication may stop working (likely caps lock or keyboard layout). Fix: plug in a USB keyboard, press `Ctrl+Alt+F2` for text console, run `passwd pi`.

### Chromium package name
On this Pi OS version, the package and command are `chromium`, not `chromium-browser`.

---

## Pi 5 Installation Status

- [x] Mount Pi 5 to display via existing standoffs
- [x] Connect M.2 adapter FFC cable to Pi 5 PCIe connector
- [x] Connect active cooler fan header + 5V/GND GPIO power
- [x] Boot from SD card — clock loads, globe stable, clouds working
- [ ] Seat Kingston 2230 NVMe in M.2 slot (SSD arriving soon)
- [ ] Flash Pi OS to NVMe and set boot order (`raspi-config` → Advanced → Boot Order)
- [ ] Check `aplay -l` for HDMI audio device (for future speaker work)

## `clock.html` vs `eona.html` — Pi Shader Differences

`clock.html` is the Pi-targeted version. Key differences from `eona.html`:

| Feature | `eona.html` | `clock.html` |
|---------|-------------|--------------|
| `fbm()` | 4 octaves | **2 octaves** — used for cloud warp vectors only |
| `fbmSurf()` | (same as `fbm`) | **4 octaves** — surface rendering only |
| `fbm2()` | 2 octaves | **2 octaves** — cloud body sampling (matches eona.html) |
| `ridgedFbm2()` | n/a | **5 octaves** — matches eona.html `ridgedFbm`; ~20 total calls at confirmed V3D limit |
| Cloud function | Full `computeCloudMask()` with 4 branches | Single warped_wisps branch; all states use warped_wisps regardless of `cloudApproach` field |
| `ridgedFbm` | 5-octave loop | `ridgedFbm2` — **5 octaves**, multiplicative accumulation; matches eona.html quality |
| Cloud warp frequency | `cp * 1.8` | `cp * 1.2` — lower frequency for broader wave structure |
| `cloudShape` per state | Per-state values | Pre-Cryogenian states bumped (0.00 → 0.15–0.75); warped_wisps looks poor at 0.00 |
| `CLOUDS_ENABLED` | `true` | `true` (conditional: function absent from GLSL when `false`) |
| `renderSurface()` | Full uber-shader (screenprint / watercolor / topographic branches) | Screenprint only — `surfaceApproach` field is ignored |
| State blending | Full dual-render cross-fade | CPU-interpolated: colours, cloudDensity, cloudShape, thresholds, polarIce all lerp smoothly. `seed`, `useLandSea`, `cloudApproach` snap at t=0.5. No dual-render (would double V3D instruction count). |

### V3D instruction budget
V3D's limit sits somewhere between ~20 and ~24 `noise3d`-equivalent calls in the compiled shader. Budget history:

| Config | Calls | Result |
|--------|-------|--------|
| Multi-branch cloud (`warped` + `warped_layers`) | ~24 | crash |
| Single warped_wisps + 2-octave `ridgedFbm2` + 2-octave warp | ~14 | stable (original) |
| Single warped_wisps + 2-octave `ridgedFbm2` + 4-octave warp | ~20 | stable — but no visible benefit, reverted |
| Single warped_wisps + 3-octave `fbm2` + 2-octave warp | ~16 | stable — too wispy |
| Single warped_wisps + 4-octave `fbm2` + 2-octave warp | ~18 | stable — edges soft |
| Single warped_wisps + 5-octave `ridgedFbm2` + 2-octave warp | ~20 | **current** ✅ |

### Surface rendering note
`renderSurface()` in `clock.html` has no `topographic` branch — the `surfaceApproach` field on STATES is accepted but ignored. Red Giant and Earth destroyed use `screenprint` with standard 0.46/0.56 thresholds. If topographic is needed for these states, the branch must be added to the Pi shader (adds instruction cost, but `renderSurface()` confirmed stable on V3D in isolation).

---

## Workflow

1. Edit `clock.html` on Mac
2. Push to `main` on GitHub
3. SSH into Pi: `cd ~/eona && git pull && sudo reboot`
