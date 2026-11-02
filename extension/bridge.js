// Runs on the EstateHawk dashboard only. Passes "search Google" requests to the extension and the text back.
document.documentElement.dataset.ehHelper = '1';
chrome.runtime.onMessage.addListener((m) => {
  if (m && m.type === 'EH_PROGRESS') window.postMessage({ type: 'EH_GOOGLE_PROGRESS', state: m.state }, '*');
});
window.addEventListener('message', (e) => {
  if (e.source !== window || !e.data || e.data.type !== 'EH_GOOGLE') return;
  chrome.runtime.sendMessage({ type: 'EH_GOOGLE', q: e.data.q }, (resp) => {
    window.postMessage({ type: 'EH_GOOGLE_RESULT', id: e.data.id, ...(resp || { ok: false, error: 'No answer from helper' }) }, '*');
  });
});
