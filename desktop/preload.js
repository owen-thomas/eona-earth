const { contextBridge, ipcRenderer } = require('electron');

// version: bump whenever a method is added or changed (see DESKTOP-APP-PLAN.md
// "Bridge guard convention"). Never remove or change an existing method's
// signature — add new ones instead, and gate renderer features on their
// presence (window.eona?.method) rather than on platform name.
contextBridge.exposeInMainWorld('eona', {
  version: 4,
  quit: () => ipcRenderer.send('quit'),
  // Requests the app take active/key status — needed because hiding the
  // Dock icon (accessory activation policy) stops macOS from doing this
  // automatically on window click, unlike a normal app.
  activate: () => ipcRenderer.send('activate'),
  // ignore: true makes the window click-through (for the transparent
  // corners); main pairs this with { forward: true } so mousemove keeps
  // flowing and re-entry can still be detected.
  setIgnoreMouse: (ignore) => ipcRenderer.send('ignore-mouse', ignore),
  // Manual window drag (not -webkit-app-region: drag — that hit-tests
  // against layout bounding boxes, not painted/masked shape, so it can't
  // produce a genuinely annular drag region). Renderer does the geometric
  // hit-test and calls beginDrag() on pointerdown inside the ring, endDrag()
  // on pointerup/pointercancel; main moves the window via cursor polling.
  beginDrag: () => ipcRenderer.send('begin-drag'),
  endDrag: () => ipcRenderer.send('end-drag'),
  // Custom resize (native resize is off — see main.js BrowserWindow config).
  // Same cursor-polling architecture as drag. Passes the initial grab point
  // in screen coordinates so main can pin the opposite edge of the ring in
  // place and resize from wherever it was grabbed, rather than symmetrically
  // from centre (which made growing the window hard unless it happened to
  // already be centred on the display).
  beginResize: (screenX, screenY) => ipcRenderer.send('begin-resize', { x: screenX, y: screenY }),
  endResize: () => ipcRenderer.send('end-resize'),
});
