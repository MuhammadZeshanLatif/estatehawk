// Deal page research: flood zone, state tax-sale rules, comparable sales and the deal calculator.
// Facts carry their source; estimates say so; legal text is a dated summary, not advice.
import { $, $$, esc, ic, api, money, fmtDate, toast, S, modal } from './app.js';

const day = (x) => x ? fmtDate(x, { month: 'short', day: 'numeric', year: 'numeric' }) : '--';
const daysTo = (x) => Math.ceil((Date.parse(x) - Date.now()) / 864e5);

function floodCard(f) {
  const high = f && f.sfha;
  return `<div class="card card-pad"><div class="row between"><h3>Flood zone</h3>${f && f.zone ? `<span class="pill ${high ? 'p-red' : 'p-green'} tiny">Zone ${esc(f.zone)}</span>` : ''}</div>
    <p class="small" style="margin:10px 0 6px">${esc(f ? f.words : 'Not checked')}</p>
    <div class="tiny muted">${f && f.checked ? `Source: ${esc(f.source || 'FEMA National Flood Hazard Layer')}, checked ${day(f.checked)}. ` : ''}FEMA maps show insurance zones, not every flood risk.</div></div>`;
}

function rulesCard(r) {
  if (!r) return '';
  const red = r.redemption;
  const left = red && red.ends ? daysTo(red.ends) : null;
  return `<div class="card card-pad rules"><div class="row between"><h3>${esc(r.name)} tax sale rules</h3><span class="tiny muted">Reviewed ${day(r.reviewed)}</span></div>
    <div class="small muted" style="margin:4px 0 10px">${esc(r.kind)}</div>
    ${r.sale_date ? `<div class="rule-sale"><b>${daysTo(r.sale_date) >= 0 ? `Sale in ${daysTo(r.sale_date)} days` : 'Sale date passed'}</b><span class="small muted">${day(r.sale_date)}</span></div>` : ''}
    ${red && red.ends ? `<div class="rule-sale"><b>${left >= 0 ? `Owner can redeem for ${left} more days` : 'Redemption period over'}</b><span class="small muted">Until about ${day(red.ends)}: ${esc(red.basis)}. ${esc(red.assumes)}</span></div>` : ''}
    ${r.points.map(([h, t, u]) => `<div class="rule-pt"><b class="small">${esc(h)}</b><p class="small">${esc(t)} <a href="${esc(u)}" target="_blank" rel="noopener" style="color:var(--green)">Statute ${ic('link', 12)}</a></p></div>`).join('')}
    <details class="small" style="margin-top:8px"><summary style="cursor:pointer;font-weight:600">Due-diligence checklist</summary><ul style="margin:8px 0 0;padding-left:18px;line-height:1.7">${r.checklist.map((c) => `<li>${esc(c)}</li>`).join('')}</ul></details>
    <p class="tiny muted" style="margin:10px 0 0">${esc(r.note)}</p></div>`;
}

function compsCard(res) {
  const c = res.comps;
  if (!res.comps_available && !c) {
    return `<div class="card card-pad"><h3>Comparable sales</h3><p class="small muted" style="margin-top:8px">${S.meta.super
      ? 'Switch on with a RentCast API key: Render > Environment > RENTCAST_API_KEY. The free plan gives 50 lookups a month.'
      : 'Recent nearby sales and a market value estimate are coming soon. Until then the calculator uses the county value.'}</p></div>`;
  }
  const rows = c && c.comps ? c.comps : [];
  return `<div class="card card-pad"><div class="row between"><h3>Comparable sales</h3>${res.comps_available ? `<button class="btn xs" id="getComps">${ic('refresh', 13)} ${c ? 'Refresh' : 'Get comps'}</button>` : ''}</div>
    ${c && c.error ? `<p class="small" style="color:var(--red);margin-top:8px">${esc(c.error)}</p>` : ''}
    ${c && c.value ? `<div class="row" style="gap:18px;margin:10px 0"><div><div class="tiny muted">Market value (estimate)</div><b style="font-size:20px">${money(c.value)}</b></div>
      <div><div class="tiny muted">Range</div><span class="small">${money(c.low)} to ${money(c.high)}</span></div></div>` : (!c ? '<p class="small muted" style="margin-top:8px">Uses one lookup. Results are kept for 30 days.</p>' : '')}
    ${rows.length ? `<div class="table-scroll"><table class="mini"><thead><tr><th>Address</th><th>Price</th><th>Sq ft</th><th>Bd/Ba</th><th>Miles</th><th>Date</th></tr></thead><tbody>
      ${rows.map((r) => `<tr><td>${esc(r.address || '')}</td><td>${money(r.price)}</td><td>${r.sqft ? Number(r.sqft).toLocaleString() : '--'}</td><td>${r.beds ?? '--'}/${r.baths ?? '--'}</td><td>${r.miles ?? '--'}</td><td>${esc(r.date || '')}</td></tr>`).join('')}</tbody></table></div>` : ''}
    ${c && c.fetched ? `<div class="tiny muted" style="margin-top:6px">Source: ${esc(c.source)}, ${day(c.fetched)}. An estimate, not an appraisal.</div>` : ''}</div>`;
}

function calcCard(res) {
  const k = res.calc, d = res.calc_defaults || {};
  if (!k) return '';
  const line = (label, v, note = '', strong = false) => `<div class="calc-row${strong ? ' strong' : ''}"><span>${label}${note ? `<span class="tiny muted"> ${esc(note)}</span>` : ''}</span><b>${v}</b></div>`;
  return `<div class="card card-pad calc" id="calcCard"><div class="row between"><h3>Deal calculator</h3><span class="tiny muted">Estimates</span></div>
    <div class="calc-in">
      <label>After-repair value<input class="input" id="kArv" inputmode="decimal" value="${k.arv || ''}"></label>
      <label>Repairs<input class="input" id="kRep" inputmode="decimal" value="${k.repairs || ''}"></label>
      <label>Known liens<input class="input" id="kLien" inputmode="decimal" value="${k.liens || 0}"></label>
      <label>Profit you want, %<input class="input" id="kPct" inputmode="decimal" value="${k.profit_pct}"></label>
      <label>Risk<select class="select" id="kRisk">${['low', 'medium', 'high'].map((r) => `<option value="${r}" ${r === k.risk ? 'selected' : ''}>${r[0].toUpperCase() + r.slice(1)}: ${{ low: 'careful', medium: 'normal', high: 'aggressive' }[r]}</option>`).join('')}</select></label>
      <label>Months to resell<input class="input" id="kHold" inputmode="decimal" value="${d.hold_months ?? 6}"></label>
    </div>
    <div class="calc-out">
      ${line('After-repair value', money(k.arv), k.sources.arv)}
      ${line('Repairs', '- ' + money(k.repairs), k.sources.repairs)}
      ${line('Back taxes', '- ' + money(k.taxes, 2), 'county list')}
      ${k.liens ? line('Known liens', '- ' + money(k.liens)) : ''}
      ${line('Closing costs (buy + sell)', '- ' + money(k.buy_closing + k.sell_closing), `${d.buy_closing_pct}% + ${d.sell_closing_pct}%`)}
      ${line('Holding costs', '- ' + money(k.holding), `${k.hold_months} months`)}
      ${line('Your profit', '- ' + money(k.profit), `${k.profit_pct}% of value`)}
      ${line('Maximum offer', money(k.max_bid), '', true)}
      ${line('70% rule, for comparison', money(k.rule70))}
      ${k.roi_pct != null ? line('Return on cash in', k.roi_pct + '%', 'if you pay the maximum offer') : ''}
    </div>
    ${k.warning ? `<p class="small" style="color:var(--red)">${esc(k.warning)}</p>` : ''}
    <p class="tiny muted" style="margin:8px 0 0">Liens and mortgages are not in county tax records: get a title search before you buy.</p>
    <div class="row" style="justify-content:flex-end;gap:8px;margin-top:10px"><button class="btn sm" id="kSave">Save as my defaults</button><button class="btn sm primary" id="kRun">Recalculate</button></div></div>`;
}

export async function loadResearch(p, box) {
  box.innerHTML = '<div class="card card-pad small muted">Loading flood zone, tax sale rules and deal math...</div>';
  let res;
  try { res = await api(`/api/parcels/${encodeURIComponent(p.id)}/research`); } catch (e) { box.innerHTML = ''; return; }
  if (!document.body.contains(box)) return;
  const draw = () => {
    box.innerHTML = `<div class="research-grid"><div class="col" style="gap:18px;min-width:0">${calcCard(res)}${compsCard(res)}</div>
      <div class="col" style="gap:18px;min-width:0">${floodCard(res.flood)}${rulesCard(res.rules)}</div></div>`;
    const run = async (save) => {
      const body = { arv: $('#kArv').value, repairs: $('#kRep').value, liens: $('#kLien').value, save,
        settings: { profit_pct: $('#kPct').value, risk: $('#kRisk').value, hold_months: $('#kHold').value } };
      try { res.calc = await api(`/api/parcels/${encodeURIComponent(p.id)}/calc`, { method: 'POST', body }); if (save) { res.calc_defaults = { ...res.calc_defaults, ...body.settings }; toast('Saved as your defaults for every lead.'); } draw(); }
      catch (e) { toast(e.message, true); }
    };
    if ($('#kRun')) { $('#kRun').onclick = () => run(false); $('#kSave').onclick = () => run(true); $$('#calcCard input').forEach((i) => i.onkeydown = (e) => { if (e.key === 'Enter') run(false); }); }
    if ($('#getComps')) $('#getComps').onclick = async () => {
      $('#getComps').disabled = true; $('#getComps').textContent = 'Looking up...';
      try { res.comps = await api(`/api/parcels/${encodeURIComponent(p.id)}/comps`, { method: 'POST' }); if (res.comps.value) $('#kArv') && ($('#kArv').value = ''); draw(); if (res.comps.value) run(false); }
      catch (e) { toast(e.message, true); draw(); }
    };
  };
  draw();
}

export function lockedResearch(p, box) {
  api(`/api/parcels/${encodeURIComponent(p.id)}/research`).then((res) => {
    if (!document.body.contains(box)) return;
    box.innerHTML = `${floodCard(res.flood)}${rulesCard(res.rules)}`;
  }).catch(() => { box.innerHTML = ''; });
}

// Side-by-side compare of 2 to 4 leads, ranked by one measure the user picks.
export async function compareModal(ids, by = 'margin') {
  let r;
  try { r = await api('/api/compare', { method: 'POST', body: { ids, by } }); } catch (e) { return toast(e.message, true); }
  const rows = r.rows;
  const line = (label, f) => `<tr><th>${label}</th>${rows.map((x) => `<td>${f(x)}</td>`).join('')}</tr>`;
  const st = { verified: 'Verified', partial: 'Partly verified', conflict: 'Amounts differ', stale: 'Not on latest list', removed: 'Off the list' };
  modal(`<h2>Compare ${rows.length} leads</h2>
    <div class="row" style="gap:8px;margin:6px 0 12px;flex-wrap:wrap"><label class="small muted" for="cmpBy">Rank by</label>
      <select class="select" id="cmpBy" style="width:auto">${Object.entries(r.options).map(([k, v]) => `<option value="${k}" ${k === r.by ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select></div>
    <div class="table-scroll"><table class="mini cmp"><thead><tr><th></th>${rows.map((x) => `<th><span class="pill ${x.rank === 1 ? 'p-green' : 'p-grey'} tiny">#${x.rank}</span><div style="margin-top:4px"><a href="#/deal/${encodeURIComponent(x.id)}" data-close style="color:var(--ink)">${esc(x.title)}</a></div><div class="tiny muted">${esc(x.place)}</div></th>`).join('')}</tr></thead><tbody>
      ${line('Why this rank', (x) => `<span class="small">${esc(x.why)}</span>`)}
      ${line('County value', (x) => money(x.value))}
      ${line('Taxes owed', (x) => money(x.taxes, 2))}
      ${line('Est. equity', (x) => money(x.est_equity))}
      ${line('Max offer (your calculator)', (x) => `<b>${money(x.max_bid)}</b>`)}
      ${line('Est. repairs', (x) => money(x.repairs))}
      ${line('Taxes as % of value', (x) => x.value ? Math.round(100 * x.taxes / x.value) + '%' : '--')}
      ${line('Years behind', (x) => x.years_behind ?? '--')}
      ${line('Deal score', (x) => x.score != null ? Math.round(x.score) : '--')}
      ${line('Property type', (x) => esc(x.property_type || '--'))}
      ${line('Owner out of state', (x) => x.out_of_state ? 'Yes' : 'No')}
      ${line('Flood zone', (x) => esc(x.flood))}
      ${line('Data check', (x) => esc(st[x.status] || x.status))}
      ${line('County data complete', (x) => x.complete + '%')}
    </tbody></table></div>
    <p class="tiny muted" style="margin:10px 0 0">${esc(r.note)} Liens and mortgages are not included.</p>
    <div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn" data-close>Close</button></div>`, (m) => {
    $('#cmpBy', m).onchange = (e) => compareModal(ids, e.target.value);
  });
}

// Auction calendar: upcoming tax sales by date, county and number of properties.
export async function auctions(el) {
  el.innerHTML = `<div class="page-head"><div><h1>Auction calendar</h1><div class="sub">Upcoming tax sales in your counties, from county and tax-attorney sale lists.</div></div>
    <div class="right"><select class="select" id="aDays" aria-label="How far ahead" style="width:auto"><option value="30">Next 30 days</option><option value="120" selected>Next 4 months</option><option value="365">Next 12 months</option></select></div></div>
    <div id="aList"><div class="card card-pad small muted">Loading sales...</div></div>`;
  const load = async () => {
    const r = await api(`/api/auctions?days=${$('#aDays').value}`);
    if (!document.body.contains(el)) return;
    const byMonth = {};
    r.rows.forEach((x) => { const k = x.d.slice(0, 7); (byMonth[k] = byMonth[k] || []).push(x); });
    $('#aList').innerHTML = Object.keys(byMonth).length ? Object.entries(byMonth).map(([mo, rows]) => `
      <h3 style="margin:18px 0 8px">${fmtDate(mo + '-01', { month: 'long', year: 'numeric' })}</h3>
      <div class="card"><div style="overflow-x:auto"><table class="table"><thead><tr><th>Sale date</th><th>County</th><th class="r">Properties</th><th class="r hide-m">Lowest minimum bid</th><th class="r hide-m">Score 80+</th><th></th></tr></thead><tbody>
      ${rows.map((x) => `<tr><td><b>${fmtDate(x.d, { weekday: 'short', month: 'short', day: 'numeric' })}</b><div class="tiny muted">${x.days === 0 ? 'Today' : `in ${x.days} days`}</div></td>
        <td>${esc(x.county)}, ${esc(x.state)}</td>
        <td class="r num">${x.n != null ? x.n : `<span class="small muted">${x.listed} on the delinquent list</span>`}</td>
        <td class="r hide-m">${x.low != null ? money(x.low) : '--'}</td><td class="r hide-m">${x.strong ?? '--'}</td>
        <td class="r">${x.kind === 'list' ? `<button class="btn xs a-open" data-c="${x.county_id}" data-d="${esc(x.d)}">Properties</button>` : '<span class="tiny muted">County sale date</span>'}</td></tr>
        <tr class="a-rows hide" data-for="${x.county_id}-${esc(x.d)}"><td colspan="6"></td></tr>`).join('')}</tbody></table></div></div>`).join('')
      : '<div class="card empty">No tax sales on the calendar for this period. Texas sale lists add dates as attorneys post them; Ohio counties set dates through the court.</div>';
    $('#aList').insertAdjacentHTML('beforeend', `<p class="tiny muted" style="margin-top:14px">${esc(r.note)}</p>`);
    $$('.a-open', el).forEach((b) => b.onclick = async () => {
      const row = $(`.a-rows[data-for="${b.dataset.c}-${b.dataset.d}"]`, el);
      if (!row.classList.contains('hide')) { row.classList.add('hide'); return; }
      const list = await api(`/api/parcels-by-sale?county_id=${b.dataset.c}&date=${b.dataset.d}`);
      row.firstElementChild.innerHTML = `<table class="mini"><thead><tr><th>Property</th><th>Minimum bid</th><th>County value</th><th>Score</th><th>Status</th></tr></thead><tbody>${list.map((p) => `<tr><td><a href="#/deal/${encodeURIComponent(p.id)}" style="color:var(--green)">${esc(p.street || 'Parcel')}</a> <span class="tiny muted">${esc(p.city || '')}</span></td><td>${money(p.min_bid ?? p.amount_owed)}</td><td>${money(p.appraised_total)}</td><td>${p.score != null ? Math.round(p.score) : '--'}</td><td class="small">${esc(p.sale_status || '')}</td></tr>`).join('')}</tbody></table>`;
      row.classList.remove('hide');
    });
  };
  $('#aDays').onchange = load;
  await load();
}
