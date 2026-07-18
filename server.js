const http = require('http');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const PORT = 3000;
const ROOT = __dirname;
const WEB_DIR = path.join(ROOT, 'dist/web');

const MIME = {
  '.html': 'text/html',
  '.js':   'application/javascript',
  '.css':  'text/css',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml',
  '.json': 'application/json',
  '.woff2':'font/woff2',
};

const SOURCE = path.join(ROOT, 'eona.html');
const WEB_INDEX = path.join(WEB_DIR, 'index.html');

function buildWeb() {
  execSync('./build.sh web', { cwd: ROOT, stdio: 'pipe', encoding: 'utf8' });
}

// Rebuilds dist/web/index.html iff eona.html has changed since it was last
// built — the edit → refresh loop, no watcher process.
function ensureWebBuilt() {
  const srcMtime = fs.statSync(SOURCE).mtimeMs;
  let distMtime = 0;
  try {
    distMtime = fs.statSync(WEB_INDEX).mtimeMs;
  } catch {
    distMtime = 0; // no dist yet — treat as stale
  }
  if (srcMtime > distMtime) {
    buildWeb();
  }
}

// Build the web variant before starting — a server that never had a valid
// dist/ shouldn't pretend to serve one.
console.log('Building web variant…');
try {
  buildWeb();
} catch (e) {
  console.error('build.sh failed — fix the error and restart server');
  console.error((e.stderr || e.stdout || e.message || '').toString());
  process.exit(1);
}

// Serve from dist/web/, falling back to repo root for shared assets
// (images/, fonts/, lib/) that aren't copied into the build output.
http.createServer((req, res) => {
  let urlPath = req.url.split('?')[0];
  if (urlPath === '/') urlPath = '/index.html';

  // Only index.html triggers a staleness check — asset requests (images,
  // fonts, lib) are served live from the repo root regardless via the
  // fallback below, so they don't need dist/ to be current.
  if (urlPath === '/index.html') {
    try {
      ensureWebBuilt();
    } catch (e) {
      const output = ((e.stderr || '') + (e.stdout || '') || (e.message || '')).toString();
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('build.sh failed:\n\n' + output);
      return;
    }
  }

  // Try dist/web/ first, then repo root
  const candidates = [
    path.join(WEB_DIR, urlPath),
    path.join(ROOT, urlPath),
  ];

  const tryNext = (i) => {
    if (i >= candidates.length) {
      res.writeHead(404);
      res.end('Not found');
      return;
    }
    fs.readFile(candidates[i], (err, data) => {
      if (err) { tryNext(i + 1); return; }
      const ext = path.extname(candidates[i]);
      res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
      res.end(data);
    });
  };

  tryNext(0);
}).listen(PORT, () => {
  console.log(`Serving on http://localhost:${PORT}`);
});
