const { contextBridge, ipcRenderer } = require('electron');

// version: bump whenever a method is added or changed (see DESKTOP-APP-PLAN.md
// "Bridge guard convention"). Never remove or change an existing method's
// signature — add new ones instead, and gate renderer features on their
// presence (window.eona?.method) rather than on platform name.
contextBridge.exposeInMainWorld('eona', {
  version: 2,
  quit: () => ipcRenderer.send('quit'),
  // Requests the app take active/key status — needed because hiding the
  // Dock icon (accessory activation policy) stops macOS from doing this
  // automatically on window click, unlike a normal app.
  activate: () => ipcRenderer.send('activate'),
});
