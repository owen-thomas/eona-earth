# Raspberry Pi Physical Clock — Setup Notes

## Hardware

### Components
- Raspberry Pi 4 (4GB RAM)
- Waveshare round display (1080×1080)
- Micro-HDMI to HDMI cable/adapter
- 32GB microSD (Nextbase Pro)

### Wiring

| Display port | Connects to |
|---|---|
| HDMI | Pi 4 **HDMI0** (micro-HDMI closest to USB-C power port) |
| USB-C (touch) | Pi USB 3 port (blue) — USB 2 underpowers it |
| USB-C (power) | Pi USB 2 port (black) — 300mA draw, no data needed |

Single wall cable: only the Pi's own USB-C power supply runs to the wall. The display is powered from the Pi.

### Mounting
- Pi fastened to back of display via hex standoffs + tiny screws
- Busy side of the board (chips, ports) faces inward toward the display
- Flat underside faces outward

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

### Auto-update (cron)
Pulls from GitHub every 5 minutes. Only refreshes the browser if a new commit was fetched.

```
*/5 * * * * cd ~/eona && OLD=$(git rev-parse HEAD) && git fetch origin main && git reset --hard origin/main && [ "$(git rev-parse HEAD)" != "$OLD" ] && DISPLAY=:0 xdotool key F5 >> ~/eona-pull.log 2>&1
```

⚠️ The `xdotool key F5` refresh **does not work on Wayland**. The pull happens correctly but the browser won't auto-refresh on new commits. Needs a Wayland-compatible solution (e.g. `ydotool`, or a script that kills and restarts Chromium).

Dependencies: `xdotool` (installed via `sudo apt install xdotool`).

Log: `~/eona-pull.log`

### Autostart
Chromium is launched on boot via:
```
~/.config/autostart/clock.desktop
```

Current contents:
```ini
[Desktop Entry]
Type=Application
Name=Clock
Exec=chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --disable-gpu --enable-unsafe-swiftshader --password-store=basic file:///home/pi/eona/clock.html
```

### Key Chromium flags
| Flag | Reason |
|------|--------|
| `--disable-gpu` | Prevents GPU process crash (exit_code=512) on VideoCore VI |
| `--enable-unsafe-swiftshader` | Forces WebGL to use CPU-based SwiftShader renderer |
| `--password-store=basic` | Suppresses keyring password prompt on launch |
| `--kiosk` | Full-screen, no browser UI |

### GPU memory
Added `gpu_mem=256` to `/boot/firmware/config.txt`.

---

## Connecting via SSH (from Mac)

```bash
ssh pi@eona.local
```

### Manually relaunching Chromium from SSH
The Pi runs Wayland, so `DISPLAY=:0` does **not** work from SSH. To kill and relaunch:

```bash
pkill chromium
# Then reboot, or trigger autostart another way
sudo reboot
```

The simplest way to apply changes is to edit the autostart file and reboot.

---

## Known Issues

### GPU process crashes (resolved)
The Pi 4's VideoCore VI GPU crashes under the Three.js WebGL shader:
```
GPU process exited unexpectedly: exit_code=512
```
**Fix:** `--disable-gpu --enable-unsafe-swiftshader` in the Chromium launch flags. This forces software (CPU) rendering via SwiftShader. Stable but slower than hardware rendering.

### Performance
SwiftShader (CPU rendering) is slower than GPU. The render loop is capped at 15fps.

**Shader optimisations applied to `clock.html` (not `eona.html`):**
- Three.js and fonts bundled locally (no CDN dependency)
- `antialias: false`, `pixelRatio: 1`
- Sphere geometry reduced 64×64 → 32×32
- Globe renders at half resolution, CSS-scaled up (4× fewer pixels)
- fbm noise octaves reduced 4 → 2
- Dual-render disabled: JS snaps to dominant state, shader skips B-side pass
- `ridgedFbm` octaves reduced 5 → 4

Result: performance improved from ~2fps to usable, but still laggy under SwiftShader.

**Next steps to try:**
- Remove `--disable-gpu` to attempt hardware rendering with simplified shader
- Fit a heatsink — Pi runs very hot under SwiftShader load and likely thermal throttles
- Upgrade to Pi 5 (VideoCore VII handles the shader without crashing)

### Cron F5 refresh broken on Wayland
`xdotool key F5` requires X11. On Wayland it silently does nothing. The git pull works fine but Chromium won't reload after an auto-update. Workaround: manually reboot or SSH in and `sudo reboot`.

### SSH password locked out
After rebooting the Pi, SSH password authentication may stop working (likely caps lock or keyboard layout). Fix: plug in a USB keyboard, press `Ctrl+Alt+F2` for text console, run `passwd pi`.

### Chromium package name
On this Pi OS version, the package and command are `chromium`, not `chromium-browser`.

### Old ~/clock.html
There is a stale copy of `clock.html` at `/home/pi/clock.html` (dated May 13). This is no longer used — the autostart now loads from `~/eona/clock.html`. The old file can be deleted.

---

## Workflow

1. Edit `clock.html` on Mac
2. Push to `main` on GitHub
3. Pi pulls automatically within 5 minutes
4. ⚠️ Browser does **not** auto-refresh (Wayland/xdotool issue) — reboot to apply updates
