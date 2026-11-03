// EstateHawk front-end core: helpers, layout, router.
import * as V from './views.js';

// ---------- icons (lucide-style strokes) ----------
const P = {
  home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  map: '<path d="m9 4-6 2v14l6-2 6 2 6-2V4l-6 2-6-2z"/><path d="M9 4v14M15 6v14"/>',
  bell: '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10 21a2 2 0 0 0 4 0"/>',
  county: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h5"/>',
  send: '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  help: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01"/>',
  chev: '<path d="m6 9 6 6 6-6"/>', left: '<path d="m15 18-6-6 6-6"/>', right: '<path d="m9 18 6-6-6-6"/>', back: '<path d="M19 12H5M12 19l-7-7 7-7"/>',
  doc: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
  star: '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9z"/>',
  house: '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-5h4v5"/>',
  pin: '<path d="M12 21s-7-6.2-7-11a7 7 0 1 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
  dollar: '<path d="M12 2v20M17 6.5C17 4.6 14.8 3.5 12 3.5S7 4.6 7 6.6c0 4.9 10 2.6 10 7.6 0 2-2.2 3.3-5 3.3s-5-1.2-5-3.3"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  users: '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0M16 4a4 4 0 0 1 0 8M22 21a7 7 0 0 0-5-6.7"/>',
  cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>',
  sms: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  dots: '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>',
  share: '<path d="M12 3v13M7 8l5-5 5 5"/><path d="M5 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5"/>',
  bookmark: '<path d="M19 21 12 16l-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  check: '<path d="m5 12 5 5L20 7"/>', x: '<path d="M18 6 6 18M6 6l12 12"/>', plus: '<path d="M12 5v14M5 12h14"/>',
  trend: '<path d="m3 17 6-6 4 4 8-8"/><path d="M14 7h7v7"/>', up: '<path d="M12 19V5M5 12l7-7 7 7"/>',
  gavel: '<path d="m14 13-7.5 7.5a2.1 2.1 0 0 1-3-3L11 10"/><path d="m16 16 6-6M8 8l6-6M9 7l8 8M21 11l-8-8"/>',
  swap: '<path d="M17 3l4 4-4 4M3 7h18M7 21l-4-4 4-4M21 17H3"/>', alert: '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
  layers: '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/>', locate: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/><circle cx="12" cy="12" r="8"/>',
  db: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  sliders: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>', link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>', shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
  card: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/>', sparkle: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
  print: '<path d="M6 9V2h12v7"/><rect x="6" y="14" width="12" height="8"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>',
  download: '<path d="M12 3v12M7 10l5 5 5-5M5 21h14"/>', filter: '<path d="M22 3H2l8 9.5V19l4 2v-8.5z"/>', menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  letter: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 9h10M7 13h6"/>', note: '<path d="M4 4h16v12l-4 4H4z"/><path d="M16 20v-4h4"/>',
};
export const ic = (n, s = 18) => `<svg class="ic" viewBox="0 0 24 24" style="width:${s}px;height:${s}px">${P[n] || ''}</svg>`;

// ---------- helpers ----------
export const $ = (s, el = document) => el.querySelector(s);
export const $$ = (s, el = document) => [...el.querySelectorAll(s)];
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const money = (v, d = 0) => (v == null || isNaN(v)) ? '--' : '$' + Number(v).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d });
export const kmoney = (v) => v == null ? '--' : Math.abs(v) >= 1000 ? '$' + (v / 1000).toFixed(v >= 100000 ? 0 : 0) + 'K' : money(v);
export const num = (v) => v == null ? '--' : Number(v).toLocaleString('en-US');
export const title = (s) => String(s || '').toLowerCase().replace(/\b([a-z])/g, (m) => m.toUpperCase()).replace(/\b(Oh|Ne|Nw|Se|Sw|Llc|Csd|Lsd)\b/g, (m) => m.toUpperCase());
export const yrs = (v) => v == null ? '--' : String(Math.round(v));
export function scorePill(s) {
  if (s == null) return '<span class="score s-lo">--</span>';
  const c = s >= 85 ? 's-hi' : s >= 65 ? 's-mid' : 's-lo';
  return `<span class="score ${c}">${Math.round(s)}</span>`;
}
export function ago(ts) {
  if (!ts) return 'never';
  const d = new Date(ts.replace(' ', 'T'));
  const s = (Date.now() - d) / 1000;
  if (s < 60) return 'just now';
  if (s < 3600) return Math.floor(s / 60) + 'm ago';
  if (s < 86400) return Math.floor(s / 3600) + 'h ago';
  if (s < 86400 * 7) return Math.floor(s / 86400) + 'd ago';
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
export const fmtDate = (d, o = { month: 'short', day: 'numeric', year: 'numeric' }) => { if (!d) return '--'; const x = d instanceof Date ? d : new Date(String(d).length === 10 ? d + 'T12:00' : String(d).replace(' ', 'T')); return isNaN(x) ? '--' : x.toLocaleDateString('en-US', o); };

// Satellite thumbnail: one Esri World Imagery tile at the parcel location (free, no key)
export const place = (p) => [title(p.city || ''), [p.state || 'OH', p.zip].filter(Boolean).join(' ')].filter(Boolean).join(', ');
export function tileUrl(lat, lng, z = 18) {
  if (lat == null || lng == null) return '';
  const x = Math.floor((lng + 180) / 360 * 2 ** z);
  const r = lat * Math.PI / 180;
  const y = Math.floor((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * 2 ** z);
  return `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`;
}
const HOUSE_SVG = "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%239AA29E' stroke-width='1.6'%3E%3Cpath d='M3 11 12 4l9 7'/%3E%3Cpath d='M5 10v10h14V10'/%3E%3Cpath d='M10 20v-5h4v5'/%3E%3C/svg%3E\")";
// layered: county aerial photo > satellite tile > house icon (a layer that fails to load is simply skipped)
export const thumb = (p, cls = '') => {
  const layers = [p.photo_url && `url('${p.photo_url}')`, p.lat != null && `url('${tileUrl(p.lat, p.lng)}')`, HOUSE_SVG].filter(Boolean);
  return `<div class="thumb ${cls}" style="background-image:${layers.join(',')};background-size:cover,cover,40% auto;background-repeat:no-repeat;background-position:center"></div>`;
};
export const homeLine = (p) => [p.beds && `${p.beds} bd`, p.baths_full != null && p.beds && `${p.baths_full + (p.baths_half ? .5 * p.baths_half : 0)} ba`, p.living_area && `${Number(p.living_area).toLocaleString('en-US')} sqft`, p.year_built && `built ${p.year_built}`].filter(Boolean).join(' · ');
export const streetView = (p) => `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${p.lat},${p.lng}`;
export const gmaps = (p) => `https://www.google.com/maps/search/?api=1&query=${p.lat},${p.lng}`;

export async function api(path, opts = {}) {
  const o = { headers: { 'Content-Type': 'application/json', ...(S.viewOrg ? { 'X-Org': String(S.viewOrg) } : {}) }, ...opts };
  if (o.body && typeof o.body !== 'string') o.body = JSON.stringify(o.body);
  const r = await fetch(path, o);
  if (r.status === 401 && !path.startsWith('/api/auth/')) { showLogin(); throw new Error('Please log in'); }
  if (r.status === 402) {
    let j = {}; try { j = await r.clone().json(); } catch (e) { }
    if (j.expired) { showExpired(j.detail); throw new Error(j.detail); }
  }
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch (e) { }
    throw new Error(msg);
  }
  const ct = r.headers.get('content-type') || '';
  return ct.includes('json') ? r.json() : r.text();
}

export function toast(msg, err = false) {
  const t = document.createElement('div');
  t.className = 'toast' + (err ? ' err' : '');
  t.textContent = msg;
  $('#toasts').append(t);
  setTimeout(() => t.remove(), 4200);
}

export function modal(html, onMount) {
  const m = $('#modal');
  $('#modalCard').innerHTML = html;
  m.hidden = false;
  const close = () => { m.hidden = true; $('#modalCard').innerHTML = ''; };
  m.onclick = (e) => { if (e.target === m) close(); };
  $$('[data-close]', m).forEach((b) => b.onclick = close);
  onMount && onMount($('#modalCard'), close);
  return close;
}

export function menu(anchor, items) {
  closeMenus();
  const d = document.createElement('div');
  d.className = 'dropdown open floating';
  d.innerHTML = items.map((it, i) => it === '-' ? '<hr style="border:0;border-top:1px solid var(--line);margin:4px 0">' :
    `<button class="item ${it.danger ? 'danger' : ''}" data-i="${i}">${it.icon ? ic(it.icon, 16) : ''}${esc(it.label)}</button>`).join('');
  document.body.append(d);
  const r = anchor.getBoundingClientRect();
  d.style.position = 'fixed';
  d.style.top = Math.min(r.bottom + 4, innerHeight - d.offsetHeight - 8) + 'px';
  d.style.left = Math.max(8, Math.min(r.right - d.offsetWidth, innerWidth - d.offsetWidth - 8)) + 'px';
  d.onclick = (e) => { const b = e.target.closest('[data-i]'); if (b) { closeMenus(); items[+b.dataset.i].fn(); } };
  setTimeout(() => document.addEventListener('click', closeMenus, { once: true }), 0);
}
export function closeMenus() { $$('.dropdown.floating').forEach((d) => d.remove()); $$('.dropdown.open').forEach((d) => d.classList.remove('open')); }

// ---------- global state ----------
export const S = { meta: null, user: null, viewOrg: (() => { try { return +localStorage.getItem('eh_view_org') || null; } catch (e) { return null; } })(), county: localStorage.getItem('eh_county') || 'all' };
export function setCounty(c) { S.county = String(c); try { localStorage.setItem('eh_county', S.county); } catch (e) { } }
export async function refreshMeta() {
  S.meta = await api('/api/meta');
  renderChrome();
  return S.meta;
}
export const countyName = (id) => (S.meta?.counties.find((c) => String(c.id) === String(id)) || {}).name;
export function countySelect(id = 'countySel', withAll = true, val = S.county) {
  const opts = (withAll ? [`<option value="all">All counties</option>`] : []).concat(
    (S.meta?.counties || []).map((c) => `<option value="${c.id}" ${String(val) === String(c.id) ? 'selected' : ''}>${esc(c.name)}, ${esc(c.state)}</option>`));
  return `<select class="select" id="${id}">${opts.join('')}</select>`;
}

// ---------- chrome ----------
const NAV = [
  ['deals', 'Deals', 'home'], ['map', 'Map', 'map'], ['alerts', 'Alerts', 'bell'], ['counties', 'Counties', 'county'],
  ['outreach', 'Outreach', 'send'], ['reports', 'Reports', 'chart'], ['settings', 'Settings', 'gear'],
];
export function setViewOrg(id) {
  try { id ? localStorage.setItem('eh_view_org', String(id)) : localStorage.removeItem('eh_view_org'); } catch (e) { }
  S.viewOrg = id || null; S.meta = null; location.hash = '#/deals'; location.reload();
}

function renderChrome() {
  const m = S.meta;
  const nav = m.super ? NAV.concat([['admin', 'Admin', 'shield']]) : NAV;
  const route = location.hash.split('/')[1] || 'deals';
  const active = route === 'deal' ? 'deals' : route;
  $('#nav').innerHTML = nav.map(([k, l, i]) => `<a href="#/${k}" class="${active === k ? 'active' : ''}">${ic(i, 19)}<span>${l}</span>${k === 'alerts' && m.unread_alerts ? `<span class="badge">${m.unread_alerts}</span>` : ''}</a>`).join('');
  $('#tabbar').innerHTML = [['deals', 'Deals', 'home'], ['map', 'Map', 'map'], ['alerts', 'Alerts', 'bell'], ['outreach', 'Outreach', 'send'], ['settings', 'More', 'dots']]
    .map(([k, l, i]) => `<a href="#/${k}" class="${active === k || (k === 'settings' && ['counties', 'reports', 'settings'].includes(active)) ? 'active' : ''}">${ic(i, 21)}<span>${l}</span>${k === 'alerts' && m.unread_alerts ? `<span class="badge">${m.unread_alerts}</span>` : ''}</a>`).join('');
  const o = m.org || {}, L = o.limits || {};
  const cLimit = L.counties == null ? 'all' : L.counties;
  $('#planCard').innerHTML = `<b>${esc(o.label || 'Plan')}${o.plan === 'internal' ? '' : ' plan'}</b>
    <div class="small muted">${esc(o.name || '')}</div>
    <div class="small muted" style="margin-top:6px">${cLimit === 'all' ? m.counties.length + ' counties' : m.counties.length + ' of ' + cLimit + ' counties'} · ${num(m.active)} leads</div>
    ${L.reveals ? `<div class="bar"><i style="width:${Math.min(100, o.reveals_used / L.reveals * 100)}%"></i></div><div class="small muted">${o.reveals_used} / ${L.reveals} leads opened</div>` : ''}
    ${o.plan === 'trial' ? `<div class="small" style="margin-top:4px;color:${o.days_left <= 3 ? '#B42318' : 'var(--ink2)'}">${o.days_left >= 0 ? o.days_left + ' days left in trial' : 'Trial ended'}</div>` : ''}
    ${o.plan === 'internal' ? '' : `<button class="btn sm" style="width:100%;margin-top:12px" id="upBtn">Upgrade Plan</button>`}`;
  if ($('#upBtn')) $('#upBtn').onclick = () => plansModal();
  const name = S.user?.name || m.settings.profile?.name || 'You';
  $('#userName').textContent = name;
  $('#avatar').textContent = name.trim()[0]?.toUpperCase() || 'U';
  $('#bellDot').classList.toggle('on', m.unread_alerts > 0);
  const viewing = S.viewOrg && m.super && o.id !== 1 ? `<div class="demo-banner" style="background:#EEF4FF;border-color:#C7D7FE">${ic('shield', 16)}<span>You are viewing <b>${esc(o.name)}</b> as super admin (${esc(o.label)}).</span><button class="btn xs" style="margin-left:auto" id="exitView">Back to my dashboard</button></div>` : '';
  const trial = o.plan === 'trial' && !viewing ? `<div class="demo-banner">${ic('lock', 16)}<span><b>Free trial:</b> ${o.days_left >= 0 ? o.days_left + ' days left' : 'ended'}. You can open ${o.reveals_left} more leads in full. Paid plans show every lead, owner and contact.</span><button class="btn xs primary" style="margin-left:auto" id="bannerUp">See plans</button></div>` : '';
  $('#banner').innerHTML = viewing + trial + (m.settings.demo ? `<div class="demo-banner">${ic('alert', 16)}<span><b>Demo data</b> is shown (made-up owners and addresses). Run a real county sync from Counties, then remove demo data in Settings.</span>
    <a class="btn xs" style="margin-left:auto" href="#/settings/profile">Manage</a></div>` : '');
  if ($('#exitView')) $('#exitView').onclick = () => setViewOrg(null);
  if ($('#bannerUp')) $('#bannerUp').onclick = () => plansModal();
}

function initTopbar() {
  $('.search .i-search').outerHTML = ic('search', 17);
  $('#helpBtn').innerHTML = ic('help', 20);
  $('#bellBtn').innerHTML = ic('bell', 20) + '<b class="dot" id="bellDot"></b>';
  $('#userBtn .i-chev').outerHTML = ic('chev', 15);
  $('#menuBtn').innerHTML = ic('menu', 20);
  $('#menuBtn').onclick = (e) => { e.stopPropagation(); $('#sidebar').classList.toggle('open'); };
  document.addEventListener('click', (e) => { if (!e.target.closest('#sidebar') && !e.target.closest('#menuBtn')) $('#sidebar').classList.remove('open'); });

  // global search
  const inp = $('#searchInput'), box = $('#searchResults');
  let t, sel = -1;
  inp.oninput = () => {
    clearTimeout(t);
    t = setTimeout(async () => {
      const q = inp.value.trim();
      if (q.length < 2) { box.classList.remove('open'); return; }
      const r = await api('/api/parcels?active=0&per=8&q=' + encodeURIComponent(q));
      sel = -1;
      box.innerHTML = r.rows.length ? r.rows.map((p) => `<a href="#/deal/${encodeURIComponent(p.id)}">${thumb(p)}<div class="grow"><b>${esc(title(p.street))}</b><div class="small muted">${esc(title(p.city))} ${esc(p.zip)} · ${esc(title(p.owner_name))} · ${esc(p.parcel_number)}</div></div>${scorePill(p.score)}</a>`).join('')
        : `<div class="empty small">No matches</div>`;
      box.classList.add('open');
    }, 180);
  };
  inp.onkeydown = (e) => {
    const items = $$('a', box);
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault(); sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      items.forEach((a, i) => a.classList.toggle('sel', i === sel));
    } else if (e.key === 'Enter' && items.length) { location.hash = items[Math.max(sel, 0)].getAttribute('href'); box.classList.remove('open'); inp.blur(); }
    else if (e.key === 'Escape') { box.classList.remove('open'); inp.blur(); }
  };
  box.onclick = () => { box.classList.remove('open'); inp.value = ''; };
  document.addEventListener('keydown', (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); inp.focus(); } });
  document.addEventListener('click', (e) => { if (!e.target.closest('#globalSearch')) box.classList.remove('open'); });

  $('#bellBtn').onclick = async (e) => {
    e.stopPropagation();
    const bm = $('#bellMenu');
    if (bm.classList.contains('open')) return bm.classList.remove('open');
    closeMenus();
    const r = await api('/api/alerts?limit=6');
    bm.innerHTML = `<div class="row between" style="padding:8px 10px"><b>Alerts</b><a class="small" style="color:var(--green)" href="#/alerts">View all</a></div>` +
      (r.rows.map((a) => `<a href="${a.parcel_id ? '#/deal/' + encodeURIComponent(a.parcel_id) : '#/alerts'}">${V.alertIcon(a.type)}<div class="grow"><div style="font-weight:${a.read ? 500 : 650}">${esc(a.title)}</div><div class="tiny muted">${esc(a.county_name || '')} · ${ago(a.ts)}</div></div></a>`).join('') || '<div class="empty small">No alerts yet</div>');
    bm.classList.add('open');
  };
  $('#userBtn').onclick = (e) => {
    e.stopPropagation();
    menu($('#userBtn'), [
      { label: 'Profile', icon: 'user', fn: () => location.hash = '#/settings/profile' },
      { label: 'Deal scoring', icon: 'sliders', fn: () => location.hash = '#/settings/scoring' },
      { label: 'Integrations', icon: 'link', fn: () => location.hash = '#/settings/integrations' },
      '-',
      { label: 'Setup wizard', icon: 'sparkle', fn: () => location.hash = '#/welcome' },
      '-',
      ...(['admin', 'superadmin'].includes(S.user?.role) ? [{ label: 'Team & logins', icon: 'user', fn: teamModal }] : []),
      ...(S.meta?.super ? [{ label: 'Admin panel', icon: 'shield', fn: () => location.hash = '#/admin' }] : []),
      { label: 'Change password', icon: 'sliders', fn: passwordModal },
      { label: 'Log out', icon: 'right', fn: async () => { await api('/api/auth/logout', { method: 'POST' }); location.reload(); } },
    ]);
  };
  $('#helpBtn').onclick = () => modal(`<h2>How EstateHawk works</h2>
    <ol style="line-height:1.8;padding-left:18px;color:var(--ink2)">
      <li>Every night at ${esc(S.meta.settings.sync_time)} it downloads each county's official tax-delinquent list.</li>
      <li>It compares with yesterday: new delinquent owners, paid-off parcels, owner changes and bigger debts become <b>Alerts</b>.</li>
      <li>Each property page is read for value, owner mailing address and tax history, then given a <b>deal score</b> (weights in Settings).</li>
      <li>Open a deal, set your offer terms and click <b>Draft offer</b> (Gemini AI if a key is added, otherwise a template). Move it through <b>Outreach</b>.</li>
    </ol>
    <p class="small muted">Values are county appraisals; equity ignores any mortgage (not in county records). Always verify before making an offer.</p>
    <div class="row" style="justify-content:flex-end"><button class="btn primary" data-close>Got it</button></div>`);
}

// sync status in the corner (polls while a sync runs)
let syncTimer = null;
export function watchSync(onDone) {
  clearInterval(syncTimer);
  syncTimer = setInterval(async () => {
    const s = await api('/api/sync/status');
    $$('[data-sync-status]').forEach((el) => el.innerHTML = s.running ? `<span class="small">${esc(s.county || '')}: ${esc(s.step)}</span><div class="progress"><i style="width:${s.progress}%"></i></div>` : '');
    if (!s.running) { clearInterval(syncTimer); await refreshMeta(); onDone && onDone(); toast('Sync finished'); }
  }, 2000);
}

// ---------- login ----------
export async function showLogin() {
  let setup = false;
  try { const r = await fetch('/api/auth/me'); if (r.ok) return; setup = (await r.json()).setup; } catch (e) { }
  ['#sidebar', '#topbar', '#banner'].forEach((s) => { if ($(s)) $(s).style.display = 'none'; });
  if ($('#tabbar')) $('#tabbar').style.visibility = 'hidden';
  const view = $('#view'); view.style.maxWidth = 'none';
  view.innerHTML = `<div style="min-height:80vh;display:grid;place-items:center"><form class="card card-pad" id="loginForm" style="width:min(400px,100%)">
    <div class="row" style="gap:10px;margin-bottom:6px"><img src="/static/icon.svg" width="30" height="30" alt=""><h2 style="margin:0">EstateHawk</h2></div>
    <p class="muted small" style="margin:0 0 16px">${setup ? 'First time here. Create the admin account (this is you).' : 'Log in to see your deals.'}</p>
    ${setup ? '<div class="field"><label>Your name</label><input class="input" id="lName" autocomplete="name"></div>' : ''}
    <div class="field"><label>Email</label><input class="input" id="lEmail" type="email" autocomplete="username" required></div>
    <div class="field"><label>Password</label><input class="input" id="lPw" type="password" autocomplete="${setup ? 'new-password' : 'current-password'}" required minlength="${setup ? 8 : 1}"></div>
    <div class="small" id="lErr" style="color:#B42318;min-height:18px"></div>
    <button class="btn primary" style="width:100%;margin-top:6px">${setup ? 'Create admin account' : 'Log in'}</button>
    ${setup ? '' : '<p class="tiny muted" style="margin:12px 0 0">Forgot your password? Ask your EstateHawk admin to reset it.</p>'}
  </form></div>`;
  $('#loginForm').onsubmit = async (e) => {
    e.preventDefault();
    const body = { email: $('#lEmail').value, password: $('#lPw').value, name: $('#lName')?.value };
    const r = await fetch(setup ? '/api/auth/setup' : '/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (r.ok) { location.hash = '#/deals'; location.reload(); return; }
    let msg = 'Could not log in'; try { msg = (await r.json()).detail || msg; } catch (x) { }
    $('#lErr').textContent = msg;
  };
}

const CONTACT = 'zeeshanlatif.tech@gmail.com';
export function plansModal(note = '') {
  const P = (S.meta && S.meta.plans) || {};
  const cur = S.meta?.org?.plan;
  const feat = (k, p) => [p.counties == null ? 'All counties' : `${p.counties} ${p.counties > 1 ? 'counties' : 'county'}`,
    p.users == null ? 'Unlimited users' : `${p.users} ${p.users > 1 ? 'users' : 'user'}`,
    p.reveals ? `${p.reveals} leads in full` : 'Every lead in full: owner, address, contacts',
    p.export ? 'CSV export + mail-merge letters' : 'No export', k === 'trial' ? `${p.days} days free` : 'Daily sync + alerts + AI offers'];
  modal(`<h2>Plans</h2>${note ? `<p class="small" style="color:#B42318">${esc(note)}</p>` : ''}<p class="muted small">Online payment is coming soon. To upgrade now, contact us and we switch your plan the same day.</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:14px 0">${Object.entries(P).map(([k, p]) => `
      <div class="card card-pad" style="${k === cur ? 'border:2px solid var(--green)' : ''}"><b>${esc(p.label)}</b>
        <div style="font-size:24px;font-weight:700;margin:6px 0">${p.price ? '$' + p.price : 'Free'}<span class="small muted" style="font-weight:400">${p.price ? ' / month' : ''}</span></div>
        <ul class="small" style="padding-left:16px;margin:0;line-height:1.7">${feat(k, p).map((f) => `<li>${esc(f)}</li>`).join('')}</ul>
        ${k === cur ? '<div class="pill p-green tiny" style="margin-top:8px">Current plan</div>' : ''}</div>`).join('')}</div>
    <div class="row" style="justify-content:flex-end"><button class="btn" data-close>Close</button>
      <a class="btn primary" href="mailto:${CONTACT}?subject=${encodeURIComponent('EstateHawk upgrade: ' + (S.meta?.org?.name || ''))}">Contact us to upgrade</a></div>`);
}

export function showExpired(msg) {
  ['#sidebar', '#topbar'].forEach((s) => { if ($(s)) $(s).style.display = 'none'; });
  $('#view').innerHTML = `<div style="min-height:70vh;display:grid;place-items:center"><div class="card card-pad" style="max-width:460px;text-align:center">
    <div style="margin-bottom:8px">${ic('lock', 32)}</div><h2>${esc(msg || 'Your free trial has ended')}</h2>
    <p class="muted">Your deals, notes and offers are saved. Pick a plan and we turn your account back on right away.</p>
    <div class="row" style="justify-content:center;gap:8px"><button class="btn" id="exPlans">See plans</button>
    <a class="btn primary" href="mailto:${CONTACT}?subject=${encodeURIComponent('EstateHawk upgrade')}">Contact us</a>
    <button class="btn" id="exOut">Log out</button></div></div></div>`;
  $('#exPlans').onclick = () => plansModal();
  $('#exOut').onclick = async () => { await fetch('/api/auth/logout', { method: 'POST' }); location.reload(); };
}

function passwordModal() {
  modal(`<h2>Change password</h2><div style="height:10px"></div>
    <div class="field"><label>Current password</label><input class="input" type="password" id="pOld"></div>
    <div class="field"><label>New password (8+ characters)</label><input class="input" type="password" id="pNew"></div>
    <div class="row" style="justify-content:flex-end"><button class="btn" data-close>Cancel</button><button class="btn primary" id="pSave">Save</button></div>`, (m, close) => {
    $('#pSave', m).onclick = async () => {
      try { await api('/api/auth/password', { method: 'POST', body: { old: $('#pOld', m).value, new: $('#pNew', m).value } }); close(); toast('Password changed'); }
      catch (e) { toast(e.message, true); }
    };
  });
}

export async function teamModal() {
  const users = await api('/api/users');
  const lim = S.meta?.org?.limits?.users;
  modal(`<h2>Team & logins</h2><p class="muted small">Everyone here can log in to ${esc(S.meta?.org?.name || 'your company')}. Notes, deals and offers are shared inside your team only.${lim ? ` Your plan allows ${lim} user(s).` : ''}</p>
    <div style="max-height:260px;overflow:auto">${users.map((u) => `<div class="row" style="padding:8px 0;border-top:1px solid var(--line);gap:8px">
      <div class="grow" style="min-width:0"><b>${esc(u.name)}</b> <span class="pill tiny">${u.role}</span>${u.active ? '' : ' <span class="pill tiny" style="background:#FEE4E2;color:#B42318">blocked</span>'}<div class="tiny muted ellip">${esc(u.email)} · last login ${u.last_login ? esc(fmtDate(u.last_login)) : 'never'}</div></div>
      ${u.id === S.user.id ? '' : `<button class="btn xs" data-reset="${u.id}">Reset password</button><button class="btn xs" data-act="${u.id}" data-on="${u.active ? 0 : 1}">${u.active ? 'Block' : 'Unblock'}</button>`}</div>`).join('')}</div>
    <h3 style="margin:16px 0 8px">Add a person</h3>
    <div class="terms"><div class="field"><label>Name</label><input class="input" id="uName"></div><div class="field"><label>Email</label><input class="input" id="uEmail" type="email"></div></div>
    <div class="terms"><div class="field"><label>Temporary password</label><input class="input" id="uPw" value="${Math.random().toString(36).slice(2, 8)}Eh!${Math.floor(Math.random() * 90 + 10)}"></div>
      <div class="field"><label>Role</label><select class="select" id="uRole"><option value="member">Member</option><option value="admin">Admin</option></select></div></div>
    <div class="row" style="justify-content:flex-end"><button class="btn" data-close>Close</button><button class="btn primary" id="uAdd">Add</button></div>`, (m, close) => {
    $('#uAdd', m).onclick = async () => {
      try {
        await api('/api/users', { method: 'POST', body: { name: $('#uName', m).value, email: $('#uEmail', m).value, password: $('#uPw', m).value, role: $('#uRole', m).value } });
        toast(`Added. Send them the link, their email and password: ${$('#uPw', m).value}`); close(); teamModal();
      } catch (e) { toast(e.message, true); }
    };
    $$('[data-act]', m).forEach((b) => b.onclick = async () => { await api('/api/users/' + b.dataset.act, { method: 'PUT', body: { active: b.dataset.on === '1' } }); close(); teamModal(); });
    $$('[data-reset]', m).forEach((b) => b.onclick = async () => {
      const pw = Math.random().toString(36).slice(2, 8) + 'Eh!' + Math.floor(Math.random() * 90 + 10);
      await api('/api/users/' + b.dataset.reset, { method: 'PUT', body: { password: pw } }); toast('New password: ' + pw);
    });
  });
}

// ---------- router ----------
const routes = {
  deals: V.deals, deal: V.deal, map: V.mapView, alerts: V.alerts, counties: V.counties, outreach: V.outreach,
  reports: V.reports, settings: V.settings, welcome: V.welcome, admin: V.admin,
};
let cleanup = null;
async function route() {
  closeMenus();
  $('#modal').hidden = true;
  const [, name = 'deals', ...rest] = location.hash.split('/');
  if (!S.user) {
    const r = await fetch('/api/auth/me');
    if (!r.ok) { showLogin(); return; }
    S.user = (await r.json()).user;
  }
  ['#sidebar', '#topbar'].forEach((s) => { if ($(s)) $(s).style.display = ''; });
  if (!S.meta) await refreshMeta();
  if (S.meta.org?.expired && !S.meta.super) { showExpired(S.meta.org.suspended ? 'Your company account is paused' : 'Your free trial has ended'); return; }
  if (!S.meta.settings.onboarded && S.meta.super && name !== 'welcome') { location.hash = '#/welcome'; return; }
  if (name === 'admin' && !S.meta.super) { location.hash = '#/deals'; return; }
  const fn = routes[name] || V.deals;
  document.body.classList.toggle('onboarding', name === 'welcome');
  $('#sidebar').style.display = name === 'welcome' ? 'none' : '';
  $('#topbar').style.display = name === 'welcome' ? 'none' : '';
  $('#tabbar').style.visibility = name === 'welcome' ? 'hidden' : '';
  $('#banner').style.display = name === 'welcome' ? 'none' : '';
  if (cleanup) { try { cleanup(); } catch (e) { } cleanup = null; }
  renderChrome();
  const view = $('#view');
  view.style.padding = name === 'welcome' ? '0' : '';
  view.style.maxWidth = name === 'welcome' ? 'none' : '';
  window.scrollTo(0, 0);
  try {
    cleanup = await fn(view, rest.map(decodeURIComponent));
  } catch (e) {
    console.error(e);
    view.innerHTML = `<div class="card empty">Something went wrong: ${esc(e.message)}</div>`;
  }
}
window.addEventListener('hashchange', route);
initTopbar();
route();
setInterval(async () => { if (!document.hidden && S.meta) { const m = await api('/api/meta'); if (m.unread_alerts !== S.meta.unread_alerts) { S.meta = m; renderChrome(); } } }, 60000);
