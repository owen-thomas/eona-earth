const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');

const APP_HTML = path.join(__dirname, '..', 'dist', 'desktop', 'app', 'index.html');

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  let win = null;

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

    // Documentation of intent only — resizable:false disables native resize
    // entirely, so this doesn't constrain anything yet. Phase 4's custom
    // resize (setBounds) must enforce both squareness and the 320px floor
    // itself; don't assume this line is doing that work.
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

  app.whenReady().then(() => {
    if (process.platform === 'darwin') app.dock.hide(); // before window creation — hiding after causes focus-loss/icon-flash quirks
    createWindow();
  });

  app.on('window-all-closed', () => app.quit()); // no dock-lurking, quit fully even on macOS
}
