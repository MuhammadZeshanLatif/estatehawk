(() => {
  if (document.getElementById('eh-chat')) return;
  const appPage = location.pathname === '/app';
  const root = document.createElement('div');
  root.id = 'eh-chat';
  if (appPage) root.classList.add('eh-chat-app');
  root.innerHTML = `<button class="eh-chat-launcher" type="button" aria-label="Open EstateHawk help" aria-expanded="false"><img src="/static/icon.svg" alt=""><span>Ask EstateHawk</span><i></i></button>
    <section class="eh-chat-panel" role="dialog" aria-label="EstateHawk assistant" hidden>
      <header class="eh-chat-head"><span class="eh-chat-mark"><img src="/static/icon.svg" alt=""></span><span><strong>EstateHawk assistant</strong><small>Help with EstateHawk features</small></span><button type="button" class="eh-chat-close" aria-label="Close chat">×</button></header>
      <div class="eh-chat-messages" role="log" aria-live="polite"></div>
      <div class="eh-chat-suggestions"></div>
      <form class="eh-chat-form"><input type="text" maxlength="1000" autocomplete="off" placeholder="Ask about EstateHawk..." aria-label="Your question"><button type="submit" aria-label="Send message">➤</button></form>
      <div class="eh-chat-foot">EstateHawk help · Please don't share private details</div>
    </section>`;
  document.body.append(root);
  const panel = root.querySelector('.eh-chat-panel');
  const launcher = root.querySelector('.eh-chat-launcher');
  const messages = root.querySelector('.eh-chat-messages');
  const suggestions = root.querySelector('.eh-chat-suggestions');
  const form = root.querySelector('.eh-chat-form');
  const input = form.querySelector('input');
  const sendButton = form.querySelector('button');
  let signedIn = false, busy = false, greeted = false;
  const userQuestions = [];

  fetch('/api/auth/me', { credentials: 'same-origin' }).then((r) => { signedIn = r.ok; }).catch(() => {});
  const addMessage = (who, message) => {
    const line = document.createElement('div'); line.className = 'eh-chat-message ' + who;
    const bubble = document.createElement('div'); bubble.className = 'eh-chat-bubble'; bubble.textContent = message;
    line.append(bubble); messages.append(line); messages.scrollTop = messages.scrollHeight;
    return line;
  };
  const showSuggestions = () => {
    const prompts = signedIn ? ['How do I filter leads?', 'How do I find owner contacts?', 'How do I draft an offer?']
      : ['How does EstateHawk work?', 'How can I find leads?', 'How are owner contacts found?'];
    suggestions.replaceChildren();
    prompts.forEach((label) => {
      const button = document.createElement('button'); button.type = 'button'; button.textContent = label;
      button.onclick = () => send(label); suggestions.append(button);
    });
  };
  const greet = () => {
    if (greeted) return;
    greeted = true;
    const typing = document.createElement('div'); typing.className = 'eh-chat-typing'; typing.textContent = 'EstateHawk is typing…'; messages.append(typing);
    setTimeout(() => { typing.remove(); addMessage('bot', signedIn ? 'Hi! How may I help you with your EstateHawk account today?' : 'Hi there! How may I help you explore EstateHawk today?'); messages.append(suggestions); showSuggestions(); }, 600);
  };
  const open = (focus = false) => {
    panel.hidden = false; launcher.setAttribute('aria-expanded', 'true'); root.classList.add('open'); greet();
    if (focus) input.focus();
  };
  const close = () => { panel.hidden = true; launcher.setAttribute('aria-expanded', 'false'); root.classList.remove('open'); launcher.focus(); };
  launcher.onclick = () => panel.hidden ? open(true) : close();
  root.querySelector('.eh-chat-close').onclick = close;
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !panel.hidden) close(); });

  async function send(value) {
    const question = String(value || '').trim();
    if (!question || busy) return;
    busy = true; input.value = ''; input.disabled = true; sendButton.disabled = true; suggestions.replaceChildren();
    addMessage('user', question);
    const typing = document.createElement('div'); typing.className = 'eh-chat-typing'; typing.textContent = 'EstateHawk is thinking…'; messages.append(typing); messages.scrollTop = messages.scrollHeight;
    try {
      const response = await fetch(signedIn ? '/api/chat' : '/api/public/chat', {
        method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', ...(signedIn && appPage && localStorage.getItem('eh_view_org') ? { 'X-Org': localStorage.getItem('eh_view_org') } : {}) },
        body: JSON.stringify({ question, history: userQuestions.slice(-2) }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Please try again.');
      typing.remove(); addMessage('bot', data.reply || 'How may I help you with EstateHawk?');
      userQuestions.push(question);
    } catch (error) {
      typing.remove(); addMessage('bot', error.message || 'Please try again shortly.');
    } finally {
      busy = false; input.disabled = false; sendButton.disabled = false; input.focus();
    }
  }
  form.onsubmit = (e) => { e.preventDefault(); send(input.value); };
  try {
    const greetKey = appPage ? 'eh_chat_greeted_app' : 'eh_chat_greeted_site';
    if (!sessionStorage.getItem(greetKey)) {
      sessionStorage.setItem(greetKey, '1');
      setTimeout(() => open(false), 900);
    }
  } catch (_) { setTimeout(() => open(false), 900); }
})();
