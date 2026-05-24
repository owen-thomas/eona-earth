# Raspberry Pi Physical Clock — Setup Notes

## Hardware

### Components
- Raspberry Pi 4
- Waveshare round display
- Micro-HDMI to HDMI cable/adapter

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
- Raspberry Pi OS (Debian-based)
- Hostname: `eona` (`eona.local` on the network)
- User: `pi`

### Repo
- Public GitHub repo: `https://github.com/owen-thomas/eona-earth.git`
- Cloned to `~/eona` on the Pi

### Auto-update (cron)
Pulls from GitHub every 5 minutes. Only refreshes the browser if a new commit was fetched.

```
*/5 * * * * cd ~/eona && OLD=$(git rev-parse HEAD) && git fetch origin main && git reset --hard origin/main && [ "$(git rev-parse HEAD)" != "$OLD" ] && DISPLAY=:0 xdotool key F5 >> ~/eona-pull.log 2>&1
```

Dependencies: `xdotool` (installed via `sudo apt install xdotool`).

Log: `~/eona-pull.log`

### Launching the clock
```bash
DISPLAY=:0 chromium --kiosk file:///home/pi/eona/clock.html
```

### GPU memory
Added `gpu_mem=256` to `/boot/firmware/config.txt` to give the GPU more headroom for WebGL.

---

## Known Issues

### GPU process crashes
The Pi 4's GPU struggles with the Three.js WebGL shader. Errors:
```
GPU process exited unexpectedly: exit_code=512
```

**Attempted fixes:**
- Increased GPU memory to 256MB — not yet confirmed effective
- `--enable-unsafe-swiftshader` flag (software rendering fallback) — not yet tested

**Not yet tried:**
- Capping `requestAnimationFrame` to 30fps to reduce GPU load
- Simplifying the shader for Pi (fewer noise octaves, disable dual-render)
- Heatsink on the CPU/GPU chip (Pi runs hot under WebGL load)

### SSH password locked out
After rebooting the Pi, SSH password authentication stopped working. The password was not changed — likely a caps lock or keyboard layout issue. Needs to be resolved by logging in locally (USB keyboard, `Ctrl+Alt+F2` for text console) and running `passwd pi`.

### Chromium package name
On this Pi OS version, the package and command are `chromium`, not `chromium-browser`.

---

## Workflow

1. Edit `clock.html` on Mac
2. Push to `main` on GitHub
3. Pi pulls automatically within 5 minutes and refreshes the browser
