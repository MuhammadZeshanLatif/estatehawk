// EstateHawk screens. Each view(el, params) renders into el and may return a cleanup function.
import {
  $, $$, esc, ic, api, money, kmoney, num, title, yrs, scorePill, ago, fmtDate, tileUrl, place, thumb, streetView, gmaps, homeLine,
  toast, modal, menu, ask, askFee, S, setCounty, refreshMeta, countySelect, countyName, watchSync, plansModal, fitMap, guardExportClick,
} from './app.js';
export { outreach, reports, settings, welcome, alerts, counties, admin } from './views2.js';
import { loadResearch, lockedResearch, compareModal } from './research.js';
export { auctions } from './research.js';

const GREEN = '#14532D', AMBER = '#E0A030', GREY = '#8C938F';
export const scoreColor = (s) => s >= 85 ? '#1F7A45' : s >= 65 ? AMBER : GREY;
const greeting = () => { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'; };

export function alertIcon(type) {
  const m = { new_delinquent: ['doc', 'tone-red'], auction: ['cal', 'tone-amber'], owner_change: ['swap', 'tone-blue'], owner: ['user', 'tone-blue'],
    amount_up: ['trend', 'tone-green'], high_score: ['house', 'tone-violet'], paid_off: ['check', 'tone-grey'] }[type] || ['bell', 'tone-grey'];
  return `<span class="ico ${m[1]}" style="width:34px;height:34px;border-radius:50%;display:grid;place-items:center;flex:none">${ic(m[0], 17)}</span>`;
}

export function baseTiles(map, kind = 'light') {
  const L = window.L;
  if (kind === 'sat') return L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19, attribution: 'Imagery &copy; Esri' }).addTo(map);
  return L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19, attribution: 'Tiles &copy; Esri' }).addTo(map);
}
export function pin(p, sel = false) {
  return window.L.circleMarker([p.lat, p.lng], { radius: sel ? 10 : 7, color: '#fff', weight: 2, fillColor: scoreColor(p.score), fillOpacity: .95 });
}
export function popupHtml(p) {
  return `<div class="pop"><div class="row">${thumb(p, 'lg')}<div class="grow"><b style="font-size:14px">${esc(title(p.street))}</b><div class="small muted">${esc(place(p))}</div></div>${scorePill(p.score)}</div>
  <div class="nums"><div><b>${kmoney(p.appraised_total)}</b><span class="tiny muted">Est. value</span></div><div><b>${kmoney(p.est_equity)}</b><span class="tiny muted">Est. equity</span></div><div><b>${money(p.total_due ?? p.amount_owed)}</b><span class="tiny muted">Taxes owed</span></div></div>
  <div class="row"><a class="btn sm grow" href="#/deal/${encodeURIComponent(p.id)}">View deal</a><a class="btn sm primary grow" href="#/deal/${encodeURIComponent(p.id)}?offer=1">Draft offer</a></div></div>`;
}

// ================================================================ DEALS (home)
export async function deals(el) {
  const st = { page: 1, per: 25, sort: 'score', min_score: '', min_owed: '', max_owed: '', min_years: '', ptype: 'homes', out_of_state: '', owner_status: '', new_days: '', min_equity: '', q: '' };
  const prof = S.meta.settings.profile;
  el.innerHTML = `
  <div class="page-head">
    <div><h1>${greeting()}, ${esc((S.meta.user?.name || prof.name || 'there').split(' ')[0])}</h1><div class="sub">Here are your latest off-market opportunities from tax-delinquent records.</div></div>
    <div class="right">
      <div class="row">${ic('pin', 18)}${countySelect('countySel')}</div>
      <div class="updated-box">${ic('cal', 18)}<div><div class="small" style="font-weight:600">${fmtDate(new Date())}</div><div class="tiny muted">Last updated ${ago(S.meta.last_sync)}</div></div>
        <button class="icon-btn" id="syncBtn" title="Sync now" aria-label="Sync now">${ic('refresh', 17)}</button></div>
      <div data-sync-status></div>
    </div>
  </div>
  <div class="grid stats" id="stats">${'<div class="card stat skeleton" style="height:96px"></div>'.repeat(4)}</div>
  <div id="filterSummary" class="card" style="display:none;margin-top:18px;padding:18px 20px">
    <div class="row between" style="flex-wrap:wrap;gap:14px">
      <div><h2 style="margin:0 0 10px">Applied filters</h2><div id="filterChips" class="row gap6" style="flex-wrap:wrap"></div></div>
      <div class="row" style="gap:24px;flex-wrap:wrap"><div><div class="small muted">Total leads</div><div id="filterTotal" class="num" style="font-size:26px;font-weight:700"></div></div><div><div class="small muted">Matching leads</div><div id="filterMatching" class="num" style="font-size:26px;font-weight:700;color:var(--green-ink)"></div></div></div>
    </div>
  </div>
  <div class="deals-grid">
    <div class="card" style="min-width:0">
      <div class="card-head" style="padding-top:20px"><div><h2>Property Leads</h2><div class="small muted" id="leadSub"></div></div>
        <div class="right row"><div class="search" style="width:260px;height:36px">${ic('search', 16)}<input id="leadQ" placeholder="Search properties..."></div></div></div>
      <div class="filters">
        <select class="select" id="fScore" aria-label="Minimum deal score"><option value="">Deal Score</option><option value="85">85+ (High)</option><option value="80">80+</option><option value="65">65+</option></select>
        <select class="select" id="fOwed"><option value="">Taxes Owed</option><option value="0-2000">Under $2,000</option><option value="2000-10000">$2,000 to $10,000</option><option value="10000-">Over $10,000</option></select>
        <select class="select" id="fYears"><option value="">Years Behind</option><option value="2">2+ years</option><option value="3">3+ years</option><option value="5">5+ years</option></select>
        <button class="chip-btn" id="fMore">${ic('filter', 15)} More Filters</button>
        <span class="grow"></span>
        <span class="small muted" id="pageInfo"></span>
        <form class="lead-jump" id="leadJump"><label for="leadNumber">Go to lead</label><input class="input" id="leadNumber" type="number" inputmode="numeric" min="1" step="1" placeholder="#" aria-label="Lead number"><button class="btn sm" type="submit">Go</button></form>
        <div class="pager"><button class="btn sm" id="prev" aria-label="Previous page">${ic('left', 16)}</button><form class="page-jump" id="pageJump"><label for="pageNumber">Page</label><input class="input" id="pageNumber" type="number" inputmode="numeric" min="1" step="1" aria-label="Page number"><span class="small muted" id="pageTotal"></span><button class="btn sm" type="submit">Go</button></form><button class="btn sm" id="next" aria-label="Next page">${ic('right', 16)}</button></div>
      </div>
      <div id="ownerHelp" class="small muted" style="display:none;padding:0 20px 14px"></div>
      <div id="bulk" class="row hide" style="padding:0 20px 12px"><b class="small" id="bulkN"></b><button class="btn xs" id="bulkCmp" title="Pick 2 to 4 leads">${ic('chart', 14)} Compare</button><button class="btn xs" id="bulkPipe">${ic('plus', 14)} Add to pipeline</button><button class="btn xs" id="bulkOffer">${ic('letter', 14)} Draft offers</button><a class="btn xs" id="bulkCsv">${ic('download', 14)} Export CSV</a></div>
      <div style="overflow-x:auto"><table class="table" id="leadTable"><thead><tr>
        <th style="width:32px"><input type="checkbox" id="allChk" aria-label="Select all leads on this page"></th><th>Property</th><th class="hide-m">Owner</th><th class="r">Taxes Owed</th>
        <th class="r hide-m hide-xl">Years Behind</th><th class="r hide-m">Est. Value</th><th style="text-align:center">Deal Score</th><th class="hide-m">Actions</th>
      </tr></thead><tbody></tbody></table></div>
    </div>
    <div class="col gap16" style="gap:18px">
      <div class="card"><div class="card-head" style="padding-bottom:12px"><h3>Properties on Map</h3><a class="btn sm right" href="#/map">View Map</a></div><div class="mini-map" id="miniMap"></div></div>
      <div class="card"><div class="card-head" style="padding-bottom:12px"><h3>Today's alerts</h3><a class="btn sm right" href="#/alerts">View all</a></div><div id="todayAlerts"></div></div>
    </div>
  </div>`;

  const chosen = new Set();
  let leadRequest = 0;
  let totalLeads = 0;
  let totalPages = 1;
  const qs = () => {
    const o = { county: S.county, ...st };
    return Object.entries(o).filter(([, v]) => v !== '' && v != null).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');
  };
  async function loadStats() {
    const s = await api('/api/stats?county=' + S.county);
    const chg = (v, txt) => v == null ? `<div class="foot">${txt}</div>` : `<div class="foot"><span class="chg ${v < 0 ? 'down' : ''}" style="margin:0">${v < 0 ? '' : '+'}${v}%</span> ${txt}</div>`;
    $('#stats').innerHTML = [
      ['layers', 'tone-blue', 'Total leads', num(s.active), `<div class="foot">${s.homes != null && s.homes < s.active ? `${num(s.homes)} homes, ${num(s.active - s.homes)} land/other` : `In ${S.county === 'all' ? (s.counties === 1 ? 'your county' : `${s.counties} counties`) : esc(countyName(S.county) || 'this county')}`}</div>`, '#/deals'],
      ['doc', 'tone-green', 'New leads today', num(s.new_today), chg(s.new_change, 'vs. yesterday'), '#/deals'],
      ['star', 'tone-amber', 'High-score deals', num(s.high_score), chg(s.high_change, '80+ vs. last week'), '#/map'],
      ['house', 'tone-green', 'Avg equity', kmoney(s.avg_equity), '<div class="foot">Estimated per deal</div>', ''],
      ['map', 'tone-green', 'Counties tracked', num(s.counties), `<div class="foot">Across ${s.states} state${s.states === 1 ? '' : 's'}</div>`, '#/counties'],
    ].map(([i, t, l, v, f, href]) => `<a class="card stat" ${href ? `href="${href}"` : ''}><span class="ico ${t}">${ic(i, 21)}</span><div><div class="lbl">${l}</div><div class="val num">${v}</div>${f}</div></a>`).join('');
  }
  async function loadLeads() {
    const request = ++leadRequest;
    const r = await api('/api/parcels?' + qs());
    if (request !== leadRequest) return;
    totalLeads = r.total;
    const cn = S.county === 'all' ? 'all counties' : countyName(S.county);
    const active = [
      ['county', S.county !== 'all' && `County: ${cn}`],
      ['min_score', st.min_score && `Score ${st.min_score}+`],
      ['owed', (st.min_owed || st.max_owed) && (st.max_owed ? (st.min_owed && st.min_owed !== '0' ? `Taxes owed $${Number(st.min_owed).toLocaleString()}–$${Number(st.max_owed).toLocaleString()}` : `Taxes owed under $${Number(st.max_owed).toLocaleString()}`) : `Taxes owed over $${Number(st.min_owed).toLocaleString()}`)],
      ['min_years', st.min_years && `${st.min_years}+ years behind`],
      ['ptype', st.ptype === 'homes' ? 'Homes only' : st.ptype !== 'all' && `Property: ${st.ptype}`],
      ['min_equity', st.min_equity && `Equity $${Number(st.min_equity).toLocaleString()}+`],
      ['new_days', st.new_days && `New in ${st.new_days} days`],
      ['out_of_state', st.out_of_state && 'Out-of-state owners'],
      ['owner_status', st.owner_status && (st.owner_status === 'missing' ? 'Name missing' : 'Name available')],
      ['q', st.q && `Search: ${st.q}`],
    ].filter(([, label]) => label);
    const baseParams = new URLSearchParams(qs());
    for (const [key] of active) {
      if (key === 'county') continue;
      if (key === 'owed') { baseParams.delete('min_owed'); baseParams.delete('max_owed'); }
      else baseParams.delete(key);
    }
    baseParams.delete('ptype');
    baseParams.set('per', '1');
    const base = active.length ? await api('/api/parcels?' + baseParams) : r;
    if (request !== leadRequest) return;
    $('#leadSub').textContent = `${num(r.total)} matching leads in ${cn}${active.length ? ` · ${num(base.total)} total leads` : ''}`;
    $('#filterSummary').style.display = active.length ? 'block' : 'none';
    $('#filterChips').innerHTML = active.map(([key, label]) => `<span class="pill p-green applied-filter">${esc(label)}<button type="button" class="applied-filter-remove" data-filter="${esc(key)}" aria-label="Remove ${esc(label)} filter" title="Remove ${esc(label)} filter">${ic('x', 12)}</button></span>`).join('');
    $('#filterTotal').textContent = num(base.total);
    $('#filterMatching').textContent = num(r.total);
    $('#fMore').style.background = active.length ? '#DCFCE7' : '';
    const help = $('#ownerHelp');
    help.style.display = st.owner_status === 'missing' ? 'block' : 'none';
    help.textContent = st.owner_status === 'missing' ? 'Texas owner names are checked automatically against the official parcel map every 4 hours. If a name stays missing, open the lead, copy its parcel number, and search that county’s appraisal district records for the latest owner. Other states may use different county records.' : '';
    $('#pageInfo').textContent = r.total ? `${(r.page - 1) * r.per + 1} - ${Math.min(r.page * r.per, r.total)} of ${num(r.total)} leads` : '0 leads';
    totalPages = Math.max(1, Math.ceil(r.total / r.per));
    $('#pageNumber').value = String(r.page);
    $('#pageNumber').max = String(totalPages);
    $('#pageTotal').textContent = `/ ${num(totalPages)}`;
    $('#leadNumber').max = String(r.total || 1);
    $('#prev').disabled = r.page <= 1; $('#next').disabled = r.page * r.per >= r.total;
    $('#leadTable tbody').innerHTML = r.rows.map((p) => `<tr data-id="${esc(p.id)}">
      <td><input type="checkbox" class="chk" aria-label="Select ${esc(p.street || p.parcel_number || 'this lead')}" ${chosen.has(p.id) ? 'checked' : ''}></td>
      <td><div class="prop">${thumb(p)}<div><b>${esc(title(p.street) || 'Address not listed by county')}</b><span>${esc(place(p))}</span>${homeLine(p) ? `<span style="display:block;color:var(--ink2)">${homeLine(p)}</span>` : ''}</div></div></td>
      <td class="hide-m"><div style="max-width:150px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="${esc(title(p.owner_name))}">${p.locked ? `<span class="pill tiny" style="background:#F2F4F7;color:#475467">${ic('lock', 11)} Locked</span>` : esc(title(p.owner_name))}</div>${p.contact_status === 'found' ? ` <span class="pill p-green tiny">${ic('phone', 11)} Contact</span>` : p.contact_status === 'private' ? ' <span class="pill tiny" style="background:#EEE;color:#555">Private</span>' : ''}${p.mail_state && p.mail_state !== p.state ? ` <span class="pill p-amber tiny" style="padding:1px 7px">Out of state: ${esc(p.mail_state)}</span>` : ''}</td>
      <td class="r num">${money(p.total_due ?? p.amount_owed)}</td>
      <td class="r num hide-m hide-xl">${yrs(p.years_behind)}</td>
      <td class="r num hide-m">${money(p.appraised_total)}</td>
      <td style="text-align:center">${scorePill(p.score)}</td>
      <td class="hide-m"><div class="row gap4" style="flex-wrap:nowrap">${p.locked ? `<a class="btn sm" href="#/deal/${encodeURIComponent(p.id)}">${ic('lock', 13)} Reveal</a>` : `<a class="btn sm primary" href="#/deal/${encodeURIComponent(p.id)}?offer=1">Draft offer</a>`}<button class="icon-btn more" style="width:30px;height:30px">${ic('dots', 18)}</button></div></td></tr>`).join('') || `<tr><td colspan="8"><div class="empty">No leads match these filters.${S.meta.parcels ? '' : ' Add a county and run a sync, or load demo data in Settings.'}</div></td></tr>`;
  }
  async function loadSide() {
    const [pts, al] = await Promise.all([api(`/api/map?county=${S.county}&ptype=homes`), api('/api/alerts?limit=4&county=' + S.county)]);
    const L = window.L, mm = $('#miniMap');
    if (!mm || !document.body.contains(mm)) return;  // the user left the page while the map data was loading
    if (!mm._map) { mm._map = L.map(mm, { zoomControl: true, attributionControl: false, scrollWheelZoom: false }); baseTiles(mm._map); mm._layer = L.layerGroup().addTo(mm._map); }
    mm._layer.clearLayers();
    const top = pts.slice(0, 120);
    top.forEach((p) => pin(p).bindPopup(popupHtml(p)).addTo(mm._layer));
    mm._map.invalidateSize();
    fitMap(mm._map, top, S.county, top.length ? null : `No mapped properties in ${S.county === 'all' ? 'your counties' : countyName(S.county)} yet.`);
    $('#todayAlerts').innerHTML = al.rows.map((a) => `<a class="alert-row" href="${a.parcel_id ? '#/deal/' + encodeURIComponent(a.parcel_id) : '#/alerts'}">${alertIcon(a.type)}<div class="grow"><b>${esc(a.title)}</b><div class="tiny muted">${esc(a.county_name || '')}</div></div><span class="tiny muted">${ago(a.ts)}</span></a>`).join('') || '<div class="empty small">No alerts yet</div>';
  }
  const reload = () => { st.page = 1; loadLeads(); };
  $('#filterChips').onclick = (e) => {
    const button = e.target.closest('.applied-filter-remove');
    if (!button) return;
    const key = button.dataset.filter;
    if (key === 'county') { setCounty('all'); $('#countySel').value = 'all'; loadStats(); loadSide(); }
    else if (key === 'owed') { st.min_owed = ''; st.max_owed = ''; $('#fOwed').value = ''; }
    else if (key === 'ptype') st.ptype = 'all';
    else if (key === 'q') { st.q = ''; $('#leadQ').value = ''; clearTimeout(qt); }
    else if (key in st) st[key] = '';
    if (key === 'min_score') $('#fScore').value = '';
    if (key === 'min_years') $('#fYears').value = '';
    reload();
  };
  $('#countySel').onchange = (e) => { setCounty(e.target.value); loadStats(); reload(); loadSide(); };
  $('#fScore').onchange = (e) => { st.min_score = e.target.value; reload(); };
  $('#fOwed').onchange = (e) => { const [a, b] = (e.target.value || '-').split('-'); st.min_owed = a; st.max_owed = b; reload(); };
  $('#fYears').onchange = (e) => { st.min_years = e.target.value; reload(); };
  let qt; $('#leadQ').oninput = (e) => { clearTimeout(qt); qt = setTimeout(() => { st.q = e.target.value; reload(); }, 250); };
  $('#prev').onclick = () => { st.page--; loadLeads(); };
  $('#next').onclick = () => { st.page++; loadLeads(); };
  $('#leadJump').onsubmit = (e) => {
    e.preventDefault();
    const n = Number($('#leadNumber').value);
    if (!Number.isSafeInteger(n) || n < 1 || n > totalLeads) return toast(`Enter a lead number from 1 to ${num(totalLeads)}.`, true);
    st.page = Math.floor((n - 1) / st.per) + 1;
    loadLeads();
  };
  $('#pageJump').onsubmit = (e) => {
    e.preventDefault();
    const n = Number($('#pageNumber').value);
    if (!Number.isSafeInteger(n) || n < 1 || n > totalPages) return toast(`Enter a page from 1 to ${num(totalPages)}.`, true);
    st.page = n;
    loadLeads();
  };
  $('#fMore').onclick = () => modal(`<h2>More filters</h2><div style="height:14px"></div>
    <div class="field"><label>Property type</label><select class="select" id="mType"><option value="homes">Homes only (single + multi family)</option><option value="all">All property types</option><option>Vacant land</option><option>Commercial</option><option>Agricultural</option></select></div>
    <div class="field"><label>Minimum est. equity</label><select class="select" id="mEq"><option value="">Any</option><option value="30000">$30K+</option><option value="50000">$50K+</option><option value="100000">$100K+</option></select></div>
    <div class="field"><label>Newly delinquent</label><select class="select" id="mNew"><option value="">Any time</option><option value="1">Today</option><option value="7">Last 7 days</option><option value="30">Last 30 days</option></select></div>
    <label class="row" style="margin:6px 0 14px"><input type="checkbox" id="mOos"> Out-of-state owners only</label>
    <div class="field"><label>Owner name</label><select class="select" id="mOwner"><option value="">All leads</option><option value="available">Name available</option><option value="missing">Name missing</option></select></div>
    <div class="field"><label>Sort by</label><select class="select" id="mSort"><option value="score">Deal score</option><option value="newest">Newest first</option><option value="owed">Taxes owed</option><option value="equity">Est. equity</option><option value="years">Years behind</option></select></div>
    <div class="row" style="justify-content:flex-end"><button class="btn" data-close>Cancel</button><button class="btn primary" id="mApply">Apply</button></div>`, (m, close) => {
    $('#mType', m).value = st.ptype; $('#mEq', m).value = st.min_equity; $('#mNew', m).value = st.new_days; $('#mOos', m).checked = st.out_of_state === '1'; $('#mOwner', m).value = st.owner_status; $('#mSort', m).value = st.sort;
    $('#mApply', m).onclick = () => { st.ptype = $('#mType', m).value; st.min_equity = $('#mEq', m).value; st.new_days = $('#mNew', m).value; st.out_of_state = $('#mOos', m).checked ? '1' : ''; st.owner_status = $('#mOwner', m).value; st.sort = $('#mSort', m).value; close(); reload(); };
  });
  const tbody = $('#leadTable tbody');
  const updBulk = () => { $('#bulk').classList.toggle('hide', !chosen.size); $('#bulkN').textContent = `${chosen.size} selected`; $('#bulkCmp').disabled = chosen.size < 2 || chosen.size > 4; $('#bulkCsv').href = '/api/parcels/export.csv?' + qs(); };
  $('#bulkCsv').addEventListener('click', guardExportClick);
  tbody.onclick = (e) => {
    const tr = e.target.closest('tr[data-id]'); if (!tr) return;
    const id = tr.dataset.id;
    if (e.target.classList.contains('chk')) { e.target.checked ? chosen.add(id) : chosen.delete(id); updBulk(); return; }
    if (e.target.closest('a')) return;
    if (e.target.closest('.more')) {
      e.stopPropagation();
      return menu(e.target.closest('.more'), [
        { label: 'View deal', icon: 'house', fn: () => location.hash = '#/deal/' + encodeURIComponent(id) },
        { label: 'Add to pipeline', icon: 'plus', fn: async () => { await api(`/api/parcels/${encodeURIComponent(id)}/stage`, { method: 'POST', body: { stage: 'new' } }); toast('Added to Outreach > New lead'); } },
        { label: 'Open in Google Maps', icon: 'pin', fn: () => { const p = { lat: 0, lng: 0 }; api(`/api/parcels/${encodeURIComponent(id)}/detail`).then((d) => open(gmaps(d))); } },
      ]);
    }
    location.hash = '#/deal/' + encodeURIComponent(id);
  };
  $('#allChk').onchange = (e) => { $$('.chk', tbody).forEach((c) => { c.checked = e.target.checked; const id = c.closest('tr').dataset.id; e.target.checked ? chosen.add(id) : chosen.delete(id); }); updBulk(); };
  $('#bulkCmp').onclick = () => compareModal([...chosen]);
  $('#bulkPipe').onclick = async () => { for (const id of chosen) await api(`/api/parcels/${encodeURIComponent(id)}/stage`, { method: 'POST', body: { stage: 'new' } }); toast(`${chosen.size} leads added to Outreach`); chosen.clear(); updBulk(); loadLeads(); };
  $('#bulkOffer').onclick = async () => { const ids = [...chosen]; for (const id of ids) await api(`/api/parcels/${encodeURIComponent(id)}/stage`, { method: 'POST', body: { stage: 'new' } }); const r = await api('/api/batch-offers', { method: 'POST', body: { ids } }); toast(`${r.count} offer drafts created`); open('/letters?ids=' + encodeURIComponent(ids.join(','))); };
  $('#syncBtn').onclick = async () => {
    if (!S.meta.counties.length) return toast('Add a county first (Counties > Add county)', true);
    const r = await api('/api/sync', { method: 'POST', body: {} });
    if (!r.ok) return toast(r.error, true);
    toast('Sync started. You can keep working.');
    watchSync(() => { loadStats(); loadLeads(); loadSide(); });
  };
  if (S.meta.sync.running) watchSync(() => { loadStats(); loadLeads(); loadSide(); });
  // the side map and alerts are extras: if they fail, the leads table still shows
  await Promise.all([loadStats().catch(console.error), loadLeads(), loadSide().catch(console.error)]);
}

// ================================================================ DEAL DETAIL
export async function deal(el, [rawId]) {
  const [id, query] = (rawId || '').split('?');
  const p = await api(`/api/parcels/${encodeURIComponent(id)}/detail`);
  if (p.locked) return lockedDeal(el, p, rawId);
  p.contacts = p.contacts || [];
  const due = p.total_due ?? p.amount_owed;
  const outState = p.mail_state && p.mail_state !== p.state;
  const d = p.offer_defaults;
  const sugg = p.suggested_offer || 0;
  const hasStreet = /^\d+\b/.test(p.street || '');
  const propertyAddress = hasStreet ? title(p.street) : 'Address not listed by county';
  const label = p.score >= 85 ? 'High potential deal' : p.score >= 65 ? 'Good potential' : 'Lower priority';
  const stageLabel = (S.meta.stages.find((s) => s.key === p.stage) || {}).label;
  el.innerHTML = `
  <a class="small muted row gap6" href="#/deals" style="margin-bottom:12px">${ic('back', 15)} Back to Deals</a>
  <div class="page-head" style="margin-bottom:16px">
    <div><h1 style="font-size:28px">${esc(propertyAddress)}</h1><div class="sub" style="color:var(--ink2)">${[title(p.city), [p.state, p.zip].filter(Boolean).join(' ')].filter(Boolean).map(esc).join(', ')} · ${esc(p.county_name)}</div></div>
    <div class="row" style="margin-left:24px"><span class="pill p-green" style="padding:6px 8px 6px 14px;font-size:13px">Deal score ${scorePill(p.score)}</span>
      ${!p.is_active ? '<span class="pill p-grey">Paid / off list</span>' : ''}${stageLabel ? `<span class="pill p-blue">${esc(stageLabel)}</span>` : ''}</div>
    <div class="right">
      <a class="btn" id="reportBtn" href="/report/${encodeURIComponent(p.id)}" target="_blank" rel="noopener">${ic('doc', 16)} Report</a>
      <button class="btn" id="shareBtn">${ic('share', 16)} Share</button>
      ${(S.meta.team || []).length > 1 ? `<select class="select" id="assignSel" aria-label="Assigned to" style="width:auto"><option value="">Not assigned</option>${S.meta.team.map((u) => `<option value="${u.id}" ${u.id === p.assigned_to ? 'selected' : ''}>${esc(u.name || u.email)}</option>`).join('')}</select>` : ''}
      <button class="btn" id="listBtn">${ic('bookmark', 16)} ${p.stage ? 'In pipeline' : 'Add to list'}</button>
      <button class="btn" id="moreBtn" style="width:40px;padding:0">${ic('dots', 18)}</button>
    </div>
  </div>
  <div class="detail-grid">
    <div class="col" style="gap:18px;min-width:0">
      <div>
        <div class="gallery" id="gal">${p.lat ? `<span class="count" id="galCount">1 / ${p.photo_url ? 4 : 3}</span>` : ''}</div>
        <div class="gal-tabs">
          ${p.photo_url ? `<button data-v="county" style="background-image:url('${esc(p.photo_url)}')"><span>County aerial</span></button>` : ''}
          ${p.lat ? `<button class="on" data-v="sat" style="background-image:url('${tileUrl(p.lat, p.lng, 18)}')"><span>Satellite</span></button>
          <button data-v="map" style="background-image:url('${tileUrl(p.lat, p.lng, 16).replace("World_Imagery", "World_Street_Map")}')"><span>Street map</span></button>
          <button data-v="sv" style="background:#3E4A44"><span>Street View</span></button>` : ''}
        </div>
      </div>
      <div class="card card-pad"><h3 style="margin-bottom:6px">Property Details</h3>
        <div class="facts">
          ${fact('pin', 'Address', `${esc(propertyAddress)}<div class="small muted" style="font-weight:400">${[title(p.city), [p.state, p.zip].filter(Boolean).join(' ')].filter(Boolean).map(esc).join(', ')}</div>`)}
          ${fact('user', 'Owner', `${esc(title(p.owner_name || p.owner_full_name || 'Not listed'))}${outState ? `<div><span class="pill p-amber tiny" style="margin-top:4px">Out of state (${esc(p.mail_state)})</span></div>` : p.owner_occupied === 0 ? '<div><span class="pill p-grey tiny" style="margin-top:4px">Not owner-occupied</span></div>' : ''}`)}
          ${fact('house', 'Property type', `${esc(p.property_type || '--')}<div class="small muted" style="font-weight:400">${esc(title(p.land_use || ''))}</div>`)}
          ${fact('dollar', 'Taxes owed', money(due, 2))}
          ${fact('cal', 'Years behind', `${yrs(p.years_behind)} <span class="small muted" style="font-weight:400">${p.cert_year ? '(certified delinquent ' + p.cert_year + ')' : '(est.)'}</span>`)}
          ${fact('chart', 'Estimated value', `${money(p.appraised_total)} <span class="small muted" style="font-weight:400">county</span>`)}
          ${fact('trend', 'Estimated equity', money(p.est_equity))}
          ${fact('home', 'Rent estimate', p.rent_est ? money(p.rent_est) + ' / mo' : '--')}
          ${p.beds || p.year_built ? fact('house', 'Beds / Baths', `${p.beds ?? '--'} bd / ${p.baths_full ?? '--'}${p.baths_half ? '.5' : ''} ba<div class="small muted" style="font-weight:400">${p.living_area ? Number(p.living_area).toLocaleString() + ' sq ft' : ''}${p.stories ? ' · ' + p.stories + ' story' : ''}</div>`) : ''}
          ${p.year_built || p.condition ? fact('cal', 'Built / condition', `${p.year_built || '--'}<div class="small muted" style="font-weight:400">${esc(title(p.condition || ''))}${p.style ? ' · ' + esc(title(p.style.replace(/^\d+-/, ''))) : ''}</div>`) : ''}
          ${fact('mail', 'Tax bill mailed to', esc(title(p.mail_address || '--')))}
          ${fact('phone', 'Owner phone / email', `<div id="factContacts">${contactFact(p)}</div>`)}
          ${fact('doc', 'Parcel / acres', `${esc(p.parcel_number)}<div class="small muted" style="font-weight:400">${p.acres ?? '--'} acres · ${esc(p.county_name)}</div>`)}
        </div>
      </div>
      <div class="research-slot" id="compsResearch"></div>
    </div>
    <div class="col" style="gap:18px;min-width:0">
      <div class="card card-pad"><h3 style="margin-bottom:12px">Tax History</h3><div class="timeline">${taxTimeline(p)}</div>
        ${p.property_url ? `<a class="small" style="color:var(--green)" href="${esc(p.property_url)}" target="_blank" rel="noopener">Open county record ${ic('link', 13)}</a>` : ''}</div>
      ${dataCard(p.data_check, false)}
      <div class="card card-pad"><div class="row between"><h3>Why this score?</h3>${p.ai ? `<button class="btn xs" id="aiWhy">${ic('sparkle', 13)} Explain with AI</button>` : ''}</div>
        <div class="big-score">${scorePill(p.score)}<div><b style="color:${p.score >= 85 ? 'var(--green-ink)' : 'var(--ink)'}">${label}</b><div class="tiny muted">Based on your scoring weights</div></div></div>
        <div id="reasons">${reasonsHtml(p.reasons)}</div>
        <div class="breakdown" style="margin-top:10px;border-top:1px solid var(--line);padding-top:10px">${Object.entries(p.score_parts || {}).map(([k, v]) => {
          const w = S.meta.settings.weights[k] || 1;
          return `<div class="b-row"><span class="muted">${esc({ years_behind: 'Years behind', equity: 'Equity', amount_owed: 'Amount owed', out_of_state: 'Out-of-state owner', vacancy: 'Vacancy signals' }[k])}</span><div class="b-bar"><i style="width:${Math.min(100, v / w * 100)}%"></i></div><b class="num" style="text-align:right">+${Math.round(v)}/${w}</b></div>`;
        }).join('')}</div>${SCORE_NOTE}</div>
      <div class="research-slot" id="floodResearch"></div>
    </div>
    <div class="col col3" style="gap:18px;min-width:0">
      <div class="card card-pad" id="offerCard"></div>
      <div class="card card-pad" id="contactsCard"></div>
      <div class="card card-pad"><div class="row between" style="margin-bottom:6px"><h3>Activity Notes</h3><div class="row gap6"><button class="btn xs" id="addTask">${ic('clock', 13)} Follow-up</button><button class="btn xs" id="addNote">Add note</button></div></div>
        <div id="acts"></div></div>
      <div class="research-slot" id="rulesResearch"></div>
    </div>
  </div>
  <div class="mobile-actions"><button class="btn primary" id="mOffer">${ic('mail', 16)} Send offer</button><div class="row"><a class="btn grow" id="mCall">${ic('phone', 16)} Call owner</a><button class="btn grow" id="mSave">${ic('bookmark', 16)} Save deal</button></div></div>`;

  loadResearch(p, { comps: $('#compsResearch'), flood: $('#floodResearch'), rules: $('#rulesResearch') });
  if ($('#assignSel')) $('#assignSel').onchange = async (e) => {
    try { await api(`/api/parcels/${encodeURIComponent(p.id)}/assign`, { method: 'POST', body: { user_id: e.target.value ? +e.target.value : null } }); toast(e.target.value ? 'Lead assigned.' : 'Lead unassigned.'); }
    catch (err) { toast(err.message, true); }
  };
  // gallery
  const L = window.L, g = $('#gal');
  const gm = L.map(g, { zoomControl: false, attributionControl: false, scrollWheelZoom: false }).setView([p.lat || 40, p.lng || -82], p.lat ? 18 : 6);
  let layer = baseTiles(gm, 'sat');
  if (p.lat) pin(p, true).addTo(gm);
  const nTabs = $$('.gal-tabs button').length;
  const photoBox = document.createElement('div');
  photoBox.style.cssText = `position:absolute;inset:0;z-index:450;background:#1d2420 url('${(p.photo_url || '').replace(/'/g, '')}') center/contain no-repeat;display:none`;
  g.append(photoBox);
  const showMsg = !p.lat && !p.photo_url;
  if (showMsg) { const m = document.createElement('div'); m.className = 'map-unavailable'; m.innerHTML = `<div>${ic('pin', 24)}<b>Map location unavailable</b><span>${hasStreet ? 'We could not verify this address on the map.' : 'The county record has no usable street address or coordinates.'}</span>${p.property_url ? `<a class="btn sm" href="${esc(p.property_url)}" target="_blank" rel="noopener">Open county record ${ic('link', 13)}</a>` : `<span>Check parcel ${esc(p.parcel_number || '')} with the county assessor.</span>`}</div>`; g.append(m); }
  $$('.gal-tabs button').forEach((b, i) => b.onclick = () => {
    if (b.dataset.v === 'sv') return p.lat ? open(streetView(p), '_blank') : open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(p.street + ', ' + p.city + ' ' + p.state + ' ' + p.zip)}`, '_blank');
    $$('.gal-tabs button').forEach((x) => x.classList.toggle('on', x === b));
    photoBox.style.display = b.dataset.v === 'county' ? 'block' : 'none';
    if (b.dataset.v !== 'county') { gm.removeLayer(layer); layer = baseTiles(gm, b.dataset.v === 'sat' ? 'sat' : 'light'); gm.setZoom(b.dataset.v === 'sat' ? 18 : 16); }
    if ($('#galCount')) $('#galCount').textContent = `${i + 1} / ${nTabs}`;
  });
  if (p.photo_url) $('.gal-tabs button[data-v=county]').click();
  // full-screen map: bigger, drag, scroll to zoom, switch satellite / street map, Esc or the button to close
  if (p.lat) {
    L.control.zoom({ position: 'bottomright' }).addTo(gm);
    const fsBtn = document.createElement('button');
    fsBtn.className = 'gal-fs'; fsBtn.type = 'button';
    const setFsBtn = (on) => { fsBtn.innerHTML = on ? ic('x', 18) : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>';
      fsBtn.setAttribute('aria-label', on ? 'Close full screen map' : 'Open map full screen'); fsBtn.title = on ? 'Close full screen (Esc)' : 'Full screen map'; };
    setFsBtn(false);
    const sw = document.createElement('div');
    sw.className = 'gal-switch';
    sw.innerHTML = '<button type="button" data-l="sat" class="on">Satellite</button><button type="button" data-l="light">Map</button>';
    g.append(fsBtn, sw);
    L.DomEvent.disableClickPropagation(fsBtn); L.DomEvent.disableClickPropagation(sw);
    sw.onclick = (e) => { const b = e.target.closest('[data-l]'); if (!b) return; $$('button', sw).forEach((x) => x.classList.toggle('on', x === b)); photoBox.style.display = 'none'; gm.removeLayer(layer); layer = baseTiles(gm, b.dataset.l); };
    let full = false;
    const onKey = (e) => { if (e.key === 'Escape' && full) toggle(false); };
    const toggle = (on) => {
      full = on;
      g.classList.toggle('gal-full', on); document.body.classList.toggle('no-scroll', on); setFsBtn(on);
      if (on) { photoBox.style.display = 'none'; gm.scrollWheelZoom.enable(); document.addEventListener('keydown', onKey); fsBtn.focus(); }
      else { gm.scrollWheelZoom.disable(); document.removeEventListener('keydown', onKey); }
      setTimeout(() => { gm.invalidateSize(); gm.panTo([p.lat, p.lng]); }, 60);
    };
    fsBtn.onclick = () => toggle(!full);
    window.addEventListener('hashchange', () => { if (full) toggle(false); }, { once: true });
  }

  // header buttons
  $('#shareBtn').onclick = async () => { await navigator.clipboard?.writeText(location.href).catch(() => { }); toast('Link copied'); };
  $('#listBtn').onclick = async () => { if (!p.stage) { await api(`/api/parcels/${encodeURIComponent(id)}/stage`, { method: 'POST', body: { stage: 'new' } }); toast('Added to Outreach > New lead'); deal(el, [rawId]); } else location.hash = '#/outreach'; };
  $('#mSave').onclick = $('#listBtn').onclick;
  $('#moreBtn').onclick = (e) => { e.stopPropagation(); menu($('#moreBtn'), [
    ...S.meta.stages.map((s) => ({ label: 'Move to ' + s.label, icon: 'right', fn: () => moveStage(s.key) })),
    '-', ...(p.lat || hasStreet ? [{ label: 'Open in Google Maps', icon: 'pin', fn: () => open(gmaps(p)) }] : []),
    ...(p.stage ? [{ label: 'Remove from pipeline', icon: 'x', danger: true, fn: () => moveStage('remove') }] : []),
  ]); };
  async function moveStage(stage) {
    let fee;
    if (stage === 'closed') { fee = await askFee(); if (fee == null) return; }
    await api(`/api/parcels/${encodeURIComponent(id)}/stage`, { method: 'POST', body: { stage, fee: fee ? +fee : null } });
    toast(stage === 'remove' ? 'Removed from pipeline' : 'Stage updated'); deal(el, [rawId]);
  }
  if ($('#aiWhy')) $('#aiWhy').onclick = async () => {
    $('#aiWhy').disabled = true; $('#aiWhy').textContent = 'Thinking...';
    try { const r = await api(`/api/parcels/${encodeURIComponent(id)}/ai-reasons`); $('#reasons').innerHTML = reasonsHtml(r.reasons); } catch (e) { toast(e.message, true); }
    $('#aiWhy').remove();
  };

  // offer card
  let offer = p.offers[0];
  function renderOffer(editing = false) {
    const oc = $('#offerCard');
    oc.innerHTML = `<div class="row between" style="gap:10px;margin-bottom:12px;flex-wrap:wrap"><h3>Offer Draft</h3><a class="small" href="/deal-profit-calculator" style="color:var(--green);font-weight:600">Free profit calculator ↗</a></div>
      <div class="offer-top"><div class="sugg"><div class="tiny muted">${hasStreet ? 'Suggested offer' : 'Unverified offer estimate'}</div><b class="num">${money(offer?.price ?? sugg)}</b></div>
        <div title="${esc(money(p.est_equity))}"><div class="tiny muted">Est. equity</div><b class="num">${kmoney(p.est_equity)}</b></div><div title="${esc(money(p.appraised_total))}"><div class="tiny muted">Est. value</div><b class="num">${kmoney(p.appraised_total)}</b></div></div>
      ${!hasStreet ? '<p class="small muted" style="margin:10px 0 0">Confirm the parcel and county value before using this estimate in an offer.</p>' : ''}
      <details ${offer ? '' : 'open'} style="margin:14px 0 4px"><summary class="small" style="cursor:pointer;font-weight:600;color:var(--ink2)">Offer terms</summary>
        <div class="terms" style="margin-top:10px">
          <div class="field"><label>Offer price</label><input class="input num" id="oPrice" value="${Math.round(offer?.price ?? sugg)}"></div>
          <div class="field"><label>Financing</label><select class="select" id="oFin">${['Cash', 'DSCR loan (80% LTV)', 'Conventional loan', 'Hard money', 'Seller financing'].map((f) => `<option ${f === (offer?.financing || d.financing) ? 'selected' : ''}>${f}</option>`).join('')}</select></div>
          <div class="field"><label>Closing (days)</label><input class="input" id="oDays" value="${offer?.closing_days || d.closing_days}"></div>
          <div class="field"><label>Earnest money</label><input class="input" id="oEarnest" value="${offer?.earnest || d.earnest}"></div>
        </div>
        <div class="field"><label>Seller credits</label><input class="input" id="oCredits" value="${esc(offer?.seller_credits || d.seller_credits)}"></div>
        <button class="btn sm" id="oGen">${ic('sparkle', 14)} ${offer ? 'Re-draft' : 'Draft offer'}${p.ai ? ' with AI' : ''}</button>
      </details>
      ${offer ? `<div class="small" style="margin:12px 0 8px"><b>Subject:</b> <span id="oSubj">${esc(offer.subject)}</span></div>
        ${editing ? `<input class="input" id="eSubj" style="width:100%;margin-bottom:8px" value="${esc(offer.subject)}"><textarea class="input" id="eBody" rows="14" style="width:100%">${esc(offer.body)}</textarea>`
          : `<div class="email-box" id="oBody">${esc(offer.body)}</div>`}
        <div class="tiny muted" style="margin:6px 0 12px">Drafted ${ago(offer.created)} · ${esc(offer.source)}</div>
        <div class="row wrap">
          <button class="btn sm" id="oCopy">${ic('copy', 15)} Copy</button>
          ${editing ? `<button class="btn sm" id="oSave">${ic('check', 15)} Save</button>` : `<button class="btn sm" id="oEdit">${ic('edit', 15)} Edit</button>`}
          <a class="btn sm" href="/letters?ids=${encodeURIComponent(id)}" target="_blank">${ic('print', 15)} Letter</a>
          <button class="btn sm primary" style="flex-basis:100%" id="oSent">${ic('send', 15)} Mark as contacted</button>
        </div>
        <div class="tiny muted" style="margin-top:8px">Tax bill address: ${esc(title(p.mail_address || 'n/a'))}. Owner phone/email needs skip tracing.</div>` : `<div class="empty small" style="padding:18px 0 4px">Set the terms and click Draft offer.</div>`}`;
    $('#oGen').onclick = async () => {
      $('#oGen').disabled = true; $('#oGen').textContent = 'Drafting...';
      try {
        offer = await api(`/api/parcels/${encodeURIComponent(id)}/offer`, { method: 'POST', body: { price: +$('#oPrice').value.replace(/[^0-9.]/g, ''), financing: $('#oFin').value, closing_days: +$('#oDays').value, earnest: +$('#oEarnest').value.replace(/[^0-9.]/g, ''), seller_credits: $('#oCredits').value } });
        toast('Offer drafted'); renderOffer();
      } catch (e) { toast(e.message, true); renderOffer(); }
    };
    if (!offer) return;
    $('#oCopy').onclick = async () => { await navigator.clipboard?.writeText(`Subject: ${offer.subject}\n\n${offer.body}`).catch(() => { }); toast('Email copied'); };
    if ($('#oEdit')) $('#oEdit').onclick = () => renderOffer(true);
    if ($('#oSave')) $('#oSave').onclick = async () => { offer = await api('/api/offers/' + offer.id, { method: 'PUT', body: { subject: $('#eSubj').value, body: $('#eBody').value } }); toast('Saved'); renderOffer(); };
    $('#oSent').onclick = () => modal(`<h2>Mark as contacted</h2><p class="muted small">How did you send it?</p>
      <div class="row wrap" style="margin:12px 0 18px">${['email', 'letter', 'sms', 'call'].map((k, i) => `<label class="chip-btn ${i === 1 ? 'on' : ''}"><input type="radio" name="via" value="${k}" ${i === 1 ? 'checked' : ''} style="display:none">${ic({ email: 'mail', letter: 'letter', sms: 'sms', call: 'phone' }[k], 15)} ${title(k)}</label>`).join('')}</div>
      <div class="row" style="justify-content:flex-end"><button class="btn" data-close>Cancel</button><button class="btn primary" id="cOk">Save</button></div>`, (m, close) => {
      $$('label.chip-btn', m).forEach((l) => l.onclick = () => { $$('label.chip-btn', m).forEach((x) => x.classList.remove('on')); l.classList.add('on'); });
      $('#cOk', m).onclick = async () => {
        const via = $('input[name=via]:checked', m).value;
        await api(`/api/parcels/${encodeURIComponent(id)}/activity`, { method: 'POST', body: { kind: via, text: `Offer sent (${money(offer.price)}) by ${via}` } });
        close(); toast('Moved to Contacted'); deal(el, [rawId]);
      };
    });
  }
  renderOffer();
  $('#mOffer').onclick = () => { $('#offerCard').scrollIntoView({ behavior: 'smooth' }); };
  $('#mCall').onclick = () => modal(`<h2>Call owner</h2><p class="muted">County records do not include phone numbers. Use a skip tracing service with the mailing address below, then log the call here.</p>
    <div class="card card-pad small">${esc(title(p.owner_name || p.owner_full_name || 'Not listed'))}<br>${esc(title(p.mail_address || ''))}</div>
    <div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-close>Close</button><button class="btn primary" id="logCall">Log a call</button></div>`, (m, close) => {
    $('#logCall', m).onclick = async () => { await api(`/api/parcels/${encodeURIComponent(id)}/activity`, { method: 'POST', body: { kind: 'call', text: 'Called owner' } }); close(); deal(el, [rawId]); };
  });

  // County records do not include phone/email. Search with Gemini when configured;
  // otherwise let the user search and paste results without installing an extension.
  let lastSrc = 'Manual';
  const contactSource = (source) => (source || 'Public source').replace(/^Gemini:\s*/i, '').replace(/^Gemini search$/i, 'Public search');
  const renderContacts = (list, msg = '') => {
    const o = ownerInfo(p);
    if (list.length) p.contact_status = 'found';
    if ($('#factContacts')) $('#factContacts').innerHTML = contactFact(p);
    const row = (c) => `<div class="contact"><span class="ico ${c.kind === 'phone' ? 'tone-green' : 'tone-blue'}">${ic(c.kind === 'phone' ? 'phone' : 'mail', 15)}</span>
      <div class="grow" style="min-width:0"><a href="${c.kind === 'phone' ? 'tel:+1' + esc(c.norm) : 'mailto:' + esc(c.value)}"><b>${esc(c.value)}</b></a>
      <div class="tiny muted">${c.kind === 'phone' ? 'Phone' : 'Email'}${/\bold\b/i.test(c.note || '') ? ' · May be outdated' : ''}</div>
      ${c.sources.length || c.note ? `<details class="contact-details"><summary>View details</summary>${c.sources.length ? `<div><b>Found on:</b> ${c.sources.map((x) => esc(contactSource(x))).join(', ')}</div>` : ''}${c.note ? `<div>${esc(c.note)}</div>` : ''}</details>` : ''}</div>
      <button class="btn xs ghost" data-cdel="${c.id}" title="Remove">${ic('x', 13)}</button></div>`;
    $('#contactsCard').innerHTML = `<div class="row between" style="margin-bottom:4px"><h3>Owner Contacts</h3></div>
      <button class="btn primary" id="cSee" style="width:100%;margin:6px 0 10px">${ic(p.ai ? 'sparkle' : 'link', 15)} ${p.ai ? 'Find owner contact' : 'Search owner on Google'}</button>
      <div class="small muted" style="margin-bottom:10px">${o.name ? `${esc(o.name)} · ${esc(o.city)}, ${esc(o.st)}` : 'Owner name is missing from this county record.'}</div>
      ${msg ? `<div class="small" style="background:var(--bg2,#F4F5F1);border-radius:8px;padding:8px 10px;margin-bottom:10px">${msg}</div>` : ''}
      <div id="cList">${list.map(row).join('') || '<div class="empty small" style="padding:10px">No phone or email yet</div>'}</div>
      <div class="small muted" style="margin:12px 0 6px">Found a contact elsewhere?</div>
      <div class="row wrap gap6">${p.ai ? lookupLinks(p).map(([n, u]) => `<button class="btn xs" data-lookup="${esc(u)}">Search ${n}</button>`).join('') : ''}<button class="btn xs" id="cClip">Paste copied info</button><button class="btn xs ghost" id="cPaste">Enter manually</button></div>`;
    $$('[data-lookup]', $('#contactsCard')).forEach((b) => b.onclick = () => { lastSrc = b.textContent.trim(); window.open(b.dataset.lookup, '_blank', 'noopener'); });
    $('#cSee').onclick = async () => {
      if (!o.name) {
        renderContacts(p.contacts, 'This county record has no owner name yet. Open the county property record under Data sources to identify the owner first.');
        return;
      }
      if (!p.ai) {
        lastSrc = 'Google';
        window.open(lookupLinks(p)[0][1], '_blank', 'noopener');
        renderContacts(p.contacts, 'Google search opened. Copy a relevant phone or email, then use Paste from clipboard here.');
        return;
      }
      const b = $('#cSee'); b.disabled = true; b.textContent = 'Searching public sources...';
      try {
        const r = await api(`/api/parcels/${encodeURIComponent(id)}/contacts/ai`, { method: 'POST', body: o });
        p.contacts = r.contacts;
        if (!r.contacts.length && r.searched?.length) { p.contact_status = 'private'; p.contact_checked = new Date().toISOString(); }
        renderContacts(p.contacts, r.added ? `${r.added} contact ${r.added === 1 ? 'detail' : 'details'} found. Check before calling.` : 'No public contact found. You can search manually below.');
      } catch (e) {
        renderContacts(p.contacts, 'Search is unavailable right now. Try again, or search Google and paste a result below.');
      }
    };
    $('#cClip').onclick = async () => {
      let text = '';
      try { text = await navigator.clipboard.readText(); } catch (e) { toast('Allow clipboard access, or use Type / paste manually'); return; }
      const r = await api(`/api/parcels/${encodeURIComponent(id)}/contacts`, { method: 'POST', body: { text, source: lastSrc } });
      p.contacts = r.contacts; renderContacts(p.contacts, r.found.length ? `Saved ${r.found.length} phone/email from ${esc(lastSrc)}.` : 'No phone number or email found in the copied text.');
    };
    $$('[data-cdel]').forEach((b) => b.onclick = async () => { await api('/api/contacts/' + b.dataset.cdel, { method: 'DELETE' }); p.contacts = p.contacts.filter((c) => c.id != b.dataset.cdel); renderContacts(p.contacts); });
    $('#cPaste').onclick = () => modal(`<h2>Paste found info</h2><p class="muted small">Copy the phone numbers and emails from the people-search page and paste them here. Every number and email in the text is saved; duplicates are merged.</p>
      <div class="field"><label>Found on</label><select class="select" id="cSrc"><option>Google</option><option>Facebook</option><option>County records</option><option>Phone call</option><option>Other</option></select></div>
      <textarea class="input" id="cText" rows="6" style="width:100%" placeholder="(330) 555-0142 Wireless&#10;jdoe@example.com"></textarea>
      <div class="row" style="justify-content:flex-end;margin-top:14px"><button class="btn" data-close>Cancel</button><button class="btn primary" id="cSave">Save</button></div>`, (m, close) => {
      $('#cSave', m).onclick = async () => {
        const r = await api(`/api/parcels/${encodeURIComponent(id)}/contacts`, { method: 'POST', body: { text: $('#cText', m).value, source: $('#cSrc', m).value } });
        close(); p.contacts = r.contacts; renderContacts(p.contacts, r.found.length ? `Saved ${r.found.length} item(s).` : 'No phone number or email found in that text.');
      };
    });
  };
  renderContacts(p.contacts);

  // activities + tasks
  const actIcon = { email: ['mail', 'tone-blue'], letter: ['letter', 'tone-blue'], sms: ['sms', 'tone-blue'], call: ['phone', 'tone-green'], reply: ['sms', 'tone-green'], stage: ['right', 'tone-grey'], note: ['note', 'tone-amber'] };
  const activityText = (a) => /^(Gemini contact search|Google AI Overview):/i.test(a.text || '') ? 'Contact search completed' : a.text;
  $('#acts').innerHTML = [...p.tasks.filter((t) => !t.done).map((t) => `<div class="act"><span class="ico tone-amber">${ic('clock', 16)}</span><div class="grow"><div>${esc(t.text)}</div><div class="tiny muted">Due ${fmtDate(t.due)}</div></div><input type="checkbox" data-task="${t.id}"></div>`),
    ...p.activities.map((a) => { const [i, t] = actIcon[a.kind] || ['note', 'tone-grey']; return `<div class="act"><span class="ico ${t}">${ic(i, 16)}</span><div class="grow"><div>${esc(activityText(a))}</div><div class="tiny muted">${fmtDate(a.ts, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })}</div></div><span class="tiny muted">${/^(Gemini contact search|Google AI Overview):/i.test(a.text || '') ? 'Contact search' : esc(a.author || '')}</span></div>`; })]
    .join('') || '<div class="empty small" style="padding:16px">No activity yet</div>';
  $$('[data-task]').forEach((c) => c.onchange = async () => { await api('/api/tasks/' + c.dataset.task, { method: 'PUT', body: { done: true } }); deal(el, [rawId]); });
  $('#addNote').onclick = () => modal(`<h2>Add note</h2><div style="height:12px"></div><div class="field"><label>Type</label><select class="select" id="nKind"><option value="note">Note</option><option value="call">Call</option><option value="email">Email sent</option><option value="sms">SMS sent</option><option value="letter">Letter mailed</option><option value="reply">Owner replied</option></select></div>
    <textarea class="input" id="nText" rows="4" style="width:100%" placeholder="What happened?"></textarea>
    <div class="row" style="justify-content:flex-end;margin-top:14px"><button class="btn" data-close>Cancel</button><button class="btn primary" id="nSave">Save</button></div>`, (m, close) => {
    $('#nSave', m).onclick = async () => { await api(`/api/parcels/${encodeURIComponent(id)}/activity`, { method: 'POST', body: { kind: $('#nKind', m).value, text: $('#nText', m).value || $('#nKind', m).selectedOptions[0].text } }); close(); deal(el, [rawId]); };
  });
  $('#addTask').onclick = () => taskModal(id, () => deal(el, [rawId]));
  if ((query || '').includes('offer=1') && !offer) setTimeout(() => $('#offerCard').scrollIntoView({ behavior: 'smooth', block: 'center' }), 200);
  return () => gm.remove();
}

// free trial: a lead not yet revealed shows the money and the score, but not who or where
function lockedDeal(el, p, rawId) {
  const due = p.total_due ?? p.amount_owed;
  const left = p.reveals_left ?? 0;
  el.innerHTML = `<a class="small muted" href="#/deals">${ic('back', 14)} Back to Deals</a>
  <div class="row between" style="margin:10px 0 16px;flex-wrap:wrap;gap:10px"><div><h1 style="font-size:26px">${ic('lock', 22)} Locked lead</h1>
    <div class="sub">${esc([title(p.city || ''), p.state, p.zip].filter(Boolean).join(' '))} · ${esc(p.county_name)}</div></div>${scorePill(p.score)}</div>
  <div class="card card-pad" style="border:2px solid var(--green);margin-bottom:18px">
    <h3>See the owner, address and contacts</h3>
    <p class="muted small" style="margin:6px 0 12px">Your free trial can open ${p.reveals_total} leads in full. You have <b>${left}</b> left. Paid plans open every lead and let you draft offers, export and print letters.</p>
    <div class="row gap6"><button class="btn primary" id="revealBtn" ${left > 0 ? '' : 'disabled'}>${ic('lock', 14)} Reveal this lead${left > 0 ? ` (${left} left)` : ''}</button><button class="btn" id="seePlans">See plans</button></div></div>
  <div class="grid-2" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px">
    <div class="card card-pad"><h3 style="margin-bottom:10px">What we know</h3><div class="facts">
      ${fact('dollar', 'Taxes owed', money(due, 2))}
      ${fact('cal', 'Years behind', `${yrs(p.years_behind)}`)}
      ${fact('chart', 'Estimated value', money(p.appraised_total))}
      ${fact('trend', 'Estimated equity', money(p.est_equity))}
      ${fact('house', 'Property type', esc(p.property_type || '--'))}
      ${fact('home', 'Beds / built', `${p.beds ?? '--'} bd · ${p.year_built || '--'}`)}
      ${fact('user', 'Owner', `<span class="pill tiny" style="background:#F2F4F7;color:#475467">${ic('lock', 11)} Hidden</span>`)}
      ${fact('pin', 'Address', `<span class="pill tiny" style="background:#F2F4F7;color:#475467">${ic('lock', 11)} Hidden</span>`)}
    </div></div>
    <div class="card card-pad"><h3>Why this score?</h3><div id="reasons" style="margin-top:8px">${reasonsHtml(p.reasons)}</div>${SCORE_NOTE}</div>
    ${dataCard(p.data_check, true)}
    <div class="col" id="lockedResearch" style="gap:18px"></div>
  </div>`;
  lockedResearch(p, $('#lockedResearch'));
  $('#seePlans').onclick = () => plansModal();
  $('#revealBtn').onclick = async () => {
    $('#revealBtn').disabled = true;
    try { await api(`/api/parcels/${encodeURIComponent(p.id)}/reveal`, { method: 'POST' }); await refreshMeta(); deal(el, [rawId]); }
    catch (e) { toast(e.message, true); plansModal(e.message); }
  };
}

export function taskModal(parcelId, done) {
  const t = new Date(); const iso = (d) => d.toISOString().slice(0, 10);
  modal(`<h2>Add follow-up</h2><div style="height:12px"></div>
    <div class="field"><label>What</label><input class="input" id="tText" value="Call back owner"></div>
    <div class="terms"><div class="field"><label>Type</label><select class="select" id="tKind"><option value="call">Call</option><option value="email">Email</option><option value="sms">SMS</option><option value="letter">Letter</option></select></div>
    <div class="field"><label>Due</label><input class="input" type="date" id="tDue" value="${iso(new Date(t.getTime() + 864e5))}"></div></div>
    <div class="row" style="justify-content:flex-end"><button class="btn" data-close>Cancel</button><button class="btn primary" id="tSave">Add</button></div>`, (m, close) => {
    $('#tSave', m).onclick = async () => { await api('/api/tasks', { method: 'POST', body: { parcel_id: parcelId, text: $('#tText', m).value, kind: $('#tKind', m).value, due: $('#tDue', m).value } }); close(); toast('Follow-up added'); done && done(); };
  });
}

function ownerInfo(p) {
  // owner name is "LAST FIRST ..." in county data; mailing city/state is where the owner lives
  const parts = (p.owner_name || p.owner_full_name || '').replace(/&.*/, '').trim().split(/\s+/).slice(0, 2).reverse().join(' ');
  const company = /\b(LLC|INC|CORP|CO|LTD|TRUST|BANK|CHURCH|PROPERTIES|HOLDINGS|INVESTMENTS?)\b/i.test(p.owner_name || '');
  const name = company ? title((p.owner_name || '').replace(/&.*/, '').trim()) : title(parts.replace(/\b(ETAL|ET AL|TRUSTEE|TR)\b/gi, '').trim());
  const m = (p.mail_address || '').match(/,\s*([^,]+?)\s+([A-Z]{2})\s+\d{5}/);
  const city = m ? title(m[1].split(',').pop().trim()) : title(p.city || '');
  const st = m ? m[2] : p.state || 'OH';
  return { name, city, st };
}

function lookupLinks(p) {
  const { name, city, st } = ownerInfo(p);
  const q = encodeURIComponent;
  return [
    ['Google', `https://www.google.com/search?q=${q('"' + name + '" ' + city + ' ' + st + ' phone')}`],
  ];
}

function contactFact(p) {
  const list = p.contacts || [];
  if (list.length) return list.slice(0, 6).map((c) => `<div style="margin-bottom:3px"><a style="color:var(--ink)" href="${c.kind === 'phone' ? 'tel:+1' + esc(c.norm) : 'mailto:' + esc(c.value)}">${esc(c.value)}</a>
    ${/\bold\b/i.test(c.note || '') ? '<span class="tiny muted"> · May be outdated</span>' : ''}</div>`).join('')
    + (list.length > 6 ? `<div class="tiny muted">+${list.length - 6} more in Owner Contacts</div>` : '');
  if (p.contact_status === 'private') return '<span class="small muted" style="font-weight:400">No public contact found yet.</span>';
  return '<span class="small muted" style="font-weight:400">Not searched yet. Use the owner contact button below to search public sources.</span>';
}

function fact(i, k, v) { return `<div class="fact">${ic(i, 17)}<div><div class="k">${k}</div><div class="v">${v}</div></div></div>`; }

// "Data sources" card: where the lead came from, how fresh it is, what the county left out, what is an estimate
const CHECK = { verified: ['p-green', 'check', 'Verified'], partial: ['p-amber', 'alert', 'Partly verified'], conflict: ['p-red', 'alert', 'Amounts differ'],
  stale: ['p-amber', 'clock', 'Not on latest list'], removed: ['p-grey', 'clock', 'Off the county list'] };
function dataCard(dc, locked) {
  if (!dc) return '';
  const [tone, icn, word] = CHECK[dc.status] || CHECK.partial;
  const row = (k, v) => `<div class="row between data-row"><span class="small muted">${k}</span><span class="small" style="text-align:right">${v}</span></div>`;
  const d = (x) => x ? fmtDate(x, { month: 'short', day: 'numeric', year: 'numeric' }) : '--';
  return `<div class="card card-pad" id="dataCard"><div class="row between"><h3>Data sources</h3><span class="pill ${tone} tiny">${ic(icn, 12)} ${word}</span></div>
    <p class="small muted" style="margin:8px 0 10px">${esc(dc.note)}</p>
    ${row('Source', dc.list_url ? `<a href="${esc(dc.list_url)}" target="_blank" rel="noopener" style="color:var(--green)">${esc(dc.source)} ${ic('link', 12)}</a>` : esc(dc.source))}
    ${dc.record_url ? row('County property record', `<a href="${esc(dc.record_url)}" target="_blank" rel="noopener" style="color:var(--green)">Open record ${ic('link', 12)}</a>`) : locked ? row('County property record', '<span class="muted">Shown after you open this lead</span>') : ''}
    ${dc.owner_source && !locked ? row('Owner name source', `<a href="https://geographic.texas.gov/stratmap/land-parcels" target="_blank" rel="noopener" style="color:var(--green)">${esc(dc.owner_source)} ${ic('link', 12)}</a>`) : ''}
    ${row('First on the list', d(dc.first_seen))}
    ${row('Last confirmed on the list', d(dc.last_seen))}
    ${dc.record_read ? row('Property record read', d(dc.record_read)) : ''}
    ${row('County last downloaded', dc.county_last_sync ? `${d(dc.county_last_sync)} <span class="muted">(${ago(dc.county_last_sync)})</span>` : '--')}
    ${dc.amount_record ? row('Amount: list / county record', `${money(dc.amount_list, 2)} / ${money(dc.amount_record, 2)}${dc.amount_differs ? ` <span class="pill p-red tiny">differ</span>` : ` <span class="pill p-green tiny">match</span>`}`) : ''}
    ${dc.missing.length ? row('Missing from source', esc(dc.missing.join(', '))) : ''}
    ${dc.estimates.length ? row('Estimates, not county facts', esc(dc.estimates.join(', '))) : ''}
  </div>`;
}
const SCORE_NOTE = '<p class="tiny muted" style="margin:10px 0 0">The score ranks public-record signals. It is not a prediction that the owner will sell.</p>';

function reasonsHtml(list) {
  const icons = [['dollar', 'tone-green'], ['doc', 'tone-green'], ['pin', 'tone-green']];
  return (list || []).map(([t, x], i) => `<div class="reason"><span class="ico ${icons[i % 3][1]}">${ic(icons[i % 3][0], 17)}</span><div><b>${esc(t)}</b><div class="small muted">${esc(x)}</div></div></div>`).join('');
}

function taxTimeline(p) {
  const out = [];
  const yr = new Date().getFullYear() - 1;
  if (p.annual_tax) {
    out.push(`<div class="tl"><div class="grow"><b>${yr} tax year</b> <span class="pill p-red tiny">Delinquent</span><div class="tiny muted">Annual tax ${money(p.annual_tax, 2)}</div></div><b class="num">${money(p.total_due, 2)}</b></div>`);
  }
  if (p.prior_due) {
    out.push(`<div class="tl"><div class="grow"><b>Prior years</b> <span class="pill p-red tiny">Delinquent</span><div class="tiny muted">About ${yrs(Math.max((p.years_behind || 1) - 1, 1))} yr of unpaid tax + interest</div></div><b class="num">${money(p.prior_due, 2)}</b></div>`);
  }
  const snaps = p.snapshots || [];
  if (snaps.length) {
    const f = snaps[0], l = snaps[snaps.length - 1];
    out.push(`<div class="tl info"><div class="grow"><b>First seen on list</b><div class="tiny muted">${fmtDate(f.date)}</div></div><b class="num">${money(f.amount, 2)}</b></div>`);
    if (snaps.length > 1) out.push(`<div class="tl info"><div class="grow"><b>Latest county list</b><div class="tiny muted">${fmtDate(l.date)}</div></div><b class="num">${money(l.amount, 2)}</b></div>`);
  }
  if (!p.is_active) out.unshift(`<div class="tl ok"><div class="grow"><b>Removed from list</b> <span class="pill p-green tiny">Paid</span></div></div>`);
  return out.join('') || '<div class="small muted">No tax history yet.</div>';
}

// ================================================================ MAP
export async function mapView(el) {
  const DEF = { min_score: '', min_equity: '', min_years: '', ptype: 'all', owed: '', q: '', sort: 'score', inview: true };
  const st = { ...DEF };
  try { Object.assign(st, JSON.parse(localStorage.getItem('eh_map_v2') || '{}')); } catch (e) { }
  const CAP = 3000, PER = 20;
  el.style.padding = '18px 20px 20px';
  const opt = (pairs, val) => pairs.map(([v, l]) => `<option value="${esc(v)}" ${String(val) === String(v) ? 'selected' : ''}>${esc(l)}</option>`).join('');
  const choice = (id, pairs, val, label) => `<button type="button" class="map-choice" id="${id}Choice" data-choice="${id}" aria-label="${label}" aria-haspopup="menu"><span class="map-choice-label">${esc(pairs.find(([v]) => String(v) === String(val))?.[1] || pairs[0][1])}</span>${ic('chev', 14)}</button><select id="${id}" hidden aria-hidden="true" tabindex="-1">${opt(pairs, val)}</select>`;
  el.innerHTML = `<div class="map-wrap">
    <div class="map-list">
      <div style="padding:14px 16px 6px">
        <div class="row between"><h2 id="mapCount" style="font-size:17px">Properties</h2>
          ${choice('mSort', [['score', 'Best deal score'], ['owed', 'Most taxes owed'], ['equity', 'Most equity'], ['years', 'Most years behind'], ['newest', 'Newest']], st.sort, 'Sort properties')}</div>
        <div class="tiny muted" id="mapSub" style="margin-top:2px"></div>
        <label class="row tiny" style="margin-top:8px;gap:6px;cursor:pointer"><input type="checkbox" id="mInView" ${st.inview ? 'checked' : ''}> Only list what is visible on the map</label>
      </div>
      <div class="items" id="mItems"></div>
      <div class="row" style="justify-content:center;padding:10px;border-top:1px solid var(--line)"><button class="btn sm" id="mPrev">${ic('left', 15)}</button><span class="small muted" id="mPage" style="min-width:90px;text-align:center"></span><button class="btn sm" id="mNext">${ic('right', 15)}</button></div></div>
    <div class="map-area"><div id="bigMap"></div>
      <div class="map-filters">
        ${choice('mCounty', [['all', 'All counties'], ...S.meta.counties.map((c) => [String(c.id), `${c.name}, ${c.state}`])], S.county, 'County')}
        <div class="search" style="width:200px;height:36px">${ic('search', 15)}<input id="mQ" placeholder="Address or owner" value="${esc(st.q)}"></div>
        ${choice('fs', [['', 'Score: any'], ['40', 'Score: 40+'], ['60', 'Score: 60+'], ['80', 'Score: 80+']], st.min_score, 'Deal score')}
        ${choice('fo', [['', 'Owed: any'], ['0-2000', 'Owed: under $2K'], ['2000-10000', 'Owed: $2K-$10K'], ['10000-', 'Owed: $10K+']], st.owed, 'Taxes owed')}
        ${choice('fe', [['', 'Equity: any'], ['10000', 'Equity: $10K+'], ['30000', 'Equity: $30K+'], ['50000', 'Equity: $50K+'], ['100000', 'Equity: $100K+']], st.min_equity, 'Estimated equity')}
        ${choice('fy', [['', 'Years behind: any'], ['2', '2+ years'], ['3', '3+ years'], ['5', '5+ years']], st.min_years, 'Years behind on taxes')}
        ${choice('ft', [['all', 'Type: all'], ['homes', 'Homes'], ['Vacant land', 'Vacant land'], ['Commercial', 'Commercial'], ['Agricultural', 'Agricultural']], st.ptype, 'Property type')}
        <button class="btn sm" id="fClear" aria-label="Remove all filters">${ic('x', 14)} Reset</button>
        <span class="grow"></span><span class="small muted" id="resN"></span>
        <button class="btn sm" id="saveSearch">${ic('bookmark', 15)} Save search</button>
      </div>
      <div class="map-loading" id="mLoad">${ic('refresh', 15)} Loading properties...</div>
      <div class="legend"><span><i style="background:#1F7A45"></i>Score 85+</span><span><i style="background:${AMBER}"></i>65-84</span><span><i style="background:${GREY}"></i>Below 65</span><span class="muted">Click a pin or a card for details</span></div>
    </div></div>`;
  $('.map-wrap', el).prepend($('.map-filters', el));
  const L = window.L;
  const syncChoice = (id) => { const select = $('#' + id), label = $('#' + id + 'Choice .map-choice-label'); if (label) label.textContent = select.selectedOptions[0]?.textContent || ''; };
  $$('[data-choice]', el).forEach((button) => button.onclick = () => {
    const select = $('#' + button.dataset.choice);
    menu(button, [...select.options].map((option) => ({ label: option.textContent, icon: option.selected ? 'check' : '', fn: () => {
      select.value = option.value; syncChoice(select.id); select.dispatchEvent(new Event('change', { bubbles: true }));
    } })));
  });
  const map = L.map('bigMap', { zoomControl: false, preferCanvas: true }).setView([39.5, -90], 5);
  L.control.zoom({ position: 'bottomright' }).addTo(map);
  baseTiles(map);
  const layer = L.layerGroup().addTo(map);
  let pts = [], shown = [], page = 1, markers = {}, sel = null, req = 0;
  const sorter = { score: (p) => -(p.score || 0), owed: (p) => -(p.total_due ?? p.amount_owed ?? 0), equity: (p) => -(p.est_equity || 0), years: (p) => -(p.years_behind || 0), newest: (p) => -new Date(p.first_seen || 0) };
  function query() {
    const [mn, mx] = (st.owed || '-').split('-');
    const q = { county: S.county, min_score: st.min_score, min_equity: st.min_equity, min_years: st.min_years, ptype: st.ptype, min_owed: mn, max_owed: mx, q: st.q.trim() };
    return Object.entries(q).filter(([, v]) => v !== '' && v != null).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');
  }
  async function load(fit = true) {
    const my = ++req;
    $('#mLoad').style.display = 'flex';
    const res = await api('/api/map?' + query());
    if (my !== req) return;  // a newer filter change already started
    $('#mLoad').style.display = 'none';
    pts = Array.isArray(res) ? res : [];
    layer.clearLayers(); markers = {}; sel = null;
    pts.forEach((p) => {
      const m = pin(p).bindPopup(popupHtml(p), { maxWidth: 320 }).addTo(layer);
      m.on('click', () => highlight(p.id, false));
      markers[p.id] = m;
    });
    $('#resN').textContent = pts.length >= CAP ? `Top ${num(CAP)} shown` : `${num(pts.length)} on map`;
    if (fit || !pts.length) fitMap(map, pts, S.county, pts.length ? null : 'No properties match these filters here. Click Reset.');
    page = 1; list();
  }
  function list() {
    const b = map.getBounds();
    const base = st.inview ? pts.filter((p) => b.contains([p.lat, p.lng])) : pts.slice();
    shown = base.sort((a, c) => sorter[st.sort](a) - sorter[st.sort](c));
    const pages = Math.max(1, Math.ceil(shown.length / PER));
    page = Math.min(page, pages);
    const cn = S.county === 'all' ? 'all counties' : countyName(S.county);
    $('#mapCount').textContent = `Properties (${num(shown.length)})`;
    $('#mapSub').textContent = st.inview ? `${num(shown.length)} of ${num(pts.length)} visible on the map, ${cn}` : `${num(pts.length)} in ${cn}${pts.length >= CAP ? ` (top ${num(CAP)} by score: pick a county to see all)` : ''}`;
    const items = shown.slice((page - 1) * PER, page * PER);
    $('#mItems').innerHTML = items.map((p) => `<div class="pcard ${p.id === sel ? 'on' : ''}" data-id="${esc(p.id)}">${thumb(p, 'lg')}<div class="grow"><b>${esc(title(p.street) || 'Address not listed')}</b><div class="small muted">${esc(place(p))}</div>${homeLine(p) ? `<div class="tiny" style="color:var(--ink2);margin-top:2px">${homeLine(p)}</div>` : ''}
      <div class="meta"><div><b class="num">${money(p.total_due ?? p.amount_owed)}</b><span class="tiny muted">Taxes owed</span></div><div><b class="num">${kmoney(p.est_equity)}</b><span class="tiny muted">Equity</span></div><div><b>${yrs(p.years_behind)}</b><span class="tiny muted">Years</span></div></div>
      <div class="row" style="gap:6px;margin-top:6px"><a class="btn xs" href="#/deal/${encodeURIComponent(p.id)}">View deal</a><a class="btn xs primary" href="#/deal/${encodeURIComponent(p.id)}?offer=1">Draft offer</a></div></div>${scorePill(p.score)}</div>`).join('')
      || `<div class="empty small" style="padding:30px 16px">${pts.length && st.inview ? 'Nothing in this part of the map. Zoom out or drag the map.' : 'No properties match these filters.'}<div style="margin-top:10px"><button class="btn sm" data-reset>${ic('x', 14)} Reset filters</button></div></div>`;
    $('#mPage').textContent = `${page} / ${pages}`;
    $('#mPrev').disabled = page <= 1; $('#mNext').disabled = page >= pages;
  }
  function highlight(id, fly = true) {
    if (sel && markers[sel]) markers[sel].setStyle({ radius: 7, weight: 2 });
    sel = id;
    const m = markers[id]; if (!m) return;
    m.setStyle({ radius: 11, weight: 3 }); m.bringToFront();
    if (fly) { map.setView(m.getLatLng(), Math.max(map.getZoom(), 15)); m.openPopup(); }
    $$('.pcard').forEach((x) => x.classList.toggle('on', x.dataset.id === id));
    const card = $(`.pcard[data-id="${CSS.escape(id)}"]`); if (card) card.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  const save = () => { try { localStorage.setItem('eh_map_v2', JSON.stringify(st)); } catch (e) { } };
  const reset = () => { Object.assign(st, DEF, { sort: st.sort, inview: st.inview }); for (const id of ['fs', 'fe', 'fy', 'ft', 'fo']) { $('#' + id).value = id === 'ft' ? 'all' : ''; syncChoice(id); } $('#mQ').value = ''; load(); };
  $('#mItems').onclick = (e) => {
    if (e.target.closest('[data-reset]')) return reset();
    if (e.target.closest('a')) return;
    const c = e.target.closest('.pcard'); if (c) highlight(c.dataset.id);
  };
  $('#mItems').onmouseover = (e) => { const c = e.target.closest('.pcard'); const m = c && markers[c.dataset.id]; if (m && c.dataset.id !== sel) { m.setStyle({ radius: 10 }); m.bringToFront(); } };
  $('#mItems').onmouseout = (e) => { const c = e.target.closest('.pcard'); const m = c && markers[c.dataset.id]; if (m && c.dataset.id !== sel) m.setStyle({ radius: 7 }); };
  $('#mPrev').onclick = () => { page--; list(); $('#mItems').scrollTop = 0; }; $('#mNext').onclick = () => { page++; list(); $('#mItems').scrollTop = 0; };
  const bind = (s, key) => $(s).onchange = (e) => { st[key] = e.target.value; load(); };
  bind('#fs', 'min_score'); bind('#fe', 'min_equity'); bind('#fy', 'min_years'); bind('#ft', 'ptype'); bind('#fo', 'owed');
  let qt; $('#mQ').oninput = (e) => { clearTimeout(qt); qt = setTimeout(() => { st.q = e.target.value; load(); }, 350); };
  $('#mSort').onchange = (e) => { st.sort = e.target.value; page = 1; list(); };
  $('#mInView').onchange = (e) => { st.inview = e.target.checked; page = 1; list(); };
  $('#mCounty').onchange = (e) => { setCounty(e.target.value); load(); };
  $('#fClear').onclick = reset;
  $('#saveSearch').onclick = () => { save(); toast('Saved. The map opens with these filters next time.'); };
  let mt; map.on('moveend', () => { clearTimeout(mt); mt = setTimeout(() => { if (st.inview) { page = 1; list(); } }, 150); });
  const fitH = () => { const w = $('.map-wrap', el); if (!w) return; w.style.height = innerWidth > 900 ? Math.max(560, innerHeight - w.getBoundingClientRect().top - 18) + 'px' : ''; map.invalidateSize(); };
  fitH(); addEventListener('resize', fitH);
  await load();
  setTimeout(() => { map.invalidateSize(); list(); }, 60);
  return () => { map.remove(); el.style.padding = ''; removeEventListener('resize', fitH); };
}
