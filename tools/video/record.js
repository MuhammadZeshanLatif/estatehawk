#!/usr/bin/env node
// EstateHawk demo video recorder (Playwright). Scenes live in scenes.js.
//
//   node tools/video/record.js [--base URL] [--scenes a,b,c] [--size 1440x810] [--video 1920x1080] [--mobile]
//                              [--split] [--file shorts/x.js] [--out DIR] [--no-captions] [--list]
//
// Login: EH_EMAIL and EH_PASSWORD (run.sh sets these for the local demo copy).
// Output: <out>/estatehawk-demo.webm (+ .mp4 when ffmpeg is installed), or one file per scene with --split.
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { chromium, devices } = require('playwright');


const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i < 0 ? d : (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true); };
const FILE = String(opt('file', 'scenes.js'));
const SCENES = require(path.resolve(__dirname, FILE));
const BASE = String(opt('base', process.env.EH_BASE || 'http://127.0.0.1:8199')).replace(/\/$/, '');
const OUT = path.resolve(String(opt('out', path.join(__dirname, 'out'))));
const MOBILE = !!opt('mobile', false);
const SPLIT = !!opt('split', false);
const CAPTIONS = !opt('no-captions', false);
const [W, H] = String(opt('size', MOBILE ? '390x844' : '1440x810')).split('x').map(Number);  // browser size
const [VW, VH] = String(opt('video', MOBILE ? '780x1688' : '1920x1080')).split('x').map(Number);  // video file size (scaled up, text stays readable)
const pick = opt('scenes', '');
const scenes = pick ? String(pick).split(',').map((id) => SCENES.find((s) => s.id === id.trim()) || (() => { throw new Error('Unknown scene: ' + id + '. Use --list'); })()) : SCENES;

if (opt('list', false)) { SCENES.forEach((s) => console.log(s.id.padEnd(12), s.title)); process.exit(0); }

// overlay: caption bar, title cards and a visible cursor (Playwright video does not draw the mouse)
const OVERLAY = `(() => {
  if (window.__ehv) return; window.__ehv = 1;
  const css = document.createElement('style');
  css.textContent = \`
  #ehv-cap{position:fixed;left:50%;bottom:44px;transform:translateX(-50%) translateY(20px);opacity:0;z-index:2147483646;
    background:rgba(16,40,26,.92);color:#fff;font:600 26px/1.3 Inter,system-ui,sans-serif;padding:14px 28px;border-radius:14px;
    max-width:80vw;text-align:center;transition:opacity .35s,transform .35s;pointer-events:none;box-shadow:0 10px 30px rgba(0,0,0,.25)}
  #ehv-cap.on{opacity:1;transform:translateX(-50%) translateY(0)}
  #ehv-cur{position:fixed;left:0;top:0;width:30px;height:30px;margin:-3px 0 0 -5px;z-index:2147483647;pointer-events:none;
    transition:transform .12s;transform-origin:5px 3px;filter:drop-shadow(0 3px 5px rgba(0,0,0,.35))}
  #ehv-cur.down{transform:scale(.82)}
  .ehv-rip{position:fixed;width:16px;height:16px;margin:-8px 0 0 -8px;border-radius:50%;border:3px solid #16A34A;z-index:2147483646;
    pointer-events:none;animation:ehvrip .6s ease-out forwards}
  @keyframes ehvrip{from{transform:scale(.4);opacity:1}to{transform:scale(3.4);opacity:0}}
  #ehv-card{position:fixed;inset:0;z-index:2147483645;background:#F7F6F2;display:flex;flex-direction:column;align-items:center;
    justify-content:center;gap:18px;font-family:Inter,system-ui,sans-serif;color:#14251B;opacity:0;transition:opacity .5s}
  #ehv-card.on{opacity:1}#ehv-card img{width:96px}#ehv-card h1{font:700 64px Georgia,serif;margin:0;color:#16492F}
  #ehv-card p{font:500 30px Inter,system-ui,sans-serif;margin:0;color:#3E5246}\`;
  document.documentElement.appendChild(css);
  const add = (id) => { const d = document.createElement('div'); d.id = id; document.documentElement.appendChild(d); return d; };
  add('ehv-cap');
  const cu = add('ehv-cur');
  cu.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M4 2l15 9.2-6.6 1.5 3.9 7.4-2.9 1.5-3.9-7.5L4 19z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  try { const p = JSON.parse(sessionStorage.getItem('ehv_cur') || 'null'); if (p) { cu.style.left = p[0] + 'px'; cu.style.top = p[1] + 'px'; } else cu.style.left = '-100px'; } catch (e) { }
  window.__ehvCap = (t) => { const c = document.getElementById('ehv-cap'); if (!t) { c.classList.remove('on'); return; } c.textContent = t; c.classList.add('on'); };
  window.__ehvCur = (x, y, down) => { const c = document.getElementById('ehv-cur'); c.style.left = x + 'px'; c.style.top = y + 'px'; c.classList.toggle('down', !!down);
    try { sessionStorage.setItem('ehv_cur', JSON.stringify([x, y])); } catch (e) { }
    if (down) { const r = document.createElement('div'); r.className = 'ehv-rip'; r.style.left = x + 'px'; r.style.top = y + 'px'; document.documentElement.appendChild(r); setTimeout(() => r.remove(), 700); } };
  window.__ehvCard = (h, p) => { let c = document.getElementById('ehv-card'); if (!c) c = add('ehv-card');
    c.innerHTML = h ? '<img src="/site/logo-mark.svg" onerror="this.remove()"><h1></h1><p></p>' : ''; if (h) { c.querySelector('h1').textContent = h; c.querySelector('p').textContent = p || ''; }
    requestAnimationFrame(() => c.classList.toggle('on', !!h)); };
})()`;

function helpers(page, events, t0) {
  const now = () => (Date.now() - t0) / 1000;
  let cur = { x: W / 2, y: H / 2 };
  let caption = '';
  const ensure = async () => { await page.evaluate(OVERLAY).catch(() => {}); if (caption) await page.evaluate((t) => window.__ehvCap(t), caption).catch(() => {}); };
  const v = {
    page,
    wait: (ms) => page.waitForTimeout(ms),
    sceneCap: '',
    // open an app page by clicking it in the sidebar (or load it when not in the app yet)
    async nav(route) {
      const inApp = page.url().startsWith(BASE + '/app');
      if (inApp && new RegExp('#/' + route + '(/|$)').test(page.url())) return;
      if (inApp && await page.locator(`#nav a[href="#/${route}"]`).count()) {
        await v.click(`#nav a[href="#/${route}"]`, 0.5, 1.8);
        await page.waitForSelector('.page-loader', { state: 'detached', timeout: 6000 }).catch(() => {});
        await page.waitForTimeout(500);
        await ensure();
      } else await v.go('#/' + route);
    },
    async go(p) {
      caption = v.sceneCap;  // a new page keeps only the current scene's caption
      await page.evaluate(() => window.__ehvCap && window.__ehvCap('')).catch(() => {});
      const url = p.startsWith('#') ? BASE + '/app' + p : BASE + p;
      const sameApp = p.startsWith('#') && page.url().startsWith(BASE + '/app');
      if (sameApp) await page.evaluate((h) => { location.hash = h; }, p);
      else await page.goto(url, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(400);
      await page.waitForSelector('.page-loader', { state: 'detached', timeout: 6000 }).catch(() => {});
      await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
      await ensure();
      await v.cursorTo(cur.x, cur.y);
    },
    async caption(text) { caption = CAPTIONS ? text : ''; await ensure(); if (!caption) await page.evaluate(() => window.__ehvCap && window.__ehvCap('')).catch(() => {}); },
    // glide the visible cursor (CSS animation, so its speed does not depend on how busy the machine is)
    async cursorTo(x, y, ms) {
      const d = Math.hypot(x - cur.x, y - cur.y);
      ms = ms ?? Math.round(Math.min(900, 280 + d * 0.6));
      await page.evaluate(([a, b, t]) => { const c = document.getElementById('ehv-cur'); if (!c) return;
        c.style.transition = `left ${t}ms cubic-bezier(.45,0,.2,1), top ${t}ms cubic-bezier(.45,0,.2,1), transform .12s`;
        window.__ehvCur(a, b); }, [x, y, ms]).catch(() => {});
      await page.mouse.move(x, y, { steps: 4 });
      await page.waitForTimeout(ms);
      cur = { x, y };
    },
    async box(sel) {
      const el = page.locator(sel).first();
      if (!(await el.count())) { console.log('   (skipped, not found:', sel + ')'); return null; }
      await el.scrollIntoViewIfNeeded().catch(() => {});
      return el.boundingBox();
    },
    async hover(sel) { const b = await v.box(sel); if (b) await v.cursorTo(b.x + Math.min(b.width / 2, 120), b.y + b.height / 2); return !!b; },
    // wait until `sec` seconds after the recording started (keeps a single take in time with the voice)
    log: (m) => console.log('   ' + now().toFixed(1) + 's', m),
    // mark where a voice sentence starts; fit.py later stretches each marked part to its sentence length
    mark(name) { events.push({ t: now(), type: 'mark', name: String(name) }); },
    async until(sec) { const ms = sec * 1000 - (Date.now() - t0); if (ms > 0) await page.waitForTimeout(ms); else console.log('   (late by', (-ms / 1000).toFixed(1) + 's at', sec + 's)'); },
    // click with a visible cursor, ripple and camera zoom. hold: seconds the camera stays zoomed (short when the click opens a new page)
    async click(sel, hold = 1.6, zoom) {
      if (!(await v.hover(sel))) return false;
      events.push({ t: now() + 0.25, x: cur.x, y: cur.y, type: 'click', hold, ...(zoom ? { zoom } : {}) });
      await page.waitForTimeout(450);  // camera zooms in while the cursor rests on the button
      await page.evaluate(([a, b]) => window.__ehvCur(a, b, true), [cur.x, cur.y]).catch(() => {});
      await page.mouse.click(cur.x, cur.y);
      await page.waitForTimeout(150);
      await page.evaluate(([a, b]) => window.__ehvCur && window.__ehvCur(a, b, false), [cur.x, cur.y]).catch(() => {});
      await page.waitForTimeout(250);
      await ensure();
      return true;
    },
    // zoom the camera onto an element for `hold` seconds (no click). zoom: 1.4 (light) to 2.2 (close)
    async focus(sel, hold = 2.2, zoom) {
      const b = await v.box(sel);
      if (!b) return false;
      await v.cursorTo(b.x + Math.min(b.width / 2, 160), b.y + Math.min(b.height / 2, 60));
      events.push({ t: now(), x: b.x + b.width / 2, y: b.y + b.height / 2, type: 'focus', hold, ...(zoom ? { zoom } : {}) });
      await page.waitForTimeout(hold * 1000 + 500);
      return true;
    },
    async type(sel, text) { if (await v.click(sel)) await page.keyboard.type(text, { delay: 70 }); },
    async scroll(px, ms = 1500) {
      await page.evaluate(([d, t]) => new Promise((res) => {
        const el = document.scrollingElement, s = el.scrollTop, t0 = performance.now();
        const step = (n) => { const k = Math.min(1, (n - t0) / t); el.scrollTop = s + d * (k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2); k < 1 ? requestAnimationFrame(step) : res(); };
        requestAnimationFrame(step);
      }), [px, ms]).catch(() => {});
      await page.waitForTimeout(250);
    },
    async scrollTo(sel) {
      const y = await page.evaluate((s) => { const e = document.querySelector(s); return e ? e.getBoundingClientRect().top - innerHeight * 0.2 : null; }, sel).catch(() => null);
      if (y === null) { console.log('   (skipped, not found:', sel + ')'); return false; }
      await v.scroll(y, Math.min(2200, 600 + Math.abs(y)));
      return true;
    },
    async card(h, p, ms) {
      if (!page.url().startsWith(BASE)) await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
      await ensure();
      await page.evaluate(() => window.__ehvCap && window.__ehvCap('')).catch(() => {});
      caption = '';
      await page.evaluate(([a, b]) => window.__ehvCard(a, b), [h, p]);
      await page.waitForTimeout(ms);
      await page.evaluate(() => window.__ehvCard(''));
      await page.waitForTimeout(500);
    },
    async topLeadId() {
      const r = await page.request.get(BASE + '/api/parcels?sort=score&per=1&page=1');
      const j = await r.json().catch(() => ({}));
      const id = (j.rows || j.items || [])[0]?.id;
      if (!id) throw new Error('No leads found (is demo data loaded?)');
      return id;
    },
  };
  return v;
}

async function login(context) {
  const email = process.env.EH_EMAIL, password = process.env.EH_PASSWORD;
  if (!email || !password) { console.log('No EH_EMAIL/EH_PASSWORD: recording public pages only; app pages will show the login screen.'); return; }
  const r = await context.request.post(BASE + '/api/auth/login', { data: { email, password } });
  if (!r.ok()) throw new Error('Login failed: ' + r.status() + ' ' + (await r.text()).slice(0, 200));
  // keep tour, chat and welcome screens out of the video
  await context.request.post(BASE + '/api/auth/tour-seen').catch(() => {});
  await context.request.put(BASE + '/api/settings', { data: { onboarded: true } }).catch(() => {});
}

async function newContext(browser, dir) {
  const base = MOBILE ? { ...devices['iPhone 13'] } : { viewport: { width: W, height: H }, deviceScaleFactor: 1 };
  const ctx = await browser.newContext({ ...base, recordVideo: { dir, size: { width: W, height: H } } });
  await ctx.addInitScript(OVERLAY.replace('(() => {', '(() => { if (!document.documentElement || document.readyState === "loading") { document.addEventListener("DOMContentLoaded", () => setTimeout(arguments.callee, 0)); return; }').replace('(() => {', '(function f() {').replace('setTimeout(arguments.callee, 0)', 'setTimeout(f, 0)'));
  await ctx.addInitScript(() => { try { localStorage.setItem('eh_hide_banner', '1'); localStorage.setItem('eh_chat_seen', '1'); } catch (e) { } });
  await login(ctx);
  return ctx;
}

function toMp4(webm, name) {
  const mp4 = path.join(OUT, name + '.mp4');
  try {
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', webm, '-vf', 'scale=' + VW + ':' + VH + ':flags=lanczos', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4]);
    return mp4;
  } catch (e) { return null; }
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const tmp = fs.mkdtempSync(path.join(OUT, '.raw-'));
  const browser = await chromium.launch();
  const groups = SPLIT ? scenes.map((s) => [s]) : [scenes];
  const made = [];
  for (const group of groups) {
    const ctx = await newContext(browser, tmp);
    const page = await ctx.newPage();
    const t0 = Date.now();
    const events = [];
    const v = helpers(page, events, t0);
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    for (const s of group) {
      console.log('scene:', s.id, '-', s.title);
      v.sceneCap = CAPTIONS && s.caption ? s.caption : '';
      await v.caption(v.sceneCap);
      try { await s.run(v); } catch (e) { console.log('   scene error:', e.message.split('\n')[0]); }
    }
    await v.caption('');
    await page.waitForTimeout(600);
    const raw = await page.video().path();
    await ctx.close();
    const name = SPLIT ? 'estatehawk-' + group[0].id : 'estatehawk-demo' + (pick ? '-' + group.map((s) => s.id).join('-').slice(0, 60) : '') + (MOBILE ? '-mobile' : '');
    const webm = path.join(OUT, name + '.webm');
    fs.renameSync(raw, webm);
    const evf = path.join(OUT, name + '.events.json');
    fs.writeFileSync(evf, JSON.stringify({ w: W, h: H, events }));
    let mp4 = null;
    try {
      mp4 = path.join(OUT, name + '.mp4');
      execFileSync('python3', [path.join(__dirname, 'zoom.py'), webm, evf, mp4, '--size', VW + 'x' + VH], { stdio: 'ignore' });
    } catch (e) { mp4 = toMp4(webm, name); }
    if (mp4) fs.unlinkSync(webm);
    made.push(mp4 || webm);
  }
  await browser.close();
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log('\nVideo ready:\n' + made.map((m) => '  ' + m).join('\n'));
})().catch((e) => { console.error(e); process.exit(1); });
