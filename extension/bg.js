// Opens one Google search in a minimized window, waits for the AI Overview, returns its text, closes the window.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function readPage() {
  const t = document.body ? document.body.innerText : '';
  if (/unusual traffic|not a robot|recaptcha/i.test(t) || location.pathname.startsWith('/sorry')) return { captcha: true };
  const i = t.indexOf('AI Overview');
  if (i < 0) return { overview: '', loading: true, snippet: t.slice(0, 3000) };
  let s = t.slice(i + 'AI Overview'.length);
  const ends = ['AI responses may include mistakes', 'People also ask', 'Ask anything', 'Things to know', 'Dive deeper in AI Mode'];
  let end = s.length;
  for (const m of ends) { const k = s.indexOf(m); if (k > 0 && k < end) end = k; }
  s = s.slice(0, Math.min(end, 5000)).trim();
  // open a collapsed overview
  const more = [...document.querySelectorAll('div[role=button],span[role=button],button')].find((b) => /^show more$/i.test((b.innerText || '').trim()));
  if (more) more.click();
  return { overview: s, generating: /generating|searching|thinking/i.test(s.slice(0, 80)) };
}

function progress(tabId, state) {
  if (tabId != null) chrome.tabs.sendMessage(tabId, { type: 'EH_PROGRESS', state }).catch(() => {});
}

async function search(q, fromTab) {
  const url = 'https://www.google.com/search?hl=en&q=' + encodeURIComponent(q);
  const win = await chrome.windows.create({ url, state: 'minimized', focused: false });
  const tabId = win.tabs[0].id;
  try {
    let last = '', stable = 0, res = {}, shown = false, limit = 25;
    for (let i = 0; i < limit; i++) {        // ~25 s, or up to 3 min while you answer Google's check
      await sleep(1000);
      let out;
      try { [out] = await chrome.scripting.executeScript({ target: { tabId }, func: readPage }); } catch (e) { continue; }
      res = out.result || {};
      if (res.captcha) {
        if (!shown) {                        // bring the window to the front so YOU can tick "I'm not a robot"
          shown = true; limit = i + 180;
          await chrome.windows.update(win.id, { state: 'normal', focused: true, width: 560, height: 760, top: 60, left: 60 });
          progress(fromTab, 'captcha');
        }
        continue;
      }
      if (shown && res.overview !== undefined) {
        shown = false; progress(fromTab, 'reading');
        chrome.windows.update(win.id, { state: 'minimized' }).catch(() => {});
        limit = i + 25;
      }
      if (res.overview && !res.generating) {
        stable = res.overview === last ? stable + 1 : 0;
        last = res.overview;
        if (stable >= 2) break;               // text stopped changing
      }
    }
    if (res.captcha) return { ok: false, captcha: true, error: 'Google check was not completed. Try again and tick "I\'m not a robot" in the window that opens.' };
    if (!res.overview) return { ok: true, overview: '', note: 'Google showed no AI Overview for this owner.' };
    return { ok: true, overview: res.overview };
  } finally {
    chrome.windows.remove(win.id).catch(() => {});
  }
}

chrome.runtime.onMessage.addListener((msg, sender, send) => {
  if (msg && msg.type === 'EH_GOOGLE') {
    search(msg.q, sender.tab && sender.tab.id).then(send).catch((e) => send({ ok: false, error: String(e) }));
    return true;
  }
});
