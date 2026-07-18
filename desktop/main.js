const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');
const fs = require('fs');

const APP_HTML = path.join(__dirname, '..', 'dist', 'desktop', 'app', 'index.html');

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  let win = null;
  let dragInterval = null;
  let resizeInterval = null;

  // Manual drag, not -webkit-app-region: drag — that property hit-tests
  // against layout bounding boxes, not painted/masked shape, so it can't
  // produce a genuinely annular drag region (a masked ring drags the whole
  // square; a nested no-drag square only carves out the ring near the
  // compass points, missing the diagonals entirely). Polling the OS cursor
  // position directly (rather than streaming renderer pointermove deltas)
  // avoids a feedback loop between window position and client-relative
  // coordinates, since screen coordinates don't shift as the window moves
  // under a stationary cursor. Same architecture for resize below.
  function stopDrag() {
    if (dragInterval) {
      clearInterval(dragInterval);
      dragInterval = null;
    }
  }

  function stopResize() {
    if (resizeInterval) {
      clearInterval(resizeInterval);
      resizeInterval = null;
    }
  }

  // Accessory activation policy (app.dock.hide()) means focusing the window
  // alone doesn't make the app active — app.focus({steal:true}) is required
  // too, same as the 'activate' IPC handler below. Shared here so neither
  // caller can drift out of sync with the other.
  function activateWindow() {
    app.focus({ steal: true });
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  }

  // With no Dock icon, relaunching the app is how a user "finds" it again —
  // focus the existing window instead of leaving them wondering nothing happened.
  app.on('second-instance', () => activateWindow());

  function createWindow() {
    if (!fs.existsSync(APP_HTML)) {
      throw new Error(
        `${APP_HTML} not found — run "./build.sh desktop" from the repo root first.`
      );
    }

    win = new BrowserWindow({
      width: 600,
      height: 600,
      minWidth: 320,
      minHeight: 320,
      frame: false,
      transparent: true,
      backgroundColor: '#00000000',
      hasShadow: false, // macOS square shadow would betray the round bounding box
      resizable: false, // native resize off — Phase 4 owns resize via setBounds
      fullscreenable: false,
      skipTaskbar: true, // widget-like: no Dock/taskbar icon (Phase 2 decision)
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });

    win.setAlwaysOnTop(true, 'floating'); // above normal windows, below panels (macOS)

    // Safety net: if pointerup/pointercancel is ever missed (e.g. focus
    // lands elsewhere mid-gesture), stop both polling loops anyway — leaving
    // either running would make the window keep following/resizing forever.
    win.on('blur', () => {
      stopDrag();
      stopResize();
    });

    // Documentation of intent only — resizable:false disables native resize
    // entirely, so this doesn't constrain anything by itself. Squareness and
    // the 320px floor are enforced explicitly in the begin-resize handler
    // below (setBounds always computes a square, size clamped to >= 320);
    // confirmed by direct test that setBounds bypasses both resizable:false
    // and this aspect-ratio lock on macOS, so neither fights the resize math.
    win.setAspectRatio(1);

    // Not a fallback — the only viable path. Cmd+Q is normally dispatched via
    // the frontmost app's menu bar, but an accessory-policy app (Dock icon
    // hidden) never owns the menu bar, so the default app-menu key
    // equivalent can never reach this window regardless of which window has
    // keyboard focus. Confirmed empirically: with the Dock icon hidden, the
    // menu bar keeps showing the previously-active app even after this
    // window becomes key, so Cmd+Q would quit that app instead.
    win.webContents.on('before-input-event', (event, input) => {
      if (
        input.type === 'keyDown' &&
        input.meta &&
        !input.alt &&
        !input.shift &&
        input.key.toLowerCase() === 'q'
      ) {
        app.quit();
      }
    });

    if (!app.isPackaged && process.env.EONA_DEVTOOLS) {
      win.webContents.openDevTools({ mode: 'detach' }); // attached devtools resize the window, fights transparency
    }

    win.loadFile(APP_HTML);
  }

  ipcMain.on('quit', () => app.quit());
  ipcMain.on('activate', () => activateWindow());

  ipcMain.on('ignore-mouse', (event, ignore) => {
    // forward: true keeps mousemove flowing to the renderer while ignoring
    // so it can detect re-entry — without it, ignoring never turns itself
    // back off. (Also: this stops working while devtools are open, a known
    // Electron limitation — test click-through with devtools closed.)
    if (win) win.setIgnoreMouseEvents(ignore, { forward: true });
  });

  ipcMain.on('begin-drag', () => {
    // Mutual exclusion is enforced here, not just by the renderer's
    // half-open ring geometry — IPC is the untrusted edge of this design,
    // and a stray message from a stale gesture shouldn't start a second
    // loop fighting the first over win.setPosition/setBounds.
    if (!win || dragInterval || resizeInterval) return;
    const startCursor = screen.getCursorScreenPoint();
    const startBounds = win.getBounds();
    let lastX = startBounds.x;
    let lastY = startBounds.y;
    dragInterval = setInterval(() => {
      const cur = screen.getCursorScreenPoint();
      const x = Math.round(startBounds.x + (cur.x - startCursor.x));
      const y = Math.round(startBounds.y + (cur.y - startCursor.y));
      if (x === lastX && y === lastY) return; // skip redundant setPosition on a stationary cursor
      lastX = x;
      lastY = y;
      win.setPosition(x, y);
    }, 16);
  });
  ipcMain.on('end-drag', () => stopDrag());

  ipcMain.on('begin-resize', (event, grabPoint) => {
    if (!win || dragInterval || resizeInterval) return;
    const startBounds = win.getBounds();
    const centerX = startBounds.x + startBounds.width / 2;
    const centerY = startBounds.y + startBounds.height / 2;
    const radius = startBounds.width / 2;

    // Anchor = the point diametrically opposite the grab, at the original
    // radius — pinned in screen space for the rest of the gesture, so the
    // window extends from wherever the ring was grabbed instead of growing
    // symmetrically from centre. (Centre-anchored resize was the first
    // attempt: it made it hard to grow the window unless it was already
    // centred on the display, and clamping to the work area to keep it
    // on-screen caused a visible jump the instant a resize began near an
    // edge — deliberately uncapped now, so growing off-screen is allowed.)
    let dx = grabPoint.x - centerX;
    let dy = grabPoint.y - centerY;
    let len = Math.hypot(dx, dy);
    if (len === 0) { dx = 1; dy = 0; len = 1; } // degenerate: shouldn't happen from a ring press, but keep this well-defined
    const anchor = { x: centerX - (dx / len) * radius, y: centerY - (dy / len) * radius };

    // Absorb the click offset into the first tick's delta rather than
    // treating the grab point as if it were exactly on the rim — the same
    // fix this project already made for the scrub handle (see CLAUDE.md:
    // seed lastAngle from the handle's true angle, not the pointer's click
    // position). The resize band spans r196-200, so the grab point sits up
    // to 2% inside the true radius; without this, |grab - anchor| is
    // already a few px short of the original size, so a motionless press
    // reads as "shrink" on the very first tick and the grabbed edge tracks
    // slightly inside the cursor for the whole gesture.
    const initialDist = Math.hypot(grabPoint.x - anchor.x, grabPoint.y - anchor.y);
    const sizeOffset = startBounds.width - initialDist;

    let lastSize = startBounds.width;
    resizeInterval = setInterval(() => {
      const cur = screen.getCursorScreenPoint();
      const ax = cur.x - anchor.x;
      const ay = cur.y - anchor.y;
      const dist = Math.hypot(ax, ay);
      const size = Math.max(320, Math.round(dist + sizeOffset));
      if (size === lastSize) return; // skip redundant setBounds (real resize + Three.js framebuffer realloc) on a stationary cursor
      lastSize = size;
      // Recompute centre from the anchor rather than the raw cursor position,
      // so the anchor stays exactly pinned even where the 320 floor clamps
      // size below the raw anchor-to-cursor distance.
      const ux = dist > 0 ? ax / dist : 1;
      const uy = dist > 0 ? ay / dist : 0;
      const newCenterX = anchor.x + ux * size / 2;
      const newCenterY = anchor.y + uy * size / 2;
      win.setBounds({
        x: Math.round(newCenterX - size / 2),
        y: Math.round(newCenterY - size / 2),
        width: size,
        height: size,
      });
    }, 16);
  });
  ipcMain.on('end-resize', () => stopResize());

  app.whenReady().then(() => {
    if (process.platform === 'darwin') app.dock.hide(); // before window creation — hiding after causes focus-loss/icon-flash quirks
    createWindow();
  });

  app.on('window-all-closed', () => app.quit()); // no dock-lurking, quit fully even on macOS
}
