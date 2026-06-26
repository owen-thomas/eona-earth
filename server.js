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

// Build the web variant before starting
console.log('Building web variant…');
try {
  execSync('./build.sh web', { cwd: ROOT, stdio: 'inherit' });
} catch (e) {
  console.error('build.sh failed — fix the error and restart server');
  process.exit(1);
}

// Serve from dist/web/, falling back to repo root for shared assets
// (images/, fonts/, lib/) that aren't copied into the build output.
http.createServer((req, res) => {
  let urlPath = req.url.split('?')[0];
  if (urlPath === '/') urlPath = '/index.html';

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
