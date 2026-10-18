import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(fileURLToPath(new URL('.', import.meta.url)));
const port = Number(process.env.PORT || 5173);
const apiBase = process.env.FREEDOM_API_BASE || 'http://127.0.0.1:8000';
const apiUrl = new URL(apiBase, 'http://localhost');
if (!['http:', 'https:'].includes(apiUrl.protocol) || apiUrl.username || apiUrl.password || apiUrl.search || apiUrl.hash) throw new Error('FREEDOM_API_BASE không hợp lệ');
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json' };
http.createServer(async (req, res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    if (pathname === '/runtime-config.js') {
      res.writeHead(200, { 'Content-Type': 'text/javascript; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
      res.end('globalThis.FREEDOM_CONFIG = Object.freeze(' + JSON.stringify({ apiBase }).replace(/</g, '\\u003c') + ');');
      return;
    }
    if (!['/', '/index.html', '/app.js', '/api.js', '/access.js', '/products.js', '/categories.js', '/category-banners.js', '/storefront-content.js', '/gallery.js', '/data.js', '/reference.css', '/styles.css'].includes(pathname) && !/^\/assets\/[a-zA-Z0-9._-]+\.(jpg|png|svg)$/.test(pathname)) { res.writeHead(404).end(); return; }
    const file = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
    if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
    const body = await readFile(file);
    res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream', 'X-Content-Type-Options': 'nosniff' });
    res.end(body);
  } catch { res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }).end('Không tìm thấy trang'); }
}).listen(port, '127.0.0.1', () => console.log(`Freedom: http://localhost:${port}`));
