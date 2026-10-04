// Authenticated playback checks for existing private recordings. No auth overrides.
const fs = require('node:fs');
const { chromium } = require('../frontend/node_modules/playwright');
(async () => {
  const auth = JSON.parse(fs.readFileSync(process.argv[2] || 0, 'utf8').replace(/^\uFEFF/, ''));
  const headers = { Authorization: `Basic ${Buffer.from(`${auth.login}:${auth.password}`).toString('base64')}` };
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const context = await browser.newContext();
  const base = 'http://localhost:3000/api/archive';
  const results = [];
  try {
    const response = await context.request.get(`${base}/staff/documents?limit=200`, { headers });
    if (!response.ok()) throw Error('Staff authentication failed');
    const rows = (await response.json()).filter(r => ['audio/mpeg', 'video/mp4'].includes(r.mime_type));
    if (rows.length !== 8) throw Error('Expected eight existing recordings');
    for (const r of rows) {
      const path = `${base}/staff/documents/${r.id}`;
      const grant = await context.request.post(`${path}/playback-session`, { headers });
      if (!grant.ok()) throw Error('Playback grant failed');
      const page = await context.newPage();
      try {
        const denied = await context.request.get(`${base}/documents/${r.id}/playback`);
        if (denied.status() !== 404) throw Error('Restricted recording became public');
        const range = await context.request.get(`${path}/playback`, { headers: { Range: 'bytes=0-31' } });
        if (range.status() !== 206 || (await range.body()).length !== 32) throw Error('Byte range failed');
        await page.goto('http://localhost:3000/staff');
        const result = await page.evaluate(async ({ id, mime }) => {
          const media = document.createElement(mime.startsWith('video/') ? 'video' : 'audio');
          media.muted = true; media.preload = 'metadata';
          media.src = `/api/archive/staff/documents/${id}/playback`;
          document.querySelector('main').appendChild(media);
          try {
            await new Promise((resolve, reject) => {
              const timer = setTimeout(() => reject(Error('metadata timeout')), 30000);
              media.onloadedmetadata = () => { clearTimeout(timer); resolve(); };
              media.onerror = () => { clearTimeout(timer); reject(Error('decode failed')); };
            });
            await media.play();
            await new Promise((resolve, reject) => {
              const began = performance.now();
              const timer = setInterval(() => {
                if (media.currentTime > 0.3) { clearInterval(timer); resolve(); }
                else if (performance.now() - began > 15000) { clearInterval(timer); reject(Error('playback timeout')); }
              }, 100);
            });
            return { passed: true, duration: media.duration, advanced: media.currentTime > 0.3, videoWidth: media.videoWidth || null };
          } finally { media.pause(); media.remove(); }
        }, { id: r.id, mime: r.mime_type });
        results.push({ id: r.id, filename: r.original_filename, public_status: denied.status(), range_status: range.status(), ...result });
      } finally {
        await page.close();
        const stopped = await context.request.post(`${path}/playback-stop`, { headers });
        const revoked = await context.request.get(`${path}/playback`);
        if (!stopped.ok() || revoked.status() !== 401) throw Error('Revocation failed');
      }
    }
    fs.writeFileSync('outputs/deadline-media.json', JSON.stringify(results, null, 2));
    console.log(`${results.length} passed, 0 failed: authenticated private playback, ranges, public exclusion and revocation`);
  } finally { await context.close(); await browser.close(); }
})().catch(() => { console.error('Authenticated media check failed; credentials withheld'); process.exitCode = 1; });
