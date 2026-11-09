// EstateHawk FEATURE LIBRARY for videos. One scene = one feature, about 6-15 seconds.
// Every scene reaches its page by clicking (sidebar, buttons, links), so scenes can be chained into one continuous take.
//
//   bash tools/video/run.sh --file library.js --list                       list every feature scene
//   bash tools/video/run.sh --file library.js --scenes home,deals,deal-open single take, in that order
//   bash tools/video/run.sh --file library.js --split --scenes map,alerts  one mp4 per scene
//   add --captions to show each scene's caption (off by default for voiceover videos: use --no-captions)
//
// Helpers (record.js): go, nav, click(sel, hold, zoom), focus(sel, sec, zoom), hover, type, scroll, scrollTo, wait, card, caption, topLeadId, page
// When a feature is added or changed in the product, add or update its scene here (see CLAUDE.md).

const deal = async (v) => {  // make sure a deal page is open, by clicking a lead like a user would
  if (/#\/deal\//.test(v.page.url())) return;
  await v.nav('deals');
  await v.click('#leadTable tbody tr b', 0.6, 1.8);
  await v.page.waitForSelector('.timeline', { timeout: 10000 }).catch(() => {});
};
const TAB = { profile: 'Profile', scoring: 'Deal scoring', integrations: 'Integrations', team: 'Team', api: 'API access', billing: 'Plan & billing' };
const setTab = (t) => async (v) => { await v.nav('settings'); await v.click(`.sub-nav a:has-text("${TAB[t]}")`, 0.8, 1.8); await v.wait(600); };

module.exports = [
  // ---------- website ----------
  { id: 'intro-card', title: 'Title card', caption: '', run: async (v) => { await v.card('EstateHawk', 'Tax-delinquent leads, straight from the county', 3200); } },
  {
    id: 'home', title: 'Website home page', caption: 'Find tax-delinquent property leads before the competition',
    run: async (v) => { await v.go('/'); await v.focus('h1', 2.2, 1.5); await v.focus('.hero a.btn, a.btn.primary', 1.4, 1.9); await v.scroll(800, 2200); await v.scroll(800, 2200); await v.scroll(-1600, 1200); },
  },
  { id: 'features-page', title: 'Features page', caption: 'Everything an investor needs in one place', run: async (v) => { await v.go('/'); await v.click('header a:has-text("Features")', 0.6); await v.wait(1500); await v.scroll(900, 3000); } },
  { id: 'how-it-works', title: 'How it works page', caption: 'How EstateHawk works', run: async (v) => { await v.go('/'); await v.click('header a:has-text("How it works")', 0.6); await v.wait(1500); await v.scroll(900, 3000); } },
  {
    id: 'calculator-public', title: 'Free deal profit calculator', caption: 'Free deal profit calculator, no login needed',
    run: async (v) => {
      await v.go('/'); await v.click('header a:has-text("Free calculator"), header a:has-text("calculator")', 0.6); await v.wait(1200);
      await v.type('input >> nth=0', '120000'); await v.type('input >> nth=1', '190000'); await v.type('input >> nth=2', '25000');
      await v.focus('main', 2.5, 1.3);
    },
  },
  { id: 'pricing', title: 'Pricing page', caption: 'Plans from $49 a month, 14-day free trial', run: async (v) => { await v.go('/'); await v.click('header a:has-text("Pricing")', 0.6); await v.wait(1200); await v.focus('.plan.pro', 2.6, 1.6); await v.scroll(700, 2000); } },
  { id: 'counties-page', title: 'Public counties page', caption: 'See every county we cover', run: async (v) => { await v.go('/'); await v.click('header a:has-text("Counties")', 0.6); await v.wait(1500); await v.scroll(700, 2500); } },
  { id: 'blog', title: 'Blog', caption: 'Guides for tax-delinquent investing', run: async (v) => { await v.go('/'); await v.click('header a:has-text("Blog")', 0.6); await v.wait(1500); await v.scroll(600, 2200); } },
  { id: 'signup', title: 'Sign up page', caption: 'Start a free trial in a minute', run: async (v) => { await v.go('/signup'); await v.wait(800); await v.focus('form', 2.5, 1.4); } },
  { id: 'chat-widget', title: 'Help chat assistant', caption: 'Ask anything about EstateHawk', run: async (v) => { await v.go('/'); await v.click('button:has-text("Ask EstateHawk"), .ehc-btn, #ehChatBtn', 1.0, 1.6); await v.wait(2500); } },
  { id: 'open-dashboard', title: 'Website to dashboard', caption: 'Open your dashboard', run: async (v) => { if (!v.page.url().includes(':8199/') || v.page.url().includes('/app')) await v.go('/'); await v.click('a:has-text("Open dashboard")', 0.7, 1.9); await v.page.waitForSelector('#leadTable tbody tr', { timeout: 10000 }).catch(() => {}); await v.wait(800); } },

  // ---------- leads ----------
  { id: 'deals', title: 'Dashboard and lead list', caption: 'Every lead is scored, the best deals come first', run: async (v) => { await v.nav('deals'); await v.focus('#stats', 2.4, 1.5); await v.focus('#leadTable tbody tr', 2.6, 1.7); } },
  { id: 'deals-county', title: 'Choose a county', caption: 'Pick a county', run: async (v) => { await v.nav('deals'); await v.click('#countySel', 1.6, 1.9); await v.wait(800); await v.page.keyboard.press('Escape').catch(() => {}); } },
  { id: 'deals-search', title: 'Search leads', caption: 'Search by address or owner', run: async (v) => { await v.nav('deals'); await v.type('#leadQ', 'Main'); await v.wait(1500); await v.focus('#leadTable', 1.8, 1.4); await v.page.fill('#leadQ', '').catch(() => {}); await v.page.keyboard.press('Enter').catch(() => {}); } },
  { id: 'deals-filters', title: 'Filters', caption: 'Filter by score, amount owed and years behind', run: async (v) => { await v.nav('deals'); await v.click('#fScore', 1.2, 1.9); await v.wait(700); await v.page.keyboard.press('Escape').catch(() => {}); await v.click('#fMore', 1.6, 1.8); await v.wait(1200); await v.page.keyboard.press('Escape').catch(() => {}); await v.focus('#filterSummary', 1.6, 1.8); } },
  { id: 'deals-pages', title: 'Pages and jump to lead', caption: 'Jump to any page or lead number', run: async (v) => { await v.nav('deals'); await v.scrollTo('#pageInfo'); await v.click('#next', 1.2, 2.0); await v.wait(800); await v.click('#prev', 1.0, 2.0); } },
  { id: 'deals-bulk', title: 'Select leads, compare, export', caption: 'Select leads to compare, export or add to your pipeline', run: async (v) => { await v.nav('deals'); await v.click('#leadTable tbody tr:nth-child(1) input[type=checkbox]', 0.6, 1.8); await v.click('#leadTable tbody tr:nth-child(2) input[type=checkbox]', 0.6, 1.8); await v.click('#leadTable tbody tr:nth-child(3) input[type=checkbox]', 0.6, 1.8); await v.focus('#bulk', 2.0, 1.6); } },
  { id: 'compare', title: 'Compare leads side by side', caption: 'Compare deals side by side', run: async (v) => { await v.nav('deals'); for (const n of [1, 2, 3]) await v.click(`#leadTable tbody tr:nth-child(${n}) input[type=checkbox]`, 0.4, 1.6); await v.click('#bulkCmp', 0.8, 1.8); await v.wait(1200); await v.focus('.cmp, #modalCard', 2.6, 1.3); await v.page.keyboard.press('Escape').catch(() => {}); } },
  { id: 'mini-map', title: 'Mini map on dashboard', caption: 'Your leads on a map, right on the dashboard', run: async (v) => { await v.nav('deals'); await v.focus('#miniMap', 2.2, 1.7); } },
  { id: 'today-alerts', title: "Today's alerts on dashboard", caption: 'What changed today', run: async (v) => { await v.nav('deals'); await v.focus('#todayAlerts', 2.2, 1.8); } },
  { id: 'global-search', title: 'Global search (Ctrl K)', caption: 'Find any property in seconds', run: async (v) => { await v.type('#searchInput', 'Chestnut'); await v.wait(1200); await v.focus('#searchResults', 1.8, 1.7); await v.page.keyboard.press('Escape').catch(() => {}); await v.page.fill('#searchInput', '').catch(() => {}); } },

  // ---------- deal page ----------
  { id: 'deal-open', title: 'Open a deal', caption: 'Open any property', run: async (v) => { await v.nav('deals'); await v.click('#leadTable tbody tr b', 0.8, 1.8); await v.page.waitForSelector('.timeline', { timeout: 10000 }).catch(() => {}); await v.wait(900); } },
  { id: 'deal-gallery', title: 'Photos, satellite and street view', caption: 'Satellite, street map and Street View', run: async (v) => { await deal(v); await v.click('.gal-tabs button:has-text("Street map")', 1.0, 1.8); await v.click('.gal-tabs button:has-text("Satellite")', 1.0, 1.8); await v.focus('#gal', 1.6, 1.5); } },
  { id: 'deal-fullscreen-map', title: 'Full-screen map', caption: 'Open the map full screen', run: async (v) => { await deal(v); await v.click('.gal-fs', 0.8, 2.0); await v.wait(2200); await v.page.keyboard.press('Escape').catch(() => {}); } },
  { id: 'deal-tax', title: 'Tax history', caption: 'How many years behind and how much is owed', run: async (v) => { await deal(v); await v.focus('.timeline', 2.8, 1.8); } },
  { id: 'deal-details', title: 'Property details', caption: 'Owner, mailing address and property facts', run: async (v) => { await deal(v); await v.scrollTo('#factContacts'); await v.focus('#factContacts', 2.6, 1.6); } },
  { id: 'deal-sources', title: 'Data sources and freshness', caption: 'Source and freshness on every lead', run: async (v) => { await deal(v); await v.scrollTo('#dataCard'); await v.focus('#dataCard', 2.6, 1.8); } },
  { id: 'deal-score', title: 'Why this score', caption: 'A deal score you can explain', run: async (v) => { await deal(v); await v.scrollTo('#reasons'); await v.focus('#reasons', 2.6, 1.8); } },
  { id: 'deal-rules', title: 'State tax-sale rules', caption: 'Tax-sale rules for the state, in plain English', run: async (v) => { await deal(v); await v.scrollTo('#rulesResearch'); await v.focus('#rulesResearch', 2.6, 1.6); } },
  { id: 'deal-flood', title: 'Flood zone (FEMA)', caption: 'FEMA flood zone for every property', run: async (v) => { await deal(v); await v.scrollTo('#floodResearch'); await v.focus('#floodResearch', 2.2, 1.8); } },
  { id: 'deal-comps', title: 'Comparable sales', caption: 'Value estimate and nearby sales', run: async (v) => { await deal(v); await v.scrollTo('#compsResearch'); await v.focus('#compsResearch', 2.2, 1.8); } },
  { id: 'deal-calculator', title: 'Maximum offer calculator', caption: 'Know your maximum offer', run: async (v) => { await deal(v); await v.scrollTo('#calcCard'); await v.type('#kArv', '240000'); await v.click('#kRun', 1.0, 1.7); await v.focus('#calcCard', 2.4, 1.4); } },
  { id: 'deal-offer', title: 'Offer draft (AI letter)', caption: 'Draft an offer letter in one click', run: async (v) => { await deal(v); await v.scrollTo('#offerCard'); await v.focus('#offerCard', 1.6, 1.6); await v.click('#oGen', 1.0, 1.8); await v.wait(2000); await v.focus('#modalCard', 2.6, 1.3); await v.page.keyboard.press('Escape').catch(() => {}); } },
  { id: 'deal-contacts', title: 'Owner contacts', caption: 'Find and save owner phone and email', run: async (v) => { await deal(v); await v.scrollTo('#contactsCard'); await v.focus('#contactsCard', 2.4, 1.7); } },
  { id: 'deal-notes', title: 'Notes and follow-ups', caption: 'Notes and follow-up tasks on every deal', run: async (v) => { await deal(v); await v.scrollTo('#acts'); await v.click('#addNote', 1.4, 1.8); await v.wait(1000); await v.page.keyboard.press('Escape').catch(() => {}); } },
  { id: 'deal-pipeline', title: 'Add to pipeline', caption: 'Add the deal to your pipeline', run: async (v) => { await deal(v); await v.scroll(-6000, 600); await v.click('#listBtn', 1.4, 1.9); await v.wait(900); await v.page.keyboard.press('Escape').catch(() => {}); } },
  { id: 'deal-report', title: 'Printable due-diligence report', caption: 'Print a due-diligence report', run: async (v) => { await deal(v); await v.scroll(-6000, 600); await v.focus('#reportBtn', 1.6, 2.0); } },
  { id: 'deal-share', title: 'Share a deal', caption: 'Share a deal with your team', run: async (v) => { await deal(v); await v.scroll(-6000, 600); await v.click('#shareBtn', 1.2, 2.0); await v.wait(800); await v.page.keyboard.press('Escape').catch(() => {}); } },

  // ---------- map ----------
  { id: 'map', title: 'Map of all leads', caption: 'Every lead on the map', run: async (v) => { await v.nav('map'); await v.focus('#bigMap', 2.4, 1.4); await v.focus('#mItems .pcard', 1.8, 1.8); } },
  { id: 'map-filters', title: 'Map filters and saved searches', caption: 'Filter the map and save your search', run: async (v) => { await v.nav('map'); await v.click('#fsChoice', 1.0, 1.9); await v.wait(600); await v.page.keyboard.press('Escape').catch(() => {}); await v.click('#fyChoice', 1.0, 1.9); await v.wait(600); await v.page.keyboard.press('Escape').catch(() => {}); await v.focus('#saveSearch', 1.4, 2.0); } },
  { id: 'map-card', title: 'Lead card on the map', caption: 'Click a lead to see its deal', run: async (v) => { await v.nav('map'); await v.click('#mItems .pcard', 1.6, 1.7); await v.wait(1000); } },

  // ---------- alerts, auctions, counties ----------
  { id: 'alerts', title: 'Alerts feed', caption: 'New leads, payoffs and owner changes', run: async (v) => { await v.nav('alerts'); await v.focus('#feed', 2.4, 1.5); await v.click('#aTabs a:nth-child(4)', 1.2, 1.8); await v.wait(800); } },
  { id: 'alert-rules', title: 'Alert rules and channels', caption: 'Choose what to be alerted about, by email, SMS or Slack', run: async (v) => { await v.nav('alerts'); await v.focus('#rScore', 1.8, 1.8); await v.focus('#ch_email', 1.8, 1.8); await v.focus('#dTime', 1.6, 1.9); } },
  { id: 'auctions', title: 'Auction calendar', caption: 'Upcoming tax sales and minimum bids', run: async (v) => { await v.nav('auctions'); await v.focus('#aDays', 2.0, 1.5); await v.focus('#aList', 2.0, 1.6); } },
  { id: 'counties', title: 'Counties, sync and data grade', caption: 'Sync status and data quality for every county', run: async (v) => { await v.nav('counties'); await v.focus('#cGrid .card', 2.6, 1.7); await v.focus('#syncAll', 1.2, 2.0); } },
  { id: 'add-county', title: 'Add or request a county', caption: 'Add a county or request a new one', run: async (v) => { await v.nav('counties'); await v.click('#addCounty', 1.2, 1.9); await v.wait(1500); await v.page.keyboard.press('Escape').catch(() => {}); } },

  // ---------- outreach & reports ----------
  { id: 'outreach', title: 'Outreach pipeline', caption: 'Track every owner from first letter to closed deal', run: async (v) => { await v.nav('outreach'); await v.focus('#kanban', 2.6, 1.3); await v.focus('#fuList', 1.8, 1.7); } },
  { id: 'batch-offers', title: 'Batch offer letters', caption: 'Draft offer letters for many owners at once', run: async (v) => { await v.nav('outreach'); await v.click('#batch', 1.0, 1.9); await v.wait(1800); await v.page.keyboard.press('Escape').catch(() => {}); } },
  { id: 'reports', title: 'Reports and charts', caption: 'Leads, outreach and conversions at a glance', run: async (v) => { await v.nav('reports'); await v.focus('#kpis', 2.0, 1.5); await v.focus('#funnel', 1.8, 1.8); await v.scrollTo('#convT'); await v.focus('#convT', 1.8, 1.6); } },
  { id: 'reports-export', title: 'Export CSV or PDF', caption: 'Export to CSV or PDF', run: async (v) => { await v.nav('reports'); await v.focus('#rCsv', 1.4, 2.1); await v.focus('#rPdf', 1.2, 2.1); } },

  // ---------- settings, plans, admin ----------
  { id: 'settings-profile', title: 'Profile and offer defaults', caption: 'Your profile and offer defaults', run: async (v) => { await setTab('profile')(v); await v.focus('#pName', 1.6, 1.8); await v.focus('#oDisc', 1.6, 1.8); } },
  { id: 'settings-scoring', title: 'Deal scoring weights', caption: 'Tune how deals are scored, with a live preview', run: async (v) => { await setTab('scoring')(v); await v.focus('#sliders', 2.2, 1.5); await v.focus('#example', 2.0, 1.6); } },
  { id: 'settings-integrations', title: 'Integrations', caption: 'Connect AI, email, Slack and SMS', run: async (v) => { await setTab('integrations')(v); await v.scroll(500, 1800); } },
  { id: 'settings-team', title: 'Team', caption: 'Invite your team', run: async (v) => { await setTab('team')(v); await v.click('#tOpen', 1.4, 1.9); await v.wait(1200); await v.page.keyboard.press('Escape').catch(() => {}); } },
  { id: 'settings-api', title: 'API access', caption: 'API access on paid plans', run: async (v) => { await setTab('api')(v); await v.focus('#kNew', 1.6, 1.9); await v.scroll(500, 1600); } },
  { id: 'plans', title: 'Plans and billing', caption: 'Simple plans, cancel anytime', run: async (v) => { await setTab('billing')(v); await v.click('#bPlans', 1.0, 1.9); await v.wait(1500); await v.focus('#modalCard', 2.4, 1.2); await v.page.keyboard.press('Escape').catch(() => {}); } },
  { id: 'admin', title: 'Admin panel (super admin)', caption: 'Companies, users and messages in one place', run: async (v) => { await v.nav('admin'); await v.wait(800); await v.click('#view a:has-text("All users"), #view button:has-text("All users")', 1.0, 1.8); await v.wait(800); await v.click('#view a:has-text("Contact messages"), #view button:has-text("Contact messages")', 1.0, 1.8); } },
  { id: 'help-menu', title: 'Help and notifications', caption: 'Help and alerts are always one click away', run: async (v) => { await v.click('#bellBtn', 1.2, 2.0); await v.wait(900); await v.page.keyboard.press('Escape').catch(() => {}); await v.click('#helpBtn', 1.2, 2.0); await v.wait(900); await v.page.keyboard.press('Escape').catch(() => {}); } },
  { id: 'outro-card', title: 'End card', caption: '', run: async (v) => { await v.card('Start your free trial', 'getestatehawk.com', 3500); } },
];
