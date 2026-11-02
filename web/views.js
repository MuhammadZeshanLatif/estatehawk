// EstateHawk screens. Each view(el, params) renders into el and may return a cleanup function.
import {
  $, $$, esc, ic, api, money, kmoney, num, title, yrs, scorePill, ago, fmtDate, tileUrl, place, thumb, streetView, gmaps, homeLine,
  toast, modal, menu, S, setCounty, refreshMeta, countySelect, countyName, watchSync,
} from './app.js';
export { outreach, reports, settings, welcome, alerts, counties } from './views2.js';

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
  const st = { page: 1, per: 25, sort: 'score', min_score: '', min_owed: '', max_owed: '', min_years: '', ptype: 'homes', out_of_state: '', new_days: '', min_equity: '', q: '' };
  const prof = S.meta.settings.profile;
  el.innerHTML = `
  <div class="page-head">
    <div><h1>${greeting()}, ${esc(prof.name || 'there')}</h1><div class="sub">Here are your latest off-market opportunities from tax-delinquent records.</div></div>
    <div class="right">
      <div class="row">${ic('pin', 18)}${countySelect('countySel')}</div>
      <div class="updated-box">${ic('cal', 18)}<div><div class="small" style="font-weight:600">${fmtDate(new Date())}</div><div class="tiny muted">Last updated ${ago(S.meta.last_sync)}</div></div>
        <button class="icon-btn" id="syncBtn" title="Sync now">${ic('refresh', 17)}</button></div>
      <div data-sync-status></div>
    </div>
  </div>
  <div class="grid stats" id="stats">${'<div class="card stat skeleton" style="height:96px"></div>'.repeat(4)}</div>
  <div class="deals-grid">
    <div class="card" style="min-width:0">
      <div class="card-head" style="padding-top:20px"><div><h2>Property Leads</h2><div class="small muted" id="leadSub"></div></div>
        <div class="right row"><div class="search" style="width:260px;height:36px">${ic('search', 16)}<input id="leadQ" placeholder="Search properties..."></div></div></div>
      <div class="filters">
        <select class="select" id="fScore"><option value="">Deal Score</option><option value="85">85+ (High)</option><option value="80">80+</option><option value="65">65+</option></select>
        <select class="select" id="fOwed"><option value="">Taxes Owed</option><option value="0-2000">Under $2,000</option><option value="2000-10000">$2,000 to $10,000</option><option value="10000-">Over $10,000</option></select>
        <select class="select" id="fYears"><option value="">Years Behind</option><option value="2">2+ years</option><option value="3">3+ years</option><option value="5">5+ years</option></select>
        <button class="chip-btn" id="fMore">${ic('filter', 15)} More Filters</button>
        <span class="grow"></span>
        <span class="small muted" id="pageInfo"></span>
        <div class="pager"><button class="btn sm" id="prev">${ic('left', 16)}</button><button class="btn sm" id="next">${ic('right', 16)}</button></div>
      </div>
      <div id="bulk" class="row hide" style="padding:0 20px 12px"><b class="small" id="bulkN"></b><button class="btn xs" id="bulkPipe">${ic('plus', 14)} Add to pipeline</button><button class="btn xs" id="bulkOffer">${ic('letter', 14)} Draft offers</button><a class="btn xs" id="bulkCsv">${ic('download', 14)} Export CSV</a></div>
      <div style="overflow-x:auto"><table class="table" id="leadTable"><thead><tr>
        <th style="width:32px"><input type="checkbox" id="allChk"></th><th>Property</th><th class="hide-m">Owner</th><th class="r">Taxes Owed</th>
        <th class="r hide-m hide-xl">Years Behind</th><th class="r hide-m">Est. Value</th><th style="text-align:center">Deal Score</th><th class="hide-m">Actions</th>
      </tr></thead><tbody></tbody></table></div>
    </div>
    <div class="col gap16" style="gap:18px">
      <div class="card"><div class="card-head" style="padding-bottom:12px"><h3>Properties on Map</h3><a class="btn sm right" href="#/map">View Map</a></div><div class="mini-map" id="miniMap"></div></div>
      <div class="card"><div class="card-head" style="padding-bottom:12px"><h3>Today's alerts</h3><a class="btn sm right" href="#/alerts">View all</a></div><div id="todayAlerts"></div></div>
    </div>
  </div>`;

  const chosen = new Set();
  const qs = () => {
    const o = { county: S.county, ...st };
    return Object.entries(o).filter(([, v]) => v !== '' && v != null).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');
  };
  async function loadStats() {
    const s = await api('/api/stats?county=' + S.county);
    const chg = (v, txt) => v == null ? `<div class="foot">${txt}</div>` : `<div class="foot"><span class="chg ${v < 0 ? 'down' : ''}" style="margin:0">${v < 0 ? '' : '+'}${v}%</span> ${txt}</div>`;
    $('#stats').innerHTML = [
      ['doc', 'tone-green', 'New leads today', num(s.new_today), chg(s.new_change, 'vs. yesterday'), '#/deals'],
      ['star', 'tone-amber', 'High-score deals', num(s.high_score), chg(s.high_change, 'Score 80+'), '#/map'],
      ['house', 'tone-green', 'Avg equity', kmoney(s.avg_equity), '<div class="foot">Estimated per deal</div>', ''],
      ['map', 'tone-green', 'Counties tracked', num(s.counties), `<div class="foot">Across ${s.states} state${s.states === 1 ? '' : 's'}</div>`, '#/counties'],
    ].map(([i, t, l, v, f, href]) => `<a class="card stat" ${href ? `href="${href}"` : ''}><span class="ico ${t}">${ic(i, 21)}</span><div><div class="lbl">${l}</div><div class="val num">${v}</div>${f}</div></a>`).join('');
  }
  async function loadLeads() {
    const r = await api('/api/parcels?' + qs());
    const cn = S.county === 'all' ? 'all counties' : countyName(S.county);
    $('#leadSub').textContent = `Tax-delinquent properties in ${cn}`;
    $('#pageInfo').textContent = r.total ? `${(r.page - 1) * r.per + 1} - ${Math.min(r.page * r.per, r.total)} of ${num(r.total)} leads` : '0 leads';
    $('#prev').disabled = r.page <= 1; $('#next').disabled = r.page * r.per >= r.total;
    $('#leadTable tbody').innerHTML = r.rows.map((p) => `<tr data-id="${esc(p.id)}">
      <td><input type="checkbox" class="chk" ${chosen.has(p.id) ? 'checked' : ''}></td>
      <td><div class="prop">${thumb(p)}<div><b>${esc(title(p.street))}</b><span>${esc(place(p))}</span>${homeLine(p) ? `<span style="display:block;color:var(--ink2)">${homeLine(p)}</span>` : ''}</div></div></td>
      <td class="hide-m"><div style="max-width:150px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="${esc(title(p.owner_name))}">${esc(title(p.owner_name))}</div>${p.contact_status === 'found' ? ` <span class="pill p-green tiny">${ic('phone', 11)} Contact</span>` : p.contact_status === 'private' ? ' <span class="pill tiny" style="background:#EEE;color:#555">Private</span>' : ''}${p.mail_state && p.mail_state !== p.state ? ` <span class="pill p-amber tiny" style="padding:1px 7px">Out of state: ${esc(p.mail_state)}</span>` : ''}</td>
      <td class="r num">${money(p.total_due ?? p.amount_owed)}</td>
      <td class="r num hide-m hide-xl">${yrs(p.years_behind)}</td>
      <td class="r num hide-m">${money(p.appraised_total)}</td>
      <td style="text-align:center">${scorePill(p.score)}</td>
      <td class="hide-m"><div class="row gap4" style="flex-wrap:nowrap"><a class="btn sm primary" href="#/deal/${encodeURIComponent(p.id)}?offer=1">Draft offer</a><button class="icon-btn more" style="width:30px;height:30px">${ic('dots', 18)}</button></div></td></tr>`).join('') || `<tr><td colspan="8"><div class="empty">No leads match these filters.${S.meta.parcels ? '' : ' Add a county and run a sync, or load demo data in Settings.'}</div></td></tr>`;
  }
  async function loadSide() {
    const [pts, al] = await Promise.all([api(`/api/map?county=${S.county}&ptype=homes&min_score=60`), api('/api/alerts?limit=4&county=' + S.county)]);
    const L = window.L, mm = $('#miniMap');
    if (!mm._map) { mm._map = L.map(mm, { zoomControl: true, attributionControl: false, scrollWheelZoom: false }); baseTiles(mm._map); mm._layer = L.layerGroup().addTo(mm._map); }
    mm._layer.clearLayers();
    const top = pts.slice(0, 120);
    top.forEach((p) => pin(p).bindPopup(popupHtml(p)).addTo(mm._layer));
    if (top.length) mm._map.fitBounds(L.latLngBounds(top.map((p) => [p.lat, p.lng])).pad(.15)); else mm._map.setView([40.3, -82.8], 7);
    $('#todayAlerts').innerHTML = al.rows.map((a) => `<a class="alert-row" href="${a.parcel_id ? '#/deal/' + encodeURIComponent(a.parcel_id) : '#/alerts'}">${alertIcon(a.type)}<div class="grow"><b>${esc(a.title)}</b><div class="tiny muted">${esc(a.county_name || '')}</div></div><span class="tiny muted">${ago(a.ts)}</span></a>`).join('') || '<div class="empty small">No alerts yet</div>';
  }
  const reload = () => { st.page = 1; loadLeads(); };
  $('#countySel').onchange = (e) => { setCounty(e.target.value); loadStats(); reload(); loadSide(); };
  $('#fScore').onchange = (e) => { st.min_score = e.target.value; reload(); };
  $('#fOwed').onchange = (e) => { const [a, b] = (e.target.value || '-').split('-'); st.min_owed = a; st.max_owed = b; reload(); };
  $('#fYears').onchange = (e) => { st.min_years = e.target.value; reload(); };
  let qt; $('#leadQ').oninput = (e) => { clearTimeout(qt); qt = setTimeout(() => { st.q = e.target.value; reload(); }, 250); };
  $('#prev').onclick = () => { st.page--; loadLeads(); };
  $('#next').onclick = () => { st.page++; loadLeads(); };
  $('#fMore').onclick = () => modal(`<h2>More filters</h2><div style="height:14px"></div>
    <div class="field"><label>Property type</label><select class="select" id="mType"><option value="homes">Homes only (single + multi family)</option><option value="all">All property types</option><option>Vacant land</option><option>Commercial</option><option>Agricultural</option></select></div>
    <div class="field"><label>Minimum est. equity</label><select class="select" id="mEq"><option value="">Any</option><option value="30000">$30K+</option><option value="50000">$50K+</option><option value="100000">$100K+</option></select></div>
    <div class="field"><label>Newly delinquent</label><select class="select" id="mNew"><option value="">Any time</option><option value="1">Today</option><option value="7">Last 7 days</option><option value="30">Last 30 days</option></select></div>
    <label class="row" style="margin:6px 0 14px"><input type="checkbox" id="mOos"> Out-of-state owners only</label>
    <div class="field"><label>Sort by</label><select class="select" id="mSort"><option value="score">Deal score</option><option value="newest">Newest first</option><option value="owed">Taxes owed</option><option value="equity">Est. equity</option><option value="years">Years behind</option></select></div>
    <div class="row" style="justify-content:flex-end"><button class="btn" data-close>Cancel</button><button class="btn primary" id="mApply">Apply</button></div>`, (m, close) => {
    $('#mType', m).value = st.ptype; $('#mEq', m).value = st.min_equity; $('#mNew', m).value = st.new_days; $('#mOos', m).checked = st.out_of_state === '1'; $('#mSort', m).value = st.sort;
    $('#mApply', m).onclick = () => { st.ptype = $('#mType', m).value; st.min_equity = $('#mEq', m).value; st.new_days = $('#mNew', m).value; st.out_of_state = $('#mOos', m).checked ? '1' : ''; st.sort = $('#mSort', m).value; close(); reload(); };
  });
  const tbody = $('#leadTable tbody');
  const updBulk = () => { $('#bulk').classList.toggle('hide', !chosen.size); $('#bulkN').textContent = `${chosen.size} selected`; $('#bulkCsv').href = '/api/parcels/export.csv?' + qs(); };
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
  await Promise.all([loadStats(), loadLeads(), loadSide()]);
}

// ================================================================ DEAL DETAIL
export async function deal(el, [rawId]) {
  const [id, query] = (rawId || '').split('?');
  const p = await api(`/api/parcels/${encodeURIComponent(id)}/detail`);
  p.contacts = p.contacts || [];
  const due = p.total_due ?? p.amount_owed;
  const outState = p.mail_state && p.mail_state !== p.state;
  const d = p.offer_defaults;
  const sugg = p.suggested_offer || 0;
  const label = p.score >= 85 ? 'High potential deal' : p.score >= 65 ? 'Good potential' : 'Lower priority';
  const stageLabel = (S.meta.stages.find((s) => s.key === p.stage) || {}).label;
  el.innerHTML = `
  <a class="small muted row gap6" href="#/deals" style="margin-bottom:12px">${ic('back', 15)} Back to Deals</a>
  <div class="page-head" style="margin-bottom:16px">
    <div><h1 style="font-size:28px">${esc(title(p.street))}</h1><div class="sub" style="color:var(--ink2)">${[title(p.city), [p.state, p.zip].filter(Boolean).join(' ')].filter(Boolean).map(esc).join(', ')} · ${esc(p.county_name)}</div></div>
    <div class="row" style="margin-left:24px"><span class="pill p-green" style="padding:6px 8px 6px 14px;font-size:13px">Deal score ${scorePill(p.score)}</span>
      ${!p.is_active ? '<span class="pill p-grey">Paid / off list</span>' : ''}${stageLabel ? `<span class="pill p-blue">${esc(stageLabel)}</span>` : ''}</div>
    <div class="right">
      <button class="btn" id="shareBtn">${ic('share', 16)} Share</button>
      <button class="btn" id="listBtn">${ic('bookmark', 16)} ${p.stage ? 'In pipeline' : 'Add to list'}</button>
      <button class="btn" id="moreBtn" style="width:40px;padding:0">${ic('dots', 18)}</button>
    </div>
  </div>
  <div class="detail-grid">
    <div class="col" style="gap:18px;min-width:0">
      <div>
        <div class="gallery" id="gal"><span class="count" id="galCount">1 / ${p.photo_url ? 4 : 3}</span></div>
        <div class="gal-tabs">
          ${p.photo_url ? `<button data-v="county" style="background-image:url('${esc(p.photo_url)}')"><span>County aerial</span></button>` : ''}
          <button class="on" data-v="sat" style="background-image:url('${tileUrl(p.lat, p.lng, 18)}')"><span>Satellite</span></button>
          <button data-v="map" style="background-image:url('${tileUrl(p.lat, p.lng, 16).replace("World_Imagery", "World_Street_Map")}')"><span>Street map</span></button>
          <button data-v="sv" style="background:#3E4A44"><span>Street View</span></button>
        </div>
      </div>
      <div class="card card-pad"><h3 style="margin-bottom:6px">Property Details</h3>
        <div class="facts">
          ${fact('pin', 'Address', `${esc(title(p.street))}<div class="small muted" style="font-weight:400">${[title(p.city), [p.state, p.zip].filter(Boolean).join(' ')].filter(Boolean).map(esc).join(', ')}</div>`)}
          ${fact('user', 'Owner', `${esc(title(p.owner_full_name || p.owner_name))}${outState ? `<div><span class="pill p-amber tiny" style="margin-top:4px">Out of state (${esc(p.mail_state)})</span></div>` : p.owner_occupied === 0 ? '<div><span class="pill p-grey tiny" style="margin-top:4px">Not owner-occupied</span></div>' : ''}`)}
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
    </div>
    <div class="col" style="gap:18px;min-width:0">
      <div class="card card-pad"><h3 style="margin-bottom:12px">Tax History</h3><div class="timeline">${taxTimeline(p)}</div>
        ${p.property_url ? `<a class="small" style="color:var(--green)" href="${esc(p.property_url)}" target="_blank" rel="noopener">Open county record ${ic('link', 13)}</a>` : ''}</div>
      <div class="card card-pad"><div class="row between"><h3>Why this score?</h3>${p.ai ? `<button class="btn xs" id="aiWhy">${ic('sparkle', 13)} Explain with AI</button>` : ''}</div>
        <div class="big-score">${scorePill(p.score)}<div><b style="color:${p.score >= 85 ? 'var(--green-ink)' : 'var(--ink)'}">${label}</b><div class="tiny muted">Based on your scoring weights</div></div></div>
        <div id="reasons">${reasonsHtml(p.reasons)}</div>
        <div class="breakdown" style="margin-top:10px;border-top:1px solid var(--line);padding-top:10px">${Object.entries(p.score_parts || {}).map(([k, v]) => {
          const w = S.meta.settings.weights[k] || 1;
          return `<div class="b-row"><span class="muted">${esc({ years_behind: 'Years behind', equity: 'Equity', amount_owed: 'Amount owed', out_of_state: 'Out-of-state owner', vacancy: 'Vacancy signals' }[k])}</span><div class="b-bar"><i style="width:${Math.min(100, v / w * 100)}%"></i></div><b class="num" style="text-align:right">+${Math.round(v)}/${w}</b></div>`;
        }).join('')}</div></div>
    </div>
    <div class="col col3" style="gap:18px;min-width:0">
      <div class="card card-pad" id="offerCard"></div>
      <div class="card card-pad" id="contactsCard"></div>
      <div class="card card-pad"><div class="row between" style="margin-bottom:6px"><h3>Activity Notes</h3><div class="row gap6"><button class="btn xs" id="addTask">${ic('clock', 13)} Follow-up</button><button class="btn xs" id="addNote">Add note</button></div></div>
        <div id="acts"></div></div>
    </div>
  </div>
  <div class="mobile-actions"><button class="btn primary" id="mOffer">${ic('mail', 16)} Send offer</button><div class="row"><a class="btn grow" id="mCall">${ic('phone', 16)} Call owner</a><button class="btn grow" id="mSave">${ic('bookmark', 16)} Save deal</button></div></div>`;

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
  if (showMsg) { const m = document.createElement('div'); m.style.cssText = 'position:absolute;inset:0;z-index:460;display:grid;place-items:center;color:#556;background:#E9ECE6;font-size:13px;text-align:center;padding:20px'; m.textContent = 'Location not placed on the map yet. It appears after the next sync.'; g.append(m); }
  $$('.gal-tabs button').forEach((b, i) => b.onclick = () => {
    if (b.dataset.v === 'sv') return p.lat ? open(streetView(p), '_blank') : open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(p.street + ', ' + p.city + ' ' + p.state + ' ' + p.zip)}`, '_blank');
    $$('.gal-tabs button').forEach((x) => x.classList.toggle('on', x === b));
    photoBox.style.display = b.dataset.v === 'county' ? 'block' : 'none';
    if (b.dataset.v !== 'county') { gm.removeLayer(layer); layer = baseTiles(gm, b.dataset.v === 'sat' ? 'sat' : 'light'); gm.setZoom(b.dataset.v === 'sat' ? 18 : 16); }
    $('#galCount').textContent = `${i + 1} / ${nTabs}`;
  });
  if (p.photo_url) $('.gal-tabs button[data-v=county]').click();

  // header buttons
  $('#shareBtn').onclick = async () => { await navigator.clipboard?.writeText(location.href).catch(() => { }); toast('Link copied'); };
  $('#listBtn').onclick = async () => { if (!p.stage) { await api(`/api/parcels/${encodeURIComponent(id)}/stage`, { method: 'POST', body: { stage: 'new' } }); toast('Added to Outreach > New lead'); deal(el, [rawId]); } else location.hash = '#/outreach'; };
  $('#mSave').onclick = $('#listBtn').onclick;
  $('#moreBtn').onclick = (e) => { e.stopPropagation(); menu($('#moreBtn'), [
    ...S.meta.stages.map((s) => ({ label: 'Move to ' + s.label, icon: 'right', fn: () => moveStage(s.key) })),
    '-', { label: 'Open in Google Maps', icon: 'pin', fn: () => open(gmaps(p)) },
    ...(p.stage ? [{ label: 'Remove from pipeline', icon: 'x', danger: true, fn: () => moveStage('remove') }] : []),
  ]); };
  async function moveStage(stage) {
    let fee;
    if (stage === 'closed') { fee = prompt('Assignment fee earned ($)?', '10000'); if (fee == null) return; }
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
    oc.innerHTML = `<h3 style="margin-bottom:12px">Offer Draft</h3>
      <div class="offer-top"><div class="sugg"><div class="tiny muted">Suggested offer</div><b class="num">${money(offer?.price ?? sugg)}</b></div>
        <div><div class="tiny muted">Est. equity</div><b class="num">${money(p.est_equity)}</b></div><div><div class="tiny muted">Est. value</div><b class="num">${money(p.appraised_total)}</b></div></div>
      <details ${offer ? '' : 'open'} style="margin:14px 0 4px"><summary class="small" style="cursor:pointer;font-weight:600;color:var(--ink2)">Offer terms</summary>
        <div class="terms" style="margin-top:10px">
          <div class="field"><label>Offer price</label><input class="input num" id="oPrice" value="${Math.round(offer?.price ?? sugg)}"></div>
          <div class="field"><label>Financing</label><select class="select" id="oFin">${['Cash', 'DSCR loan (80% LTV)', 'Conventional loan', 'Hard money', 'Seller financing'].map((f) => `<option ${f === (offer?.financing || d.financing) ? 'selected' : ''}>${f}</option>`).join('')}</select></div>
          <div class="field"><label>Closing (days)</label><input class="input" id="oDays" value="${offer?.closing_days || d.closing_days}"></div>
          <div class="field"><label>Earnest money</label><input class="input" id="oEarnest" value="${offer?.earnest || d.earnest}"></div>
        </div>
        <div class="field"><label>Seller credits</label><input class="input" id="oCredits" value="${esc(offer?.seller_credits || d.seller_credits)}"></div>
        <button class="btn sm" id="oGen">${ic('sparkle', 14)} ${offer ? 'Re-draft' : 'Draft offer'}${p.ai ? ' with Gemini' : ''}</button>
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
    <div class="card card-pad small">${esc(title(p.owner_full_name || p.owner_name))}<br>${esc(title(p.mail_address || ''))}</div>
    <div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-close>Close</button><button class="btn primary" id="logCall">Log a call</button></div>`, (m, close) => {
    $('#logCall', m).onclick = async () => { await api(`/api/parcels/${encodeURIComponent(id)}/activity`, { method: 'POST', body: { kind: 'call', text: 'Called owner' } }); close(); deal(el, [rawId]); };
  });

  // owner contacts: county records have none. Free sources: Gemini + Google Search, and what the user pastes after a lookup.
  let lastSrc = 'Manual';
  const renderContacts = (list, msg = '') => {
    const o = ownerInfo(p);
    if (list.length) p.contact_status = 'found';
    if ($('#factContacts')) $('#factContacts').innerHTML = contactFact(p);
    const row = (c) => `<div class="contact"><span class="ico ${c.kind === 'phone' ? 'tone-green' : 'tone-blue'}">${ic(c.kind === 'phone' ? 'phone' : 'mail', 15)}</span>
      <div class="grow" style="min-width:0"><a href="${c.kind === 'phone' ? 'tel:+1' + esc(c.norm) : 'mailto:' + esc(c.value)}"><b>${esc(c.value)}</b></a>${c.note ? `<div class="tiny muted ellip">${esc(c.note)}</div>` : ''}
      <div class="row wrap gap6" style="margin-top:4px">${c.sources.length > 1 ? `<span class="pill p-green tiny">${c.sources.length} sources</span>` : ''}${c.sources.map((x) => `<span class="pill tiny">${esc(x)}</span>`).join('')}</div></div>
      <button class="btn xs ghost" data-cdel="${c.id}" title="Remove">${ic('x', 13)}</button></div>`;
    $('#contactsCard').innerHTML = `<div class="row between" style="margin-bottom:4px"><h3>Owner Contacts</h3>${p.ai ? `<button class="btn xs" id="cAi">${ic('sparkle', 13)} Find with Gemini</button>` : ''}</div>
      <button class="btn primary" id="cSee" style="width:100%;margin:6px 0 10px">${ic('phone', 15)} Click to see contact info</button>
      <div class="tiny muted" style="margin-bottom:10px">${esc(o.name)} · lives in ${esc(o.city)}, ${esc(o.st)}. Same number from several sources shows once.</div>
      ${msg ? `<div class="small" style="background:var(--bg2,#F4F5F1);border-radius:8px;padding:8px 10px;margin-bottom:10px">${msg}</div>` : ''}
      <div id="cList">${list.map(row).join('') || '<div class="empty small" style="padding:10px">No phone or email yet</div>'}</div>
      <div class="small muted" style="margin:12px 0 6px">Look up free, then paste what you find:</div>
      <div class="row wrap gap6">${lookupLinks(p).map(([n, u]) => `<button class="btn xs" data-lookup="${esc(u)}">${n}</button>`).join('')}<button class="btn xs primary" id="cClip">Paste from clipboard</button><button class="btn xs ghost" id="cPaste">Type / paste manually</button></div>
      <div class="tiny muted" style="margin-top:6px">Tip: click Google, copy the AI Overview (or any page text) with Ctrl+A, Ctrl+C, come back and click Paste from clipboard.</div>`;
    $$('[data-lookup]', $('#contactsCard')).forEach((b) => b.onclick = () => { lastSrc = b.textContent.trim(); window.open(b.dataset.lookup, '_blank', 'noopener'); });
    $('#cSee').onclick = async () => {
      if (document.documentElement.dataset.ehHelper !== '1') {
        modal(`<h2>Install EstateHawk Helper (one time)</h2><p class="muted small">This button reads the owner's Google search in a hidden window. A web page cannot do that alone, so it needs the small helper extension from your project folder.</p>
          <ol class="small" style="line-height:1.8;padding-left:18px"><li>Open <b>chrome://extensions</b> in Chrome</li><li>Turn on <b>Developer mode</b> (top right)</li><li>Click <b>Load unpacked</b> and pick <b>E:\\Projects\\EstateHawk\\estatehawk\\extension</b></li><li>Come back here and press F5</li></ol>
          <div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn primary" data-close>OK</button></div>`);
        return;
      }
      const b = $('#cSee'); b.disabled = true; b.innerHTML = 'Searching Google in the background...';
      const q = `"${o.name}" ${o.city} ${o.st} phone`;
      const rid = Math.random().toString(36).slice(2);
      const res = await new Promise((resolve) => {
        const t = setTimeout(() => { window.removeEventListener('message', on); resolve({ ok: false, error: 'Timed out' }); }, 240000);
        function on(e) {
          if (e.source === window && e.data && e.data.type === 'EH_GOOGLE_PROGRESS') {
            b.innerHTML = e.data.state === 'captcha' ? 'Google wants a check: tick "I\'m not a robot" in the window that just opened' : 'Reading Google answer...';
            if (e.data.state === 'captcha') toast('Tick "I\'m not a robot" in the Google window. It closes by itself after.');
            return;
          }
          if (e.source === window && e.data && e.data.type === 'EH_GOOGLE_RESULT' && e.data.id === rid) { clearTimeout(t); window.removeEventListener('message', on); resolve(e.data); } }
        window.addEventListener('message', on);
        window.postMessage({ type: 'EH_GOOGLE', q, id: rid }, '*');
      });
      if (!res.ok) { toast(res.error || 'Search failed'); renderContacts(p.contacts, esc(res.error || 'Search failed')); return; }
      const text = res.overview || '';
      const summary = text.split(/\n+/).map((x) => x.trim()).filter((x) => x.length > 30)[0] || '';
      const r = await api(`/api/parcels/${encodeURIComponent(id)}/contacts`, { method: 'POST', body: { text, source: 'Google', searched: true, summary } });
      p.contacts = r.contacts;
      if (!r.contacts.length) { p.contact_status = 'private'; p.contact_checked = new Date().toISOString(); }
      renderContacts(p.contacts, r.found.length ? `Found ${r.found.length} phone/email on Google.${summary ? '<br><span class="muted">' + esc(summary.slice(0, 220)) + '</span>' : ''}` : (res.note || 'No phone or email in Google\'s answer. Marked Private.'));
    };
    $('#cClip').onclick = async () => {
      let text = '';
      try { text = await navigator.clipboard.readText(); } catch (e) { toast('Allow clipboard access, or use Type / paste manually'); return; }
      const r = await api(`/api/parcels/${encodeURIComponent(id)}/contacts`, { method: 'POST', body: { text, source: lastSrc } });
      p.contacts = r.contacts; renderContacts(p.contacts, r.found.length ? `Saved ${r.found.length} phone/email from ${esc(lastSrc)}.` : 'No phone number or email found in the copied text.');
    };
    $$('[data-cdel]').forEach((b) => b.onclick = async () => { await api('/api/contacts/' + b.dataset.cdel, { method: 'DELETE' }); p.contacts = p.contacts.filter((c) => c.id != b.dataset.cdel); renderContacts(p.contacts); });
    $('#cPaste').onclick = () => modal(`<h2>Paste found info</h2><p class="muted small">Copy the phone numbers and emails from the people-search page and paste them here. Every number and email in the text is saved; duplicates are merged.</p>
      <div class="field"><label>Found on</label><select class="select" id="cSrc"><option>Google</option><option>TruePeopleSearch</option><option>FastPeopleSearch</option><option>Whitepages</option><option>Facebook</option><option>Ohio SOS</option><option>Other</option></select></div>
      <textarea class="input" id="cText" rows="6" style="width:100%" placeholder="(330) 555-0142 Wireless&#10;jdoe@example.com"></textarea>
      <div class="row" style="justify-content:flex-end;margin-top:14px"><button class="btn" data-close>Cancel</button><button class="btn primary" id="cSave">Save</button></div>`, (m, close) => {
      $('#cSave', m).onclick = async () => {
        const r = await api(`/api/parcels/${encodeURIComponent(id)}/contacts`, { method: 'POST', body: { text: $('#cText', m).value, source: $('#cSrc', m).value } });
        close(); p.contacts = r.contacts; renderContacts(p.contacts, r.found.length ? `Saved ${r.found.length} item(s).` : 'No phone number or email found in that text.');
      };
    });
    if ($('#cAi')) $('#cAi').onclick = async () => {
      const b = $('#cAi'); b.disabled = true; b.innerHTML = 'Searching the web...';
      try {
        const r = await api(`/api/parcels/${encodeURIComponent(id)}/contacts/ai`, { method: 'POST', body: o });
        p.contacts = r.contacts; if (!r.contacts.length) { p.contact_status = 'private'; p.contact_checked = new Date().toISOString(); }
        renderContacts(p.contacts, `${r.added ? `Gemini found ${r.added} item(s). Check them before calling.` : 'Gemini found no public phone or email for this owner.'}${r.notes ? '<br>' + esc(r.notes) : ''}`);
      } catch (e) { toast(e.message || 'Gemini search failed'); b.disabled = false; b.innerHTML = 'Find with Gemini'; }
    };
  };
  renderContacts(p.contacts);

  // activities + tasks
  const actIcon = { email: ['mail', 'tone-blue'], letter: ['letter', 'tone-blue'], sms: ['sms', 'tone-blue'], call: ['phone', 'tone-green'], reply: ['sms', 'tone-green'], stage: ['right', 'tone-grey'], note: ['note', 'tone-amber'] };
  $('#acts').innerHTML = [...p.tasks.filter((t) => !t.done).map((t) => `<div class="act"><span class="ico tone-amber">${ic('clock', 16)}</span><div class="grow"><div>${esc(t.text)}</div><div class="tiny muted">Due ${fmtDate(t.due)}</div></div><input type="checkbox" data-task="${t.id}"></div>`),
    ...p.activities.map((a) => { const [i, t] = actIcon[a.kind] || ['note', 'tone-grey']; return `<div class="act"><span class="ico ${t}">${ic(i, 16)}</span><div class="grow"><div>${esc(a.text)}</div><div class="tiny muted">${fmtDate(a.ts, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })}</div></div><span class="tiny muted">${esc(a.author || '')}</span></div>`; })]
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
  const parts = (p.owner_full_name || '').trim() ? (p.owner_full_name || '').split(/\s*&\s*/)[0] : (p.owner_name || '').replace(/&.*/, '').trim().split(/\s+/).slice(0, 2).reverse().join(' ');
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
    ['TruePeopleSearch', `https://www.truepeoplesearch.com/results?name=${q(name)}&citystatezip=${q(city + ', ' + st)}`],
    ['FastPeopleSearch', `https://www.fastpeoplesearch.com/name/${name.toLowerCase().replace(/[^a-z ]/g, '').trim().replace(/\s+/g, '-')}_${city.toLowerCase().replace(/\s+/g, '-')}-${st.toLowerCase()}`],
    ['Google', `https://www.google.com/search?q=${q('"' + name + '" ' + city + ' ' + st + ' phone')}`],
  ];
}

function contactFact(p) {
  const list = p.contacts || [];
  if (list.length) return list.slice(0, 6).map((c) => `<div style="margin-bottom:3px"><a style="color:var(--ink)" href="${c.kind === 'phone' ? 'tel:+1' + esc(c.norm) : 'mailto:' + esc(c.value)}">${esc(c.value)}</a>
    <span class="tiny muted" style="font-weight:400">${c.sources.length > 1 ? c.sources.length + ' sources' : esc((c.sources[0] || '').replace('Gemini: ', ''))}${(/\b(cell|landline)\b/.exec(c.note || '') || [])[1] ? ' · ' + /\b(cell|landline)\b/.exec(c.note)[1] : ''}${/old/.test(c.note || '') ? ' · old' : ''}</span></div>`).join('')
    + (list.length > 6 ? `<div class="tiny muted">+${list.length - 6} more in Owner Contacts</div>` : '');
  if (p.contact_status === 'private') return `<span class="pill tiny" style="background:#EEE;color:#555">Private</span><div class="small muted" style="font-weight:400;margin-top:4px">No public phone or email found${p.contact_checked ? ' (searched ' + esc(fmtDate(p.contact_checked)) + ')' : ''}.</div>`;
  return '<span class="small muted" style="font-weight:400">Not searched yet. The next sync searches it (best scores first), or use Find with Gemini below.</span>';
}

function fact(i, k, v) { return `<div class="fact">${ic(i, 17)}<div><div class="k">${k}</div><div class="v">${v}</div></div></div>`; }

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
  const st = { min_score: '80', min_equity: '30000', min_years: '2', ptype: 'homes', sort: 'score' };
  el.style.padding = '18px 20px 20px';
  el.innerHTML = `<div class="map-wrap">
    <div class="map-list"><div class="row between" style="padding:16px 16px 8px"><h2 id="mapCount" style="font-size:17px">Properties</h2>
      <select class="select" id="mSort" style="height:32px"><option value="score">Sort by: Deal Score</option><option value="owed">Taxes owed</option><option value="equity">Equity</option><option value="newest">Newest</option></select></div>
      <div class="items" id="mItems"></div>
      <div class="row" style="justify-content:center;padding:10px;border-top:1px solid var(--line)"><button class="btn sm" id="mPrev">${ic('left', 15)}</button><span class="small muted" id="mPage" style="min-width:90px;text-align:center"></span><button class="btn sm" id="mNext">${ic('right', 15)}</button></div></div>
    <div class="map-area"><div id="bigMap"></div>
      <div class="map-filters">
        ${countySelect('mCounty')}
        <select class="select" id="fs"><option value="">Score: any</option><option value="65">Score: 65+</option><option value="80" selected>Score: 80+</option><option value="85">Score: 85+</option></select>
        <select class="select" id="fe"><option value="">Equity: any</option><option value="30000" selected>Equity: $30K+</option><option value="50000">Equity: $50K+</option><option value="100000">Equity: $100K+</option></select>
        <select class="select" id="fy"><option value="">Years behind: any</option><option value="2" selected>Years behind: 2+</option><option value="3">Years behind: 3+</option></select>
        <select class="select" id="ft"><option value="homes">Property type: Homes</option><option value="all">All types</option><option>Vacant land</option><option>Commercial</option><option>Agricultural</option></select>
        <button class="btn ghost sm" id="fClear">Clear</button><span class="grow"></span><span class="small muted" id="resN"></span>
        <button class="btn sm" id="saveSearch">${ic('bookmark', 15)} Save Search</button>
      </div>
      <div class="legend"><span><i style="background:#1F7A45"></i>85+ (High)</span><span><i style="background:${AMBER}"></i>65-84 (Medium)</span><span><i style="background:${GREY}"></i>Below 65 (Low)</span></div>
    </div></div>`;
  try { Object.assign(st, JSON.parse(localStorage.getItem('eh_map_search') || '{}')); } catch (e) { }
  $('#fs').value = st.min_score; $('#fe').value = st.min_equity; $('#fy').value = st.min_years; $('#ft').value = st.ptype; $('#mSort').value = st.sort;
  const L = window.L;
  const map = L.map('bigMap', { zoomControl: false }).setView([40.3, -82.4], 8);
  L.control.zoom({ position: 'bottomright' }).addTo(map);
  baseTiles(map);
  const layer = L.layerGroup().addTo(map);
  let pts = [], page = 1, markers = {};
  const PER = 20;
  async function load(fit = true) {
    const q = { county: S.county, min_score: st.min_score, min_equity: st.min_equity, min_years: st.min_years, ptype: st.ptype, sort: st.sort };
    pts = await api('/api/map?' + Object.entries(q).filter(([, v]) => v).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&'));
    if (st.sort !== 'score') { const key = { owed: (p) => -(p.total_due ?? p.amount_owed), equity: (p) => -(p.est_equity || 0), newest: (p) => -new Date(p.first_seen) }[st.sort]; pts.sort((a, b) => key(a) - key(b)); }
    layer.clearLayers(); markers = {};
    pts.forEach((p) => { markers[p.id] = pin(p).bindPopup(popupHtml(p), { maxWidth: 320 }).addTo(layer); });
    if (fit && pts.length) map.fitBounds(L.latLngBounds(pts.map((p) => [p.lat, p.lng])).pad(.1));
    $('#mapCount').textContent = `Properties (${num(pts.length)})`;
    $('#resN').textContent = `${num(pts.length)} results`;
    page = 1; list();
  }
  function list() {
    const items = pts.slice((page - 1) * PER, page * PER);
    $('#mItems').innerHTML = items.map((p) => `<div class="pcard" data-id="${esc(p.id)}">${thumb(p, 'lg')}<div class="grow"><b>${esc(title(p.street))}</b><div class="small muted">${esc(place(p))}</div>${homeLine(p) ? `<div class="tiny" style="color:var(--ink2);margin-top:2px">${homeLine(p)}</div>` : ''}
      <div class="meta"><div><b class="num">${money(p.total_due ?? p.amount_owed)}</b><span class="tiny muted">Taxes owed</span></div><div><b>${yrs(p.years_behind)}</b><span class="tiny muted">Years behind</span></div></div></div>${scorePill(p.score)}</div>`).join('') || '<div class="empty small">No properties match. Try fewer filters.</div>';
    const pages = Math.max(1, Math.ceil(pts.length / PER));
    $('#mPage').textContent = `${page} / ${pages}`;
    $('#mPrev').disabled = page <= 1; $('#mNext').disabled = page >= pages;
  }
  $('#mItems').onclick = (e) => { const c = e.target.closest('.pcard'); if (!c) return; const m = markers[c.dataset.id]; $$('.pcard').forEach((x) => x.classList.toggle('on', x === c)); if (m) { map.setView(m.getLatLng(), Math.max(map.getZoom(), 15)); m.openPopup(); } };
  $('#mItems').ondblclick = (e) => { const c = e.target.closest('.pcard'); if (c) location.hash = '#/deal/' + encodeURIComponent(c.dataset.id); };
  $('#mPrev').onclick = () => { page--; list(); }; $('#mNext').onclick = () => { page++; list(); };
  const bind = (sel, key) => $(sel).onchange = (e) => { st[key] = e.target.value; load(); };
  bind('#fs', 'min_score'); bind('#fe', 'min_equity'); bind('#fy', 'min_years'); bind('#ft', 'ptype');
  $('#mSort').onchange = (e) => { st.sort = e.target.value; load(false); };
  $('#mCounty').onchange = (e) => { setCounty(e.target.value); load(); };
  $('#fClear').onclick = () => { Object.assign(st, { min_score: '', min_equity: '', min_years: '', ptype: 'all' }); ['#fs', '#fe', '#fy'].forEach((s) => $(s).value = ''); $('#ft').value = 'all'; load(); };
  $('#saveSearch').onclick = () => { try { localStorage.setItem('eh_map_search', JSON.stringify(st)); } catch (e) { } toast('Search saved. It opens with these filters next time.'); };
  const fitH = () => { const w = $('.map-wrap'); if (w && innerWidth > 900) { w.style.height = Math.max(560, innerHeight - w.getBoundingClientRect().top - window.scrollY - 18) + 'px'; map.invalidateSize(); } };
  fitH(); addEventListener('resize', fitH);
  await load();
  setTimeout(() => map.invalidateSize(), 50);
  return () => { map.remove(); el.style.padding = ''; removeEventListener('resize', fitH); };
}
