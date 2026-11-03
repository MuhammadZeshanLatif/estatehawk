// Alerts, Counties, Outreach, Reports, Settings, Onboarding
import {
  $, $$, esc, ic, api, money, kmoney, num, title, yrs, scorePill, ago, fmtDate, tileUrl, place, thumb,
  toast, modal, menu, S, setCounty, refreshMeta, countySelect, countyName, watchSync, plansModal, teamModal, setViewOrg,
} from './app.js';
import { alertIcon, baseTiles, taskModal, scoreColor } from './views.js';

const tog = (id, on) => `<label class="toggle"><input type="checkbox" id="${id}" ${on ? 'checked' : ''}><span></span></label>`;
const lastUpdatedBox = () => `<div class="updated-box">${ic('cal', 18)}<div><div class="small" style="font-weight:600">${fmtDate(new Date())}</div><div class="tiny muted">Last updated ${ago(S.meta.last_sync)}</div></div></div>`;

// ================================================================ ALERTS
export async function alerts(el) {
  let tab = 'all';
  const s = S.meta.settings;
  el.innerHTML = `
  <div class="page-head"><div><h1>Alerts</h1><div class="sub">Get notified about new opportunities, changes, and important updates in your target counties.</div></div>
    <div class="right"><div class="row">${ic('pin', 18)}${countySelect('aCounty')}</div>${lastUpdatedBox()}</div></div>
  <div class="alerts-grid">
    <div style="min-width:0"><div class="row between"><div class="tabs grow" id="aTabs"></div><button class="btn sm" id="readAll" style="margin-left:12px">${ic('check', 15)} Mark all read</button></div>
      <div class="card" id="feed"></div></div>
    <div class="col" style="gap:18px">
      <div class="card card-pad"><h3>Alert rules</h3><div class="small muted" style="margin-bottom:8px">Get notified when properties match your criteria.</div>
        <div class="rule">${tog('rScore', s.alert_rules.score_above)}<span class="grow">Score above</span><input class="input" id="rScoreV" value="${s.alert_rules.score_min}"></div>
        <div class="rule">${tog('rEq', s.alert_rules.equity_above)}<span class="grow">Equity above</span><input class="input" id="rEqV" value="${num(s.alert_rules.equity_min)}"></div>
        <div class="rule">${tog('rNew', s.alert_rules.new_in_counties)}<span class="grow">New delinquent in my counties<div class="tiny muted">Any property newly delinquent</div></span></div>
        <div class="rule">${tog('rAuc', s.alert_rules.auction_within)}<span class="grow">Auction within</span><input class="input" id="rAucV" value="${s.alert_rules.auction_days}" style="width:64px"><span class="small muted">days</span></div>
      </div>
      <div class="card card-pad"><h3>Notification channels</h3><div class="small muted" style="margin-bottom:6px">Choose how you want to receive alerts.</div>
        ${[['email', 'mail', 'Email'], ['sms', 'sms', 'SMS'], ['slack', 'hash', 'Slack'], ['whatsapp', 'phone', 'WhatsApp']].map(([k, i, l]) => `<div class="rule">${ic(k === 'slack' ? 'layers' : i, 18)}<span class="grow">${l}${S.meta.integrations[k] ? '' : ` <a class="tiny" style="color:var(--green)" href="#/settings/integrations">Set up</a>`}</span>${tog('ch_' + k, s.channels[k])}</div>`).join('')}
        <div style="border-top:1px solid var(--line);margin-top:8px;padding-top:12px">
          <div class="rule"><b class="grow">Daily digest</b>${tog('dEn', s.digest.enabled)}</div>
          <div class="small muted">Receive a summary of new opportunities.</div>
          <div class="row" style="margin-top:10px">${ic('clock', 16)}<select class="select" id="dTime">${Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, '0')}:00`).map((t) => `<option ${t === s.digest.time ? 'selected' : ''}>${t}</option>`).join('')}</select>
            <button class="btn xs" id="dTest">Send test</button></div>
        </div></div>
    </div></div>`;
  const TABS = [['all', 'All'], ['new_delinquent', 'New delinquent'], ['auction', 'Auction dates'], ['owner_change', 'Owner changes'], ['equity', 'Equity changes']];
  async function load() {
    const r = await api(`/api/alerts?type=${tab}&county=${S.county}`);
    const c = r.counts, all = Object.values(c).reduce((a, b) => a + b, 0);
    const cnt = { all, new_delinquent: c.new_delinquent || 0, auction: c.auction || 0, owner_change: c.owner_change || 0, equity: (c.amount_up || 0) + (c.high_score || 0) };
    $('#aTabs').innerHTML = TABS.map(([k, l]) => `<a data-t="${k}" class="${tab === k ? 'on' : ''}">${l} (${cnt[k]})</a>`).join('');
    const today = new Date().toISOString().slice(0, 10), yest = new Date(Date.now() - 864e5).toISOString().slice(0, 10);
    const groups = { Today: [], Yesterday: [], Earlier: [] };
    r.rows.forEach((a) => groups[a.ts.startsWith(today) ? 'Today' : a.ts.startsWith(yest) ? 'Yesterday' : 'Earlier'].push(a));
    $('#feed').innerHTML = Object.entries(groups).filter(([, v]) => v.length).map(([g, rows]) => `<div class="feed-group">${g}</div>` + rows.map((a) => `
      <div class="feed-row" data-id="${a.id}" data-p="${esc(a.parcel_id || '')}"><span class="${a.read ? '' : 'unread'}"></span>${alertIcon(a.type).replace('border-radius:50%', 'border-radius:10px;width:38px;height:38px')}
        <div style="min-width:0"><b style="font-weight:600">${esc(a.title)}</b><div class="small muted" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(a.body || '')}</div></div>
        <span class="small muted c4">${esc(a.county_name || '')}</span><span class="small muted c5">${g === 'Earlier' || g === 'Yesterday' ? fmtDate(a.ts, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : ago(a.ts)}</span>
        <span>${a.score != null ? scorePill(a.score) : ''}</span><a class="small" style="color:var(--green);font-weight:600" ${a.parcel_id ? `href="#/deal/${encodeURIComponent(a.parcel_id)}"` : 'href="#/counties"'}>View</a>
        <button class="icon-btn more" style="width:30px;height:30px">${ic('dots', 16)}</button></div>`).join('')).join('') || '<div class="empty">No alerts here yet. They appear after each nightly sync.</div>';
  }
  $('#aTabs').onclick = (e) => { const a = e.target.closest('[data-t]'); if (a) { tab = a.dataset.t; load(); } };
  $('#aCounty').onchange = (e) => { setCounty(e.target.value); load(); };
  $('#feed').onclick = async (e) => {
    const row = e.target.closest('.feed-row'); if (!row) return;
    if (e.target.closest('.more')) { e.stopPropagation(); return menu(e.target.closest('.more'), [{ label: 'Mark as read', icon: 'check', fn: async () => { await api('/api/alerts/read', { method: 'POST', body: { ids: [row.dataset.id] } }); load(); refreshMeta(); } }]); }
    await api('/api/alerts/read', { method: 'POST', body: { ids: [row.dataset.id] } });
    if (!e.target.closest('a') && row.dataset.p) location.hash = '#/deal/' + encodeURIComponent(row.dataset.p);
  };
  $('#readAll').onclick = async () => { await api('/api/alerts/read', { method: 'POST', body: { all: true } }); await refreshMeta(); load(); };
  const save = async () => {
    const st = S.meta.settings;
    const rules = { score_above: $('#rScore').checked, score_min: +$('#rScoreV').value || 85, equity_above: $('#rEq').checked, equity_min: +$('#rEqV').value.replace(/[^0-9]/g, '') || 0,
      new_in_counties: $('#rNew').checked, auction_within: $('#rAuc').checked, auction_days: +$('#rAucV').value || 30 };
    const channels = Object.fromEntries(['email', 'sms', 'slack', 'whatsapp'].map((k) => [k, $('#ch_' + k).checked]));
    const digest = { enabled: $('#dEn').checked, time: $('#dTime').value };
    st.alert_rules = rules; st.channels = channels; st.digest = digest;
    await api('/api/settings', { method: 'PUT', body: { alert_rules: rules, channels, digest } });
    toast('Alert settings saved');
    ['email', 'sms', 'slack', 'whatsapp'].forEach((k) => { if (channels[k] && !S.meta.integrations[k]) toast(`${k.toUpperCase()} is on but not set up yet (Settings > Integrations)`, true); });
  };
  $$('.alerts-grid input, .alerts-grid select').forEach((i) => i.onchange = save);
  $('#dTest').onclick = async () => { const r = await api('/api/integrations/test/digest', { method: 'POST' }); modal(`<h2>Digest preview</h2><pre class="email-box">${esc(r.message)}</pre><div class="small muted">${Object.keys(r.sent || {}).length ? 'Sent: ' + esc(JSON.stringify(r.sent)) : 'No channel is switched on and set up, so nothing was sent.'}</div><div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn" data-close>Close</button></div>`); };
  await load();
}

// ================================================================ COUNTIES
function countyShape(name) {
  // simple deterministic outline so each county card has its own silhouette
  let h = 0; for (const c of name) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  const r = (n) => { h = (h * 1103515245 + 12345) >>> 0; return (h % 1000) / 1000 * n; };
  const pts = [[8 + r(8), 6 + r(6)], [30 + r(10), 4 + r(4)], [50 - r(6), 10 + r(8)], [52 - r(4), 30 + r(8)], [44 - r(6), 50 - r(4)], [26 + r(8), 52 - r(4)], [10 + r(6), 44 - r(8)], [6 + r(4), 24 + r(6)]];
  return `<svg class="shape" viewBox="0 0 56 56"><path d="M${pts.map((p) => p.map((v) => v.toFixed(1)).join(' ')).join(' L')} Z" fill="#DCEFE1" stroke="#2E7D4F" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
}
function spark(vals, color = '#1F7A45') {
  const w = 300, h = 70, max = Math.max(...vals, 1), n = vals.length;
  const pts = vals.map((v, i) => [i / (n - 1) * w, h - 6 - v / max * (h - 14)]);
  const line = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><path d="${line} L${w} ${h} L0 ${h} Z" fill="${color}" opacity=".1"/><path d="${line}" fill="none" stroke="${color}" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>`;
}
export async function counties(el) {
  const rows = await api('/api/counties');
  const hide = localStorage.getItem('eh_hide_banner') === '1';
  el.innerHTML = `${hide ? '' : `<div class="info-banner">${ic('db', 18)}<span>Data refreshes every night from official county records.</span><span class="small muted" style="margin-left:auto">Last full update: ${S.meta.last_sync ? fmtDate(S.meta.last_sync, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }) : 'not yet'}</span><button class="icon-btn" id="hideBanner" style="width:28px;height:28px">${ic('x', 15)}</button></div>`}
  <div class="page-head"><div><div class="row"><h1>My counties</h1><span class="pill p-green">${rows.filter((r) => r.enabled).length} tracking</span></div><div class="sub">Track tax-delinquent properties in your target counties.</div></div>
    <div class="right"><div data-sync-status></div><div class="search" style="width:260px">${ic('search', 16)}<input id="cQ" placeholder="Search counties..."></div>
      ${S.meta.super ? `<button class="btn" id="syncAll">${ic('refresh', 16)} Sync all</button><button class="btn primary" id="addCounty">${ic('plus', 16)} Add county</button>` : `<button class="btn primary" id="moreCounties">${ic('plus', 16)} Add more counties</button>`}</div></div>
  <div class="county-grid" id="cGrid"></div>`;
  const statusPill = (c) => ({ synced: `<span class="pill p-green">${ic('check', 13)} Synced</span>`, syncing: `<span class="pill p-amber">${ic('refresh', 13)} Syncing</span>`,
    error: `<span class="pill p-red">${ic('alert', 13)} Error</span>`, never: `<span class="pill p-grey">Not synced</span>` }[c.sync_status] || `<span class="pill p-grey">${esc(c.sync_status)}</span>`);
  const draw = (q = '') => {
    $('#cGrid').innerHTML = rows.filter((c) => c.name.toLowerCase().includes(q.toLowerCase())).map((c) => `
      <div class="card county" style="${c.enabled ? '' : 'opacity:.55'}"><div class="row" style="align-items:flex-start">${countyShape(c.name)}
        <div class="grow" style="min-width:0"><div class="row between" style="align-items:flex-start"><h3 style="font-size:16px">${esc(c.name)}, ${esc(c.state)}</h3><button class="icon-btn more" data-id="${c.id}" style="width:28px;height:28px;margin:-4px -6px 0 0">${ic('dots', 16)}</button></div>
        <div class="row between" style="margin-top:4px"><span class="small muted">Source: County Treasurer</span>${statusPill(c)}</div></div></div>
        <div class="tiny muted" style="text-align:right;margin-top:4px">${c.sync_status === 'error' ? `<a class="small retry" data-id="${c.id}" style="color:var(--blue);cursor:pointer">${ic('refresh', 13)} Retry sync</a><br>` : ''}Last sync: ${c.last_sync ? fmtDate(c.last_sync, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }) : 'never'}</div>
        ${c.sync_status === 'error' ? `<div class="small" style="color:var(--red);margin-top:4px">${esc(c.sync_error || '')}</div>` : ''}
        <div class="row between" style="margin-top:8px"><div><div class="big num">${num(c.active)}</div><div class="small muted">Delinquent properties</div></div>
          <span class="pill ${c.new_today ? 'p-green' : 'p-grey'}">${ic('trend', 13)} +${c.new_today} new today</span></div>
        <div class="tiny muted" style="margin-top:12px">New delinquent properties (30 days)${c.tax_sale_date ? ` · Tax sale ${fmtDate(c.tax_sale_date)}` : ''}</div>
        ${spark(c.spark, c.sync_status === 'error' ? '#C2410C' : c.sync_status === 'syncing' ? '#D49A2A' : '#1F7A45')}
      </div>`).join('') || `<div class="card empty" style="grid-column:1/-1">No counties yet. Click <b>Add county</b>.</div>`;
  };
  draw();
  if ($('#hideBanner')) $('#hideBanner').onclick = () => { try { localStorage.setItem('eh_hide_banner', '1'); } catch (e) { } $('.info-banner').remove(); };
  $('#cQ').oninput = (e) => draw(e.target.value);
  const syncIds = async (ids) => { const r = await api('/api/sync', { method: 'POST', body: { ids } }); if (!r.ok) return toast(r.error, true); toast('Sync started'); setTimeout(() => counties(el), 800); watchSync(() => counties(el)); };
  if ($('#syncAll')) $('#syncAll').onclick = () => syncIds(null);
  if ($('#moreCounties')) $('#moreCounties').onclick = () => plansModal(`Your ${S.meta.org.label} plan includes ${S.meta.org.limits.counties ?? 'all'} county(ies).`);
  $('#cGrid').onclick = (e) => {
    const rt = e.target.closest('.retry'); if (rt) return syncIds([+rt.dataset.id]);
    const b = e.target.closest('.more'); if (!b) return;
    e.stopPropagation();
    const c = rows.find((x) => x.id === +b.dataset.id);
    if (!S.meta.super) return menu(b, [{ label: 'Show leads', icon: 'home', fn: () => { setCounty(c.id); location.hash = '#/deals'; } }]);
    menu(b, [
      { label: 'Sync now', icon: 'refresh', fn: () => syncIds([c.id]) },
      { label: 'Edit (website, tax sale date)', icon: 'edit', fn: () => countyModal(c) },
      { label: c.enabled ? 'Pause tracking' : 'Resume tracking', icon: 'clock', fn: async () => { await api('/api/counties/' + c.id, { method: 'PUT', body: { enabled: c.enabled ? 0 : 1 } }); await refreshMeta(); counties(el); } },
      { label: 'Show leads', icon: 'home', fn: () => { setCounty(c.id); location.hash = '#/deals'; } },
      ...(c.host ? [{ label: 'Open county website', icon: 'link', fn: () => open(`https://${c.host}/DelinquentList`, '_blank') }] : []),
      '-', { label: 'Remove', icon: 'x', danger: true, fn: async () => { if (!confirm('Remove ' + c.name + '?')) return; await api('/api/counties/' + c.id, { method: 'DELETE' }); await refreshMeta(); counties(el); } },
    ]);
  };
  if ($('#addCounty')) $('#addCounty').onclick = () => countyModal(null);
  async function countyModal(c) {
    const known = c ? [] : await api('/api/known-counties');
    modal(`<h2>${c ? 'Edit county' : 'Add county'}</h2><div style="height:12px"></div>
      ${c ? '' : `<div class="field"><label>Pick a supported county</label><select class="select" id="kPick"><option value="">Custom...</option>${known.map((k, i) => `<option value="${i}" ${k.added ? 'disabled' : ''}>${esc(k.name)}, ${k.state}${k.added ? ' (added)' : k.verified ? '' : ' (website not verified)'}</option>`).join('')}</select>
        <div class="hint">Ohio counties on the ISSG treasurer platform work out of the box.</div></div>`}
      <div class="terms"><div class="field"><label>County name</label><input class="input" id="kName" value="${esc(c?.name || '')}"></div>
      <div class="field"><label>State</label><input class="input" id="kState" value="${esc(c?.state || 'OH')}"></div></div>
      <div class="field"><label>Delinquent list website</label><input class="input" id="kHost" placeholder="treasurer.example-county.gov" value="${esc(c?.host || '')}"><div class="hint">The site where /DelinquentList opens.</div></div>
      <div class="field"><label>Next tax sale / auction date (optional)</label><input class="input" type="date" id="kSale" value="${esc(c?.tax_sale_date || '')}"></div>
      <div class="small" id="kTestRes"></div>
      <div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn" id="kTest">Test connection</button><button class="btn" data-close>Cancel</button><button class="btn primary" id="kSave">${c ? 'Save' : 'Add county'}</button></div>`, (m, close) => {
      if ($('#kPick', m)) $('#kPick', m).onchange = (e) => { const k = known[+e.target.value]; if (!k) return; $('#kName', m).value = k.name; $('#kState', m).value = k.state; $('#kHost', m).value = k.host; m._k = k; };
      $('#kTest', m).onclick = async () => { $('#kTestRes', m).textContent = 'Testing...'; const r = await api('/api/counties/test', { method: 'POST', body: { host: $('#kHost', m).value } });
        $('#kTestRes', m).innerHTML = r.ok ? `<span style="color:var(--green-ink)">Connected: ${r.townships} townships, about ${num(r.parcels)} delinquent parcels.</span>` : `<span style="color:var(--red)">Could not read the list: ${esc(r.error)}</span>`; };
      $('#kSave', m).onclick = async () => {
        const body = { name: $('#kName', m).value, state: $('#kState', m).value, host: $('#kHost', m).value, tax_sale_date: $('#kSale', m).value, lat: m._k?.lat, lng: m._k?.lng };
        if (c) await api('/api/counties/' + c.id, { method: 'PUT', body }); else await api('/api/counties', { method: 'POST', body });
        close(); await refreshMeta(); toast(c ? 'Saved' : 'County added. Click Sync now to download its list.'); counties(el);
      };
    });
  }
  if (S.meta.sync.running) watchSync(() => counties(el));
}

// ================================================================ OUTREACH
export async function outreach(el) {
  const od = S.meta.settings.offer_defaults;
  el.innerHTML = `
  <div class="page-head"><div><h1>Outreach Pipeline</h1><div class="sub">Turn your leads into deals with organized follow-ups and outreach.</div></div></div>
  <div class="kanban-wrap"><div style="min-width:0">
    <div class="row wrap" style="margin-bottom:14px"><div class="search" style="width:260px">${ic('search', 16)}<input id="oQ" placeholder="Search leads in pipeline..."></div>
      <div class="row">${ic('pin', 16)}${countySelect('oCounty')}</div>
      <div class="row">${ic('mail', 16)}<select class="select" id="oSeq">${['Tax-delinquent v1', 'Tax-delinquent v2'].map((s) => `<option ${s === od.sequence ? 'selected' : ''}>Sequence: ${s}</option>`).join('')}</select></div>
      <button class="btn primary" id="batch">${ic('send', 15)} Send batch emails</button></div>
    <div class="kanban" id="kanban"></div></div>
    <div class="col" style="gap:18px">
      <div class="card card-pad"><div class="row between"><div class="row"><h3>Follow-ups today</h3><span class="pill p-grey" id="fuN">0</span></div><button class="btn xs" id="addFu">${ic('plus', 13)}</button></div><div id="fuList" style="margin-top:6px"></div></div>
      <div class="card card-pad"><div class="row">${'<span class="ico tone-green" style="width:40px;height:40px;border-radius:50%;display:grid;place-items:center">' + ic('chart', 18) + '</span>'}<div><div class="small" style="font-weight:600">Reply rate this week</div><div class="row"><b style="font-size:26px" id="rr">0%</b></div><div class="tiny muted" id="rrSub"></div></div></div>
        <div class="row between" style="margin-top:14px;padding-top:12px;border-top:1px solid var(--line)"><h3>Recent replies</h3></div><div id="replies"></div></div>
    </div></div>`;
  const kIcon = { email: 'mail', call: 'phone', sms: 'sms', letter: 'letter', reply: 'sms', stage: 'right', note: 'note' };
  async function load() {
    const r = await api(`/api/pipeline?county=${S.county}&q=${encodeURIComponent($('#oQ').value)}`);
    $('#kanban').innerHTML = r.columns.map((c) => `<div class="kcol" data-stage="${c.key}"><div class="khead k-${c.key}">${esc(c.label)}<span class="n">${c.items.length}</span></div>
      <div class="kitems">${c.items.map((p) => { const [k, ts, txt] = (p.last || '||').split('|'); return `<div class="kcard" draggable="true" data-id="${esc(p.parcel_id)}">
        <div class="top">${thumb(p)}<div class="grow" style="min-width:0"><b style="font-size:13px">${esc(title(p.street))}</b><div class="tiny muted">${esc(place(p))}</div></div></div>
        <div class="owner"><span>${esc(title(p.owner_name).slice(0, 22))}</span>${scorePill(p.score)}</div>
        <div class="last" style="color:${k === 'reply' ? 'var(--green-ink)' : k ? 'var(--blue)' : 'var(--mute)'}">${ic(kIcon[k] || 'clock', 13)}<span class="grow" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${k ? esc(txt) : 'Not contacted yet'}</span>${ts ? `<span class="tiny muted">${ago(ts)}</span>` : ''}</div></div>`; }).join('')}</div></div>`).join('');
    $('#rr').textContent = r.reply_rate + '%';
    $('#rrSub').textContent = `${r.replies_week} replies from ${r.contacts_week} contacts`;
    $('#replies').innerHTML = r.recent_replies.map((a) => `<a class="act" href="#/deal/${encodeURIComponent(a.parcel_id)}"><span class="avatar" style="background:#E3EEE6;color:var(--green-ink)">${esc((a.author || '?')[0])}</span><div class="grow"><b class="small">${esc(a.author || '')}</b><div class="tiny muted">${esc(title(a.street))}</div><div class="small">"${esc(a.text)}"</div></div><span class="tiny muted">${ago(a.ts)}</span></a>`).join('') || '<div class="small muted" style="padding:10px 0">No replies yet</div>';
    const tasks = await api('/api/tasks');
    const open_ = tasks.filter((t) => !t.done);
    $('#fuN').textContent = open_.length;
    $('#fuList').innerHTML = tasks.slice(0, 8).map((t) => `<div class="task"><input type="checkbox" data-t="${t.id}" ${t.done ? 'checked' : ''}>${ic(kIcon[t.kind] || 'clock', 16)}<div class="grow" style="${t.done ? 'text-decoration:line-through;color:var(--mute)' : ''}"><div class="small" style="font-weight:600">${esc(t.text)}</div><div class="tiny muted">${esc(title(t.street || ''))}</div></div><span class="tiny muted">${fmtDate(t.due, { month: 'short', day: 'numeric' })}</span></div>`).join('') || '<div class="small muted" style="padding:10px 0">Nothing due. Add follow-ups from a deal.</div>';
    $$('[data-t]').forEach((c) => c.onchange = async () => { await api('/api/tasks/' + c.dataset.t, { method: 'PUT', body: { done: c.checked } }); load(); });
  }
  // drag and drop
  let dragId = null;
  $('#kanban').addEventListener('dragstart', (e) => { const c = e.target.closest('.kcard'); if (c) { dragId = c.dataset.id; e.dataTransfer.effectAllowed = 'move'; } });
  $('#kanban').addEventListener('dragover', (e) => { const col = e.target.closest('.kcol'); if (col) { e.preventDefault(); $$('.kcol').forEach((k) => k.classList.toggle('drop', k === col)); } });
  $('#kanban').addEventListener('drop', async (e) => {
    const col = e.target.closest('.kcol'); $$('.kcol').forEach((k) => k.classList.remove('drop'));
    if (!col || !dragId) return; e.preventDefault();
    let fee = null;
    if (col.dataset.stage === 'closed') { fee = prompt('Assignment fee earned ($)?', '10000'); if (fee == null) return; }
    await api(`/api/parcels/${encodeURIComponent(dragId)}/stage`, { method: 'POST', body: { stage: col.dataset.stage, fee: fee ? +fee : null } });
    dragId = null; load();
  });
  $('#kanban').addEventListener('click', (e) => { const c = e.target.closest('.kcard'); if (c) location.hash = '#/deal/' + encodeURIComponent(c.dataset.id); });
  let qt; $('#oQ').oninput = () => { clearTimeout(qt); qt = setTimeout(load, 250); };
  $('#oCounty').onchange = (e) => { setCounty(e.target.value); load(); };
  $('#oSeq').onchange = async (e) => { const v = e.target.value.replace('Sequence: ', ''); S.meta.settings.offer_defaults.sequence = v; await api('/api/settings', { method: 'PUT', body: { offer_defaults: S.meta.settings.offer_defaults } }); toast('Sequence saved'); };
  $('#addFu').onclick = () => taskModal(null, load);
  $('#batch').onclick = () => {
    const n = $('[data-stage=new] .kcard') ? $$('[data-stage=new] .kcard').length : 0;
    modal(`<h2>Send batch offers</h2><p class="muted">Creates an offer draft for every lead in <b>New lead</b> (${n}) using your default terms, then opens printable letters addressed to each owner's tax-bill mailing address.</p>
      <div class="card card-pad small" style="background:#FAFAF8">County records have mailing addresses but no owner emails or phones. Mail the letters, or skip-trace first to email/text them.</div>
      ${S.meta.integrations.gemini ? `<label class="row" style="margin-top:12px"><input type="checkbox" id="bAi"> Write each one with Gemini (slower)</label>` : ''}
      <div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-close>Cancel</button><button class="btn primary" id="bGo" ${n ? '' : 'disabled'}>Create ${n} drafts</button></div>`, (m, close) => {
      $('#bGo', m).onclick = async () => {
        $('#bGo', m).disabled = true; $('#bGo', m).textContent = 'Working...';
        const r = await api('/api/batch-offers', { method: 'POST', body: { ai: $('#bAi', m)?.checked } });
        close(); toast(`${r.count} drafts ready`); open('/letters?ids=' + encodeURIComponent(r.ids.join(',')));
      };
    });
  };
  await load();
}

// ================================================================ REPORTS
export async function reports(el) {
  let days = 30;
  el.innerHTML = `<div class="page-head"><div><h1>Reports</h1><div class="sub">Track your performance, pipeline, and revenue from tax-delinquent deals.</div></div>
    <div class="right no-print"><div class="updated-box">${ic('cal', 18)}<div><select class="select" id="rDays" style="border:0;height:24px;padding-left:0;font-weight:600"><option value="7">Last 7 days</option><option value="30" selected>Last 30 days</option><option value="90">Last 90 days</option></select><div class="tiny muted" id="rSpan"></div></div></div>
      <a class="btn" id="rCsv">${ic('download', 16)} Export CSV</a><button class="btn primary" id="rPdf">${ic('doc', 16)} Export PDF</button></div></div>
    <div class="grid kpis" id="kpis"></div>
    <div class="reports-mid">
      <div class="card card-pad"><div class="row between"><h3>New leads per day</h3><div class="row small" id="legend"></div></div><div class="chart-box" style="margin-top:10px"><canvas id="lineC"></canvas></div></div>
      <div class="card card-pad"><h3>Leads by county</h3><div id="hbars" style="margin-top:10px"></div></div>
      <div class="card card-pad"><h3>Lead to deal</h3><div id="funnel"></div></div>
    </div>
    <div class="card" style="margin-top:18px"><div class="card-head" style="padding-bottom:10px"><h3>Top deals this month</h3><a class="btn sm right" href="#/outreach">View all deals</a></div>
      <div style="overflow-x:auto"><table class="table"><thead><tr><th>#</th><th>Property</th><th>Owner</th><th class="hide-m">County</th><th class="r">Est. value</th><th class="r hide-m">Est. equity</th><th class="r">Fee</th><th class="hide-m">Date</th><th>Status</th></tr></thead><tbody id="topT"></tbody></table></div></div>`;
  const COLORS = ['#1F6B3A', '#E0A030', '#8C938F', '#5B8DEF', '#B36BD6', '#2BA59A'];
  let chart;
  async function load() {
    const r = await api(`/api/reports?days=${days}&county=${S.county}`);
    $('#rSpan').textContent = `${fmtDate(r.labels[0])} - ${fmtDate(r.labels[r.labels.length - 1])}`;
    $('#rCsv').href = `/api/reports/export.csv?days=${days}`;
    const k = r.kpi;
    const bars = (seed) => { let h = seed; return Array.from({ length: 12 }, () => { h = (h * 9301 + 49297) % 233280; return 4 + h / 233280 * 16; }).map((v, i) => `<i style="display:inline-block;width:3px;margin-right:2px;height:${v + i}px;background:#1F6B3A;opacity:.55;border-radius:1px"></i>`).join(''); };
    $('#kpis').innerHTML = [
      ['doc', 'tone-green', 'Leads found', num(k.found), k.found_change != null ? `<span class="chg" style="margin:0">${ic('up', 12)} ${k.found_change}%</span> vs previous ${days} days` : `last ${days} days`],
      ['mail', 'tone-blue', 'Contacted', num(k.contacted), `${k.found ? Math.round(k.contacted * 100 / Math.max(k.found, 1)) : 0}% of leads found`],
      ['sms', 'tone-amber', 'Replies', num(k.replied), `${k.reply_rate}% reply rate`],
      ['dollar', 'tone-green', 'Deals closed', num(k.closed), `${money(k.fees)} in fees`],
    ].map(([i, t, l, v, f], n) => `<div class="card stat"><span class="ico ${t}" style="border-radius:50%">${ic(i, 20)}</span><div class="grow"><div class="lbl">${l}</div><div class="val num">${v}</div><div class="foot">${f}</div></div><div style="align-self:flex-end;display:flex;align-items:flex-end;height:36px">${bars(n * 7 + k.found)}</div></div>`).join('');
    const names = Object.keys(r.per_day);
    const top = names.sort((a, b) => r.per_day[b].reduce((x, y) => x + y, 0) - r.per_day[a].reduce((x, y) => x + y, 0));
    const series = top.slice(0, 2).map((n) => [n, r.per_day[n]]);
    if (top.length > 2) series.push(['Other', r.labels.map((_, i) => top.slice(2).reduce((s, n) => s + r.per_day[n][i], 0))]);
    $('#legend').innerHTML = series.map(([n], i) => `<span class="row gap6"><i style="width:9px;height:9px;border-radius:50%;background:${COLORS[i]}"></i>${esc(n.replace(' County', ''))}</span>`).join('');
    chart && chart.destroy();
    chart = new window.Chart($('#lineC'), {
      type: 'line', data: { labels: r.labels.map((d) => fmtDate(d, { month: 'short', day: 'numeric' })), datasets: series.map(([n, v], i) => ({ label: n, data: v, borderColor: COLORS[i], backgroundColor: i === 0 ? 'rgba(31,107,58,.08)' : 'transparent', fill: i === 0, tension: .35, pointRadius: 0, borderWidth: 2 })) },
      options: { maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } }, interaction: { mode: 'index', intersect: false },
        scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 7, color: '#7A847F', font: { size: 11 } } }, y: { beginAtZero: true, grid: { color: '#F0F0EC' }, ticks: { precision: 0, color: '#7A847F', font: { size: 11 } } } } },
    });
    const maxC = Math.max(...r.by_county.map((c) => c.n), 1);
    $('#hbars').innerHTML = r.by_county.map((c, i) => `<div class="hbar"><span class="muted">${esc(c.name.replace(' County', ' County, OH'))}</span><div><div class="t" style="width:${c.n / maxC * 100}%;background:${['#1F6B3A', '#E0A030', '#4E8F68', '#8DBE9E', '#B9DCC4', '#D7EBDD'][i % 6]}"></div></div><b class="num" style="text-align:right">${num(c.n)}</b></div>`).join('');
    const f0 = Math.max(r.funnel[0][1], 1);
    const fc = [['#1F6B3A', '#fff'], ['#BFE0C9', '#163'], ['#FBE3A6', '#6B4A0E'], ['#FCEFD0', '#6B4A0E'], ['#FDF6E6', '#6B4A0E']];
    $('#funnel').innerHTML = `<div class="funnel">${r.funnel.map(([l, v], i) => `<div class="funnel-row"><div style="display:flex;justify-content:center"><div class="lvl" style="width:${100 - i * 15}%;background:${fc[i][0]};color:${fc[i][1]}">${num(v)}</div></div><div class="small"><b>${l}</b><div class="tiny muted">${(v * 100 / f0).toFixed(v / f0 < .01 ? 1 : 0)}%</div></div></div>`).join('')}</div>`;
    const stPill = { closed: 'p-green', under_contract: 'p-violet', negotiating: 'p-amber' };
    $('#topT').innerHTML = r.top.map((p, i) => `<tr onclick="location.hash='#/deal/${encodeURIComponent(p.id)}'"><td>${i + 1}</td><td><div class="prop">${thumb(p)}<div><b>${esc(title(p.street))}</b><span>${esc(place(p))}</span></div></div></td><td>${esc(title(p.owner_name))}</td><td class="hide-m">${esc(p.county.replace(' County', ''))}</td><td class="r num">${money(p.appraised_total)}</td><td class="r num hide-m">${money(p.est_equity)}</td><td class="r num">${p.fee ? money(p.fee) : '--'}</td><td class="hide-m small">${fmtDate(p.closed_at || p.updated_at)}</td><td><span class="pill ${stPill[p.stage]}">${esc((S.meta.stages.find((s) => s.key === p.stage) || {}).label)}</span></td></tr>`).join('') || '<tr><td colspan="9"><div class="empty">No deals in negotiation, under contract or closed yet.</div></td></tr>';
  }
  $('#rDays').onchange = (e) => { days = +e.target.value; load(); };
  $('#rPdf').onclick = () => print();
  await load();
  return () => chart && chart.destroy();
}

// ================================================================ SETTINGS
export async function settings(el, [tab = 'scoring']) {
  const SUPER = S.meta.super;
  const TABS = [['profile', 'Profile', 'user'], ...(SUPER ? [['scoring', 'Deal scoring', 'chart'], ['integrations', 'Integrations', 'link']] : []),
    ['notifications', 'Notifications', 'bell'], ['team', 'Team', 'users'], ['billing', 'Plan & billing', 'card']];
  if (!SUPER && ['scoring', 'integrations'].includes(tab)) tab = 'profile';
  el.innerHTML = `<div class="page-head"><div><h1>Settings</h1><div class="sub">Customize your preferences, integrations, and account settings.</div></div></div>
    <div class="settings-wrap"><div class="card sub-nav" style="padding:8px">${TABS.map(([k, l, i]) => `<a href="#/settings/${k}" class="${tab === k ? 'on' : ''}">${ic(i, 17)}${l}</a>`).join('')}</div><div id="sBody" style="min-width:0"></div></div>`;
  const body = $('#sBody');
  const s = S.meta.settings;
  if (tab === 'scoring') return scoringTab(body);
  if (tab === 'integrations') return integrationsTab(body);
  if (tab === 'notifications') { location.hash = '#/alerts'; return; }
  if (tab === 'profile') {
    const p = s.profile, o = s.offer_defaults;
    body.innerHTML = `<div class="settings-cols"><div class="card card-pad"><h3 style="margin-bottom:14px">Investor profile</h3><div class="small muted" style="margin:-8px 0 14px">Auto-filled into every offer letter and email.</div>
      <div class="terms"><div class="field"><label>Your name</label><input class="input" id="pName" value="${esc(p.name)}"></div><div class="field"><label>Company</label><input class="input" id="pCo" value="${esc(p.company)}"></div>
      <div class="field"><label>Email</label><input class="input" id="pEmail" value="${esc(p.email)}"></div><div class="field"><label>Phone</label><input class="input" id="pPhone" value="${esc(p.phone)}"></div></div>
      <h3 style="margin:10px 0 14px">Offer defaults</h3>
      <div class="terms"><div class="field"><label>Offer = % of county value, minus taxes owed</label><input class="input" id="oDisc" value="${o.discount_pct}"></div>
      <div class="field"><label>Financing</label><select class="select" id="oFin">${['Cash', 'DSCR loan (80% LTV)', 'Conventional loan', 'Hard money', 'Seller financing'].map((f) => `<option ${f === o.financing ? 'selected' : ''}>${f}</option>`).join('')}</select></div>
      <div class="field"><label>Closing timeline (days)</label><input class="input" id="oDays" value="${o.closing_days}"></div><div class="field"><label>Earnest money ($)</label><input class="input" id="oEarn" value="${o.earnest}"></div></div>
      <div class="field"><label>Seller credits</label><input class="input" id="oCred" value="${esc(o.seller_credits)}"></div>
      ${SUPER ? `<div class="field"><label>Nightly county sync time</label><select class="select" id="sTime" style="width:140px">${Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, '0')}:00`).map((t) => `<option ${t === s.sync_time ? 'selected' : ''}>${t}</option>`).join('')}</select><div class="hint">Hosted: the daily sync runs on GitHub Actions at 08:17 Pakistan time.</div></div>` : ''}
      <button class="btn primary" id="pSave">Save changes</button></div>
      ${SUPER ? `<div class="card card-pad"><h3>Demo data</h3><p class="small muted">Made-up owners and addresses so you can try every screen before the first real county sync.</p>
        <div class="row"><button class="btn" id="dSeed">${ic('db', 15)} Load demo data</button><button class="btn danger" id="dClear">${ic('x', 15)} Remove demo data</button></div>
        <h3 style="margin-top:22px">Setup wizard</h3><p class="small muted">Run the first-time setup again (profile, counties, alerts).</p><a class="btn" href="#/welcome">${ic('sparkle', 15)} Open setup</a></div>` : ''}</div>`;
    $('#pSave').onclick = async () => {
      const profile = { ...p, name: $('#pName').value, company: $('#pCo').value, email: $('#pEmail').value, phone: $('#pPhone').value };
      const offer_defaults = { ...o, discount_pct: +$('#oDisc').value || 65, financing: $('#oFin').value, closing_days: +$('#oDays').value || 21, earnest: +$('#oEarn').value || 0, seller_credits: $('#oCred').value };
      await api('/api/settings', { method: 'PUT', body: { profile, offer_defaults, ...($('#sTime') ? { sync_time: $('#sTime').value } : {}) } }); await refreshMeta(); toast('Saved');
    };
    if (!SUPER) return;
    $('#dSeed').onclick = async () => { $('#dSeed').disabled = true; await api('/api/demo/seed', { method: 'POST' }); await refreshMeta(); toast('Demo data loaded'); };
    $('#dClear').onclick = async () => { if (!confirm('Remove all demo parcels, alerts and pipeline items?')) return; const r = await api('/api/demo/clear', { method: 'POST' }); await refreshMeta(); toast(`Removed ${r.removed} demo parcels`); };
    return;
  }
  if (tab === 'team') {
    const users = ['admin', 'superadmin'].includes(S.user?.role) ? await api('/api/users') : [];
    body.innerHTML = `<div class="card card-pad"><div class="row between"><h3>Team</h3>${users.length ? '<button class="btn primary" id="tOpen">Manage team</button>' : ''}</div>
      <p class="muted small">${users.length ? `People who can log in to ${esc(S.meta.org.name)}. Your notes, deals and offers are private to your team.` : 'Only your company admin can add or remove people.'}</p>
      ${users.map((u) => `<div class="row" style="padding:8px 0;border-top:1px solid var(--line)"><div class="grow"><b>${esc(u.name)}</b> <span class="pill tiny">${esc(u.role)}</span><div class="tiny muted">${esc(u.email)}</div></div><span class="tiny muted">last login ${u.last_login ? fmtDate(u.last_login) : 'never'}</span></div>`).join('')}</div>`;
    if ($('#tOpen')) $('#tOpen').onclick = () => teamModal();
    return;
  }
  if (tab === 'billing') {
    const o = S.meta.org, L = o.limits;
    body.innerHTML = `<div class="card card-pad"><h3>Your plan: ${esc(o.label)}</h3>
      <div class="facts" style="margin-top:10px">
        <div class="fact"><div><div class="k">Company</div><div class="v">${esc(o.name)}</div></div></div>
        <div class="fact"><div><div class="k">Counties</div><div class="v">${S.meta.counties.length} of ${L.counties ?? 'all'}</div></div></div>
        <div class="fact"><div><div class="k">Users</div><div class="v">${o.users} of ${L.users ?? 'unlimited'}</div></div></div>
        ${L.reveals ? `<div class="fact"><div><div class="k">Leads opened</div><div class="v">${o.reveals_used} of ${L.reveals}</div></div></div>` : ''}
        ${o.plan === 'trial' ? `<div class="fact"><div><div class="k">Trial ends</div><div class="v">${fmtDate(o.trial_ends)} (${o.days_left} days)</div></div></div>` : ''}
      </div>${o.plan === 'internal' ? '<p class="muted small">Owner account: no limits.</p>' : '<button class="btn primary" id="bPlans" style="margin-top:12px">See plans / upgrade</button>'}</div>`;
    if ($('#bPlans')) $('#bPlans').onclick = () => plansModal();
    return;
  }
}

async function scoringTab(body) {
  const LBL = { years_behind: ['Years behind on tax', 'More years = higher score', 'cal'], equity: ['Estimated equity', 'Higher equity = higher score', 'house'], amount_owed: ['Amount owed', 'Higher amounts can indicate motivation', 'dollar'],
    out_of_state: ['Out-of-state owner', 'Non-Ohio / absentee owners = higher score', 'user'], vacancy: ['Vacancy signals', 'Not owner-occupied, long delinquency, empty lot', 'home'] };
  let w = { ...S.meta.settings.weights };
  const integ = (await api('/api/integrations')).configured;
  body.innerHTML = `<div class="settings-cols">
    <div class="card card-pad"><h3>How deals are scored</h3><div class="small muted">Adjust the weight of each factor to match your investment criteria.</div>
      <div id="sliders" style="margin-top:8px"></div><div class="row between" style="padding:12px 0"><b>Total</b><b id="tot" class="num"></b></div></div>
    <div class="card card-pad" id="example"></div></div>
    <div class="card card-pad" style="margin-top:18px"><h3>Integrations</h3><div class="small muted" style="margin-bottom:8px">Connect your tools to streamline research, outreach, and deal management.</div>
      ${[['sparkle', 'Gemini AI', 'AI-powered offer writing and score explanations', integ.gemini], ['mail', 'Gmail', 'Send alerts and digests from your Gmail (app password)', integ.email],
        ['search', 'Skip tracing', 'Owner phone and email lookup (BatchData, TLO, etc.) - coming soon', false], ['layers', 'Slack', 'Get alerts in a Slack channel', integ.slack], ['phone', 'Twilio SMS', 'SMS and WhatsApp alerts to your phone', integ.sms]]
        .map(([i, n, dsc, on]) => `<div class="integ-row">${ic(i, 20)}<b>${n}</b><span class="small muted desc">${dsc}</span><span class="small st"><span class="status-dot ${on ? 'on' : ''}"></span>${on ? 'Connected' : 'Not connected'}</span>
        ${n === 'Skip tracing' ? '<button class="btn sm" disabled>Soon</button>' : `<a class="btn sm ${on ? '' : 'primary'}" href="#/settings/integrations">${on ? 'Configure' : 'Connect'}</a>`}</div>`).join('')}
      <div class="row" style="margin-top:16px"><button class="btn primary" id="wSave">Save changes</button><button class="btn" id="wDiscard">Discard</button></div></div>`;
  const total = () => Object.values(w).reduce((a, b) => a + b, 0);
  function drawSliders() {
    $('#sliders').innerHTML = Object.entries(LBL).map(([k, [l, h, i]]) => `<div class="slider-row"><span class="ico tone-grey" style="width:36px;height:36px;border-radius:9px;display:grid;place-items:center">${ic(i, 17)}</span>
      <div><b class="small">${l}</b><div class="tiny muted">${h}</div></div><input type="range" class="sl" min="0" max="60" value="${w[k]}" data-k="${k}"><div class="row gap6"><input class="input num" style="width:52px;height:32px" value="${w[k]}" data-n="${k}"><span class="muted small">%</span></div></div>`).join('');
    $('#tot').textContent = total() + '%';
    $('#tot').style.color = total() === 100 ? '' : 'var(--red)';
  }
  let pt;
  async function preview() {
    clearTimeout(pt);
    pt = setTimeout(async () => {
      const r = await api('/api/settings/preview-score', { method: 'POST', body: { weights: w } });
      if (!r.parcel) { $('#example').innerHTML = '<h3>Example score</h3><div class="empty small">No properties yet.</div>'; return; }
      const p = r.parcel;
      $('#example').innerHTML = `<h3>Example score</h3><div class="small muted">Live preview based on the current weights.</div>
        <div class="row" style="margin:14px 0">${thumb(p, 'lg')}<div class="grow"><b>${esc(title(p.street))}</b><div class="small muted">${esc(place(p))}</div></div>${scorePill(r.score)}</div>
        <div class="row between small" style="border-bottom:1px solid var(--line);padding-bottom:10px"><div><b>${money(p.appraised_total)}</b><div class="tiny muted">Est. value</div></div><div><b>${money(p.est_equity)}</b><div class="tiny muted">Est. equity</div></div><div><b>${money(p.total_due ?? p.amount_owed)}</b><div class="tiny muted">Taxes owed</div></div><div><b>${yrs(p.years_behind)}</b><div class="tiny muted">Years behind</div></div></div>
        <div class="small" style="font-weight:600;margin:12px 0 4px">Score breakdown</div>
        ${Object.entries(r.parts).map(([k, v]) => `<div class="row between small" style="padding:5px 0"><span class="row gap6 muted">${ic(LBL[k][2], 15)}${LBL[k][0]}</span><b style="color:var(--green-ink)" class="num">+${Math.round(v)} / ${w[k]}</b></div>`).join('')}
        <div class="row between" style="background:var(--green-50);border-radius:8px;padding:9px 12px;margin-top:8px"><b>Total score</b><b class="num">${r.score} / 100</b></div>`;
    }, 120);
  }
  drawSliders(); preview();
  $('#sliders').oninput = (e) => {
    const k = e.target.dataset.k || e.target.dataset.n; if (!k) return;
    w[k] = Math.max(0, Math.min(100, +e.target.value || 0));
    if (e.target.dataset.k) $(`[data-n=${k}]`).value = w[k]; else $(`[data-k=${k}]`).value = w[k];
    $('#tot').textContent = total() + '%'; $('#tot').style.color = total() === 100 ? '' : 'var(--red)';
    preview();
  };
  $('#wSave').onclick = async () => {
    if (total() !== 100) { const f = 100 / total(); Object.keys(w).forEach((k) => w[k] = Math.round(w[k] * f)); const d = 100 - total(); w.years_behind += d; drawSliders(); toast('Weights scaled to total 100%'); }
    $('#wSave').disabled = true; $('#wSave').textContent = 'Re-scoring all properties...';
    await api('/api/settings', { method: 'PUT', body: { weights: w } }); await refreshMeta();
    $('#wSave').disabled = false; $('#wSave').textContent = 'Save changes'; toast('Saved. All deals re-scored.');
  };
  $('#wDiscard').onclick = () => { w = { ...S.meta.settings.weights }; drawSliders(); preview(); };
}

async function integrationsTab(body) {
  const r = await api('/api/integrations');
  const v = r.values, c = r.configured;
  // secret fields are masked with CSS, not type=password, so Chrome never autofills the login password into them
  const f = (k, l, ph = '', type = 'text') => `<div class="field"><label>${l}</label><input class="input" data-env="${k}" type="text" autocomplete="off" data-lpignore="true" data-1p-ignore spellcheck="false"${type === 'password' ? ' style="-webkit-text-security:disc"' : ''} placeholder="${esc(v[k] === 'set' ? 'Saved (hidden). Type to replace.' : ph)}" value="${v[k] && v[k] !== 'set' ? esc(v[k]) : ''}"></div>`;
  const sect = (name, key, on, inner, help) => `<div class="card card-pad" style="margin-bottom:18px"><div class="row between"><h3>${name}</h3><span class="small"><span class="status-dot ${on ? 'on' : ''}"></span>${on ? 'Connected' : 'Not connected'}</span></div>
    <div class="small muted" style="margin:4px 0 14px">${help}</div>${inner}<div class="row"><button class="btn primary sm" data-save>Save</button>${key ? `<button class="btn sm" data-test="${key}">Send test</button>` : ''}</div></div>`;
  body.innerHTML = `
    ${sect('Gemini AI', 'gemini', c.gemini, `<div class="terms">${f('GEMINI_API_KEY', 'API key', 'AIza...', 'password')}${f('GEMINI_MODEL', 'Model', 'gemini-2.5-flash')}</div>`,
      'Writes offer letters/emails and explains deal scores. Get a free key at aistudio.google.com > Get API key. Without a key, built-in templates are used.')}
    ${sect('Email (Gmail SMTP)', 'email', c.email, `<div class="terms">${f('SMTP_HOST', 'SMTP host', 'smtp.gmail.com')}${f('SMTP_PORT', 'Port', '587')}${f('SMTP_USER', 'Username', 'you@gmail.com')}${f('SMTP_PASSWORD', 'App password', '16-letter app password', 'password')}${f('ALERT_EMAIL_TO', 'Send alerts to', 'you@gmail.com')}${f('SMTP_FROM', 'From (optional)', '')}</div>`,
      'For Gmail: turn on 2-step verification, then create an App password (myaccount.google.com > Security > App passwords).')}
    ${sect('Slack', 'slack', c.slack, f('SLACK_WEBHOOK_URL', 'Incoming webhook URL', 'https://hooks.slack.com/services/...', 'password'), 'Create an Incoming Webhook in your Slack workspace and paste its URL.')}
    ${sect('Twilio SMS / WhatsApp', 'sms', c.sms, `<div class="terms">${f('TWILIO_SID', 'Account SID', 'AC...')}${f('TWILIO_TOKEN', 'Auth token', '', 'password')}${f('TWILIO_FROM', 'SMS from number', '+1...')}${f('TWILIO_WHATSAPP_FROM', 'WhatsApp from number', '+1...')}${f('ALERT_PHONE_TO', 'Your phone', '+92...')}</div>`,
      'Texts high-score deals and the daily digest to your phone.')}
    <div class="card card-pad small muted">Keys are saved only in the <b>.env</b> file inside your EstateHawk folder on this computer.</div>`;
  $$('[data-save]', body).forEach((b) => b.onclick = async () => {
    const vals = {}; $$('[data-env]', b.closest('.card')).forEach((i) => { if (i.value.trim()) vals[i.dataset.env] = i.value.trim(); });
    await api('/api/integrations', { method: 'POST', body: vals }); await refreshMeta(); toast('Saved'); integrationsTab(body);
  });
  $$('[data-test]', body).forEach((b) => b.onclick = async () => { b.disabled = true; b.textContent = 'Testing...'; const t = await api('/api/integrations/test/' + b.dataset.test, { method: 'POST' }); toast(t.message || (t.ok ? 'OK' : 'Failed'), !t.ok); b.disabled = false; b.textContent = 'Send test'; });
}

// ================================================================ ONBOARDING
export async function welcome(el) {
  const st = { step: 1, profile: { ...S.meta.settings.profile }, picks: new Set(S.meta.counties.map((c) => c.name)), types: new Set(S.meta.settings.deal_types || ['wholesale']) };
  const known = await api('/api/known-counties');
  if (!st.picks.size) known.filter((k) => k.verified).forEach((k) => st.picks.add(k.name));
  const counts = Object.fromEntries((await api('/api/counties')).map((c) => [c.name, c.active]));
  let map;
  function draw() {
    const steps = `<div class="steps">${[1, 2, 3].map((i) => `<i class="${i <= st.step ? 'on' : ''}"></i>`).join('')}</div>`;
    let inner = '';
    if (st.step === 1) inner = `<h1 style="font-size:28px">Welcome to EstateHawk</h1><div class="sub" style="margin-bottom:20px">Fresh off-market deals from county tax records. First, who are you? This goes on your offer letters.</div>
      <div class="terms"><div class="field"><label>Your name</label><input class="input" id="wName" value="${esc(st.profile.name || '')}"></div><div class="field"><label>Company (optional)</label><input class="input" id="wCo" value="${esc(st.profile.company || '')}"></div>
      <div class="field"><label>Email</label><input class="input" id="wEmail" value="${esc(st.profile.email || '')}"></div><div class="field"><label>Phone</label><input class="input" id="wPhone" value="${esc(st.profile.phone || '')}"></div></div>`;
    if (st.step === 2) inner = `<h1 style="font-size:28px">Pick the counties you want to watch</h1><div class="sub" style="margin-bottom:18px">We'll track tax-delinquent records and find off-market opportunities in your selected counties.</div>
      <div class="onb-grid"><div><div class="search" style="width:100%;margin-bottom:10px">${ic('search', 16)}<input id="wQ" placeholder="Search Ohio counties..."><span class="pill p-grey">Ohio (OH)</span></div>
        <div class="county-pick" id="wList">${known.map((k) => `<label class="${st.picks.has(k.name) ? 'on' : ''}"><input type="checkbox" data-n="${esc(k.name)}" ${st.picks.has(k.name) ? 'checked' : ''} ${k.host ? '' : 'disabled'}><span class="grow"><b>${esc(k.name)}, OH</b></span><span class="small muted">${counts[k.name] != null ? num(counts[k.name]) + ' delinquent properties' : k.host ? (k.verified ? 'Supported' : 'Website not verified') : 'Coming soon'}</span></label>`).join('')}</div></div>
        <div id="onbMap"></div></div>
      <h3 style="margin:22px 0 6px">What kind of deals do you want?</h3><div class="small muted" style="margin-bottom:12px">Choose the types of opportunities you're most interested in.</div>
      <div class="deal-types">${[['wholesale', 'Wholesale', 'Quick closes, lower risk', 'home'], ['flip', 'Fix and flip', 'Value add opportunities', 'edit'], ['hold', 'Buy and hold', 'Long-term cash flow', 'chart']].map(([k, l, d, i]) => `<div class="deal-type ${st.types.has(k) ? 'on' : ''}" data-t="${k}"><span class="ico tone-grey" style="width:38px;height:38px;border-radius:9px;display:grid;place-items:center">${ic(i, 18)}</span><div class="grow"><b>${l}</b><div class="tiny muted">${d}</div></div>${st.types.has(k) ? ic('check', 18) : ''}</div>`).join('')}</div>`;
    if (st.step === 3) inner = `<h1 style="font-size:28px">You're almost set</h1><div class="sub" style="margin-bottom:20px">Choose how to start. You can change everything later in Settings.</div>
      <div class="deal-types" style="grid-template-columns:1fr 1fr">
        <div class="deal-type on" data-start="sync"><span class="ico tone-green" style="width:38px;height:38px;border-radius:9px;display:grid;place-items:center">${ic('refresh', 18)}</span><div class="grow"><b>Download real county data now</b><div class="tiny muted">Takes a few minutes per county. Runs in the background.</div></div></div>
        <div class="deal-type" data-start="demo"><span class="ico tone-amber" style="width:38px;height:38px;border-radius:9px;display:grid;place-items:center">${ic('db', 18)}</span><div class="grow"><b>Explore with demo data first</b><div class="tiny muted">Made-up properties so you can try every screen.</div></div></div></div>
      <div class="card card-pad small" style="margin-top:18px;background:#FAFAF8">Alerts: new high-score deals (85+) and new delinquent owners appear in <b>Alerts</b>. To also get them by email, Slack, SMS or WhatsApp, add keys in Settings > Integrations. Add a <b>Gemini API key</b> there for AI-written offers.</div>`;
    el.innerHTML = `<div class="onb"><a class="brand" style="font-size:26px;padding:6px 0 16px"><img src="/static/icon.svg" style="width:42px;height:42px">EstateHawk</a>
      <div class="card"><div class="row between"><div class="small muted">Step ${st.step} of 3</div><div class="small muted">${['', 'Your profile', 'Set up your target counties', 'Start'][st.step]}</div></div>${steps}${inner}
      <div class="row" style="margin-top:22px;gap:12px">${st.step > 1 ? '<button class="btn grow" id="wBack">Back</button>' : '<span class="grow"></span>'}<button class="btn primary grow" id="wNext">${st.step === 3 ? 'Finish' : 'Continue'} ${ic('right', 16)}</button></div></div></div>`;
    if (st.step === 2) {
      const L = window.L;
      map = L.map('onbMap', { zoomControl: false, attributionControl: false, scrollWheelZoom: false }).setView([40.25, -82.75], 6.6);
      baseTiles(map);
      known.forEach((k) => { if (!k.lat) return; const on = st.picks.has(k.name); L.circleMarker([k.lat, k.lng], { radius: on ? 14 : 9, color: on ? '#14532D' : '#9AA29E', weight: 2, fillColor: on ? '#2E7D4F' : '#DADDD7', fillOpacity: on ? .55 : .5 }).bindTooltip(k.name.replace(' County', ''), { permanent: on, direction: 'top', className: '' }).addTo(map); });
      $('#wList').onchange = (e) => { const n = e.target.dataset.n; e.target.checked ? st.picks.add(n) : st.picks.delete(n); map.remove(); draw(); };
      $('#wQ').oninput = (e) => $$('#wList label').forEach((l) => l.style.display = l.textContent.toLowerCase().includes(e.target.value.toLowerCase()) ? '' : 'none');
      $$('.deal-type').forEach((d) => d.onclick = () => { st.types.has(d.dataset.t) ? st.types.delete(d.dataset.t) : st.types.add(d.dataset.t); map.remove(); draw(); });
    }
    if (st.step === 3) $$('[data-start]').forEach((d) => d.onclick = () => { $$('[data-start]').forEach((x) => x.classList.toggle('on', x === d)); });
    if ($('#wBack')) $('#wBack').onclick = () => { map && map.remove(); map = null; st.step--; draw(); };
    $('#wNext').onclick = async () => {
      if (st.step === 1) st.profile = { ...st.profile, name: $('#wName').value, company: $('#wCo').value, email: $('#wEmail').value, phone: $('#wPhone').value };
      if (st.step === 2 && !st.picks.size) return toast('Pick at least one county', true);
      if (st.step < 3) { map && map.remove(); map = null; st.step++; return draw(); }
      $('#wNext').disabled = true;
      const have = new Set(S.meta.counties.map((c) => c.name));
      for (const k of known) if (st.picks.has(k.name) && !have.has(k.name)) await api('/api/counties', { method: 'POST', body: { name: k.name, state: k.state, host: k.host, lat: k.lat, lng: k.lng } });
      await api('/api/settings', { method: 'PUT', body: { profile: st.profile, deal_types: [...st.types], onboarded: true } });
      const mode = $('[data-start].on').dataset.start;
      if (mode === 'demo') await api('/api/demo/seed', { method: 'POST' });
      else await api('/api/sync', { method: 'POST', body: {} });
      await refreshMeta();
      location.hash = mode === 'demo' ? '#/deals' : '#/counties';
      if (mode !== 'demo') { toast('County download started'); watchSync(); }
    };
  }
  draw();
  return () => map && map.remove();
}


// ---------- super admin ----------
const ACTION = [
  [/^login$/, 'Logged in'], [/reveal$/, 'Opened a locked lead'], [/\/offer$/, 'Drafted an offer'], [/\/stage$/, 'Moved a deal'],
  [/\/activity$/, 'Added a note / call'], [/\/contacts\/ai$/, 'Gemini contact search'], [/\/contacts$/, 'Saved owner contact'],
  [/export\.csv$/, 'Exported CSV'], [/^GET \/letters/, 'Printed letters'], [/batch-offers/, 'Batch offers'], [/\/api\/settings/, 'Changed settings'],
  [/\/api\/users/, 'Team change'], [/\/api\/tasks/, 'Follow-up task'], [/alerts\/read/, 'Read alerts'], [/auth\/password/, 'Changed password'],
  [/integrations/, 'Integrations'], [/\/api\/sync/, 'Started sync'], [/\/api\/counties/, 'County change'], [/^POST \/api\/admin\/orgs$/, 'Created company'], [/^PUT \/api\/admin\/orgs/, 'Changed company'], [/\/api\/admin\/users/, 'Changed user'], [/company/, null], [/user updated/, null],
];
const human = (a) => { for (const [re, l] of ACTION) if (re.test(a)) return l || a; return a; };

export async function admin(el, [tab = 'companies']) {
  const [st, orgs] = await Promise.all([api('/api/admin/stats'), api('/api/admin/orgs')]);
  const T = [['companies', 'Companies'], ['users', 'All users'], ['activity', 'Activity log']];
  el.innerHTML = `<div class="page-head"><div><h1>Admin</h1><div class="sub">Every company, user and action across EstateHawk.</div></div>
    <div class="right"><button class="btn primary" id="newOrg">${ic('plus', 16)} New company</button></div></div>
    <div class="stats" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px">
      ${[['Companies', st.companies], ['On trial', st.trials], ['Paying', st.paying], ['Monthly revenue', '$' + num(st.mrr)], ['Users', st.users], ['Active this week', st.active_week]]
        .map(([k, v]) => `<div class="card card-pad"><div class="small muted">${k}</div><div style="font-size:24px;font-weight:700">${v}</div></div>`).join('')}</div>
    <div class="row gap6" style="margin-bottom:12px">${T.map(([k, l]) => `<a class="btn ${tab === k ? 'primary' : ''}" href="#/admin/${k}">${l}</a>`).join('')}</div>
    <div id="aBody"></div>`;
  $('#newOrg').onclick = () => orgModal(null);
  const body = $('#aBody');
  const planPill = (o) => `<span class="pill tiny ${o.plan === 'trial' ? 'p-amber' : o.plan === 'internal' ? 'p-grey' : 'p-green'}">${esc(o.label)}</span>`;
  if (tab === 'companies') {
    body.innerHTML = `<div class="card" style="overflow:auto"><table class="table"><thead><tr><th>Company</th><th>Plan</th><th>Status</th><th>Counties</th><th class="r">Users</th><th class="r">Leads opened</th><th>Last activity</th><th></th></tr></thead><tbody>
      ${orgs.map((o) => `<tr><td><b>${esc(o.name)}</b><div class="tiny muted">${o.admin ? esc(o.admin.email) : ''}</div></td><td>${planPill(o)}${o.plan === 'trial' ? `<div class="tiny ${o.days_left < 0 ? '' : 'muted'}" style="${o.days_left < 0 ? 'color:#B42318' : ''}">${o.days_left < 0 ? 'ended' : o.days_left + ' days left'}</div>` : ''}</td>
        <td>${o.suspended ? '<span class="pill tiny p-red">Paused</span>' : '<span class="pill tiny p-green">Active</span>'}</td>
        <td class="small">${esc(o.county_names.join(', ') || 'none chosen')}</td><td class="r">${o.users}</td><td class="r">${o.limits.reveals ? `${o.reveals_used}/${o.limits.reveals}` : '--'}</td>
        <td class="small muted">${o.last_activity ? ago(o.last_activity) : 'never'}</td>
        <td><div class="row gap4" style="flex-wrap:nowrap"><button class="btn xs" data-edit="${o.id}">Edit</button>${o.id !== 1 ? `<button class="btn xs" data-view="${o.id}">View as</button>` : ''}</div></td></tr>`).join('')}
      </tbody></table></div>`;
    $$('[data-edit]', body).forEach((b) => b.onclick = () => orgModal(orgs.find((o) => o.id === +b.dataset.edit)));
    $$('[data-view]', body).forEach((b) => b.onclick = () => setViewOrg(+b.dataset.view));
  }
  if (tab === 'users') {
    const us = await api('/api/admin/users');
    body.innerHTML = `<div class="card" style="overflow:auto"><table class="table"><thead><tr><th>User</th><th>Company</th><th>Role</th><th>Last login</th><th></th></tr></thead><tbody>
      ${us.map((u) => `<tr style="${u.active ? '' : 'opacity:.55'}"><td><b>${esc(u.name)}</b><div class="tiny muted">${esc(u.email)}</div></td><td>${esc(u.org_name || '')}</td><td><span class="pill tiny">${esc(u.role)}</span></td>
        <td class="small muted">${u.last_login ? ago(u.last_login) : 'never'}</td>
        <td>${u.role === 'superadmin' ? '' : `<div class="row gap4" style="flex-wrap:nowrap"><button class="btn xs" data-reset="${u.id}">Reset password</button><button class="btn xs" data-act="${u.id}" data-on="${u.active ? 0 : 1}">${u.active ? 'Block' : 'Unblock'}</button></div>`}</td></tr>`).join('')}
      </tbody></table></div>`;
    $$('[data-act]', body).forEach((b) => b.onclick = async () => { await api('/api/admin/users/' + b.dataset.act, { method: 'PUT', body: { active: b.dataset.on === '1' } }); admin(el, [tab]); });
    $$('[data-reset]', body).forEach((b) => b.onclick = async () => {
      const pw = Math.random().toString(36).slice(2, 8) + 'Eh!' + Math.floor(Math.random() * 90 + 10);
      await api('/api/admin/users/' + b.dataset.reset, { method: 'PUT', body: { password: pw } });
      modal(`<h2>New password</h2><p>Send this to the user:</p><div class="card card-pad" style="font-family:ui-monospace,monospace">${esc(pw)}</div><div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn primary" data-close>Done</button></div>`);
    });
  }
  if (tab === 'activity') {
    body.innerHTML = `<div class="row gap6" style="margin-bottom:10px"><select class="select" id="aOrg" style="width:220px"><option value="">All companies</option>${orgs.map((o) => `<option value="${o.id}">${esc(o.name)}</option>`).join('')}</select>
      <div class="search" style="width:260px">${ic('search', 16)}<input id="aQ" placeholder="Search user or action..."></div></div><div class="card" style="overflow:auto"><table class="table"><thead><tr><th>When</th><th>Company</th><th>User</th><th>Action</th><th>Detail</th></tr></thead><tbody id="aRows"></tbody></table></div>`;
    const load = async () => {
      const rows = await api(`/api/admin/activity?org=${$('#aOrg').value}&q=${encodeURIComponent($('#aQ').value)}`);
      const pid = (a) => (a.match(/\/api\/parcels\/(.+?)\/(reveal|offer|stage|activity|contacts)/) || [])[1];
      $('#aRows').innerHTML = rows.map((r) => `<tr><td class="small muted" style="white-space:nowrap">${fmtDate(r.ts, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</td><td class="small">${esc(r.org_name || '')}</td>
        <td class="small">${esc(r.user_name || '')}</td><td><b class="small">${esc(human(r.action))}</b>${pid(r.action) ? ` <a class="tiny" href="#/deal/${pid(r.action)}">lead</a>` : ''}</td>
        <td class="tiny muted">${esc(r.detail || '')}${r.ip ? ' · ' + esc(r.ip) : ''}</td></tr>`).join('') || '<tr><td colspan="5"><div class="empty">No activity yet</div></td></tr>';
    };
    $('#aOrg').onchange = load; let t; $('#aQ').oninput = () => { clearTimeout(t); t = setTimeout(load, 300); };
    load();
  }

  function orgModal(o) {
    const P = S.meta.plans, all = S.meta.counties;
    const isNew = !o;
    const pw = Math.random().toString(36).slice(2, 8) + 'Eh!' + Math.floor(Math.random() * 90 + 10);
    const chosen = new Set(o ? (o.counties || all.map((c) => c.id)) : []);
    modal(`<h2>${isNew ? 'New company' : 'Edit ' + esc(o.name)}</h2><div style="height:10px"></div>
      <div class="terms"><div class="field"><label>Company name</label><input class="input" id="oName" value="${esc(o?.name || '')}"></div>
      <div class="field"><label>Plan</label><select class="select" id="oPlan">${Object.entries(P).concat(o?.plan === 'internal' ? [['internal', { label: 'Owner' }]] : []).map(([k, p]) => `<option value="${k}" ${(o?.plan || 'trial') === k ? 'selected' : ''}>${esc(p.label)}${p.price ? ' ($' + p.price + '/mo)' : ''}</option>`).join('')}</select></div></div>
      ${isNew ? `<div class="terms"><div class="field"><label>Admin name</label><input class="input" id="oAdmin"></div><div class="field"><label>Admin email (login)</label><input class="input" id="oEmail" type="text" autocomplete="off"></div></div>
        <div class="field"><label>Temporary password (send it to them)</label><input class="input" id="oPw" value="${pw}" autocomplete="off"></div>` : ''}
      <div class="field"><label>Counties <span class="muted small" id="oLim"></span></label><div class="row wrap gap6" id="oCounties">${all.map((c) => `<label class="pill" style="cursor:pointer"><input type="checkbox" value="${c.id}" ${chosen.has(c.id) ? 'checked' : ''}> ${esc(c.name)}</label>`).join('')}</div></div>
      ${!isNew && o.plan === 'trial' ? `<div class="field"><label>Trial</label><div class="row gap6"><span class="small muted">ends ${fmtDate(o.trial_ends)}</span><button class="btn xs" data-ext="7">+7 days</button><button class="btn xs" data-ext="14">+14 days</button></div></div>` : ''}
      ${!isNew && o.id !== 1 ? `<div class="field"><label>Status</label><select class="select" id="oStatus"><option value="active" ${o.status === 'active' ? 'selected' : ''}>Active</option><option value="suspended" ${o.status === 'suspended' ? 'selected' : ''}>Paused (cannot log in)</option></select></div>` : ''}
      <div class="field"><label>Private notes</label><textarea class="input" id="oNotes" rows="2" style="width:100%">${esc(o?.notes || '')}</textarea></div>
      <div class="row" style="justify-content:flex-end"><button class="btn" data-close>Cancel</button><button class="btn primary" id="oSave">${isNew ? 'Create company' : 'Save'}</button></div>`, (m, close) => {
      const lim = () => { const p = P[$('#oPlan', m).value] || {}; $('#oLim', m).textContent = p.counties == null ? '(all counties; leave empty for all)' : `(plan allows ${p.counties})`; };
      $('#oPlan', m).onchange = lim; lim();
      $$('[data-ext]', m).forEach((b) => b.onclick = async () => { await api('/api/admin/orgs/' + o.id, { method: 'PUT', body: { extend_days: +b.dataset.ext } }); close(); toast('Trial extended'); admin(el, [tab]); });
      $('#oSave', m).onclick = async () => {
        const counties = $$('#oCounties input:checked', m).map((x) => +x.value);
        const body = { name: $('#oName', m).value, plan: $('#oPlan', m).value, counties, notes: $('#oNotes', m).value };
        try {
          if (isNew) {
            Object.assign(body, { admin_name: $('#oAdmin', m).value, email: $('#oEmail', m).value, password: $('#oPw', m).value });
            await api('/api/admin/orgs', { method: 'POST', body });
            close();
            modal(`<h2>Company created</h2><p>Send these to the customer:</p><div class="card card-pad small" style="font-family:ui-monospace,monospace;line-height:1.8">Link: ${esc(location.origin)}<br>Email: ${esc(body.email)}<br>Password: ${esc(body.password)}</div>
              <p class="small muted">They should change the password after the first login (user menu > Change password).</p><div class="row" style="justify-content:flex-end"><button class="btn primary" data-close>Done</button></div>`);
          } else {
            if ($('#oStatus', m)) body.status = $('#oStatus', m).value;
            await api('/api/admin/orgs/' + o.id, { method: 'PUT', body }); close(); toast('Saved');
          }
          admin(el, [tab]);
        } catch (e) { toast(e.message, true); }
      };
    });
  }
}
