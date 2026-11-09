// EstateHawk intro AD (about 60 s): single take, every page reached by clicking, zoom + click sounds.
// Voice: tools/video/shorts/ad-voice.txt (Google AI Studio, voice Koda, emotion tags).
// T = when each sentence starts in the voice (seconds), from transcribing the voice file. Update T when the voice changes.
// Record: bash tools/video/run.sh --file shorts/ad.js --no-captions
// Join:   python3 tools/video/voiceover.py VOICE.wav OUT.mp4 tools/video/out/estatehawk-demo.mp4 --music tools/video/out/music.wav --skip 0.8 --lead 0.4
const T = (process.env.AD_T || '0,4.6,6.6,15.0,20.0,27.0,32.5,36.0,41.5,46.0').split(',').map(Number);
const O = 1.2;  // where the voice starts in the raw recording (skip 0.8 + lead 0.4)

module.exports = [
  {
    id: 'ad',
    title: 'EstateHawk intro ad',
    run: async (v) => {
      const at = (i) => v.until(T[i] + O);
      const esc = () => v.page.keyboard.press('Escape').catch(() => {});

      // 0 "Imagine knowing which homeowners are behind on their taxes... before every other investor does."
      await v.go('/');
      await v.cursorTo(980, 560);
      await v.focus('h1', 2.6, 1.55);
      await v.focus('.hero a.btn, a.btn.primary', 1.0, 1.9);

      // 1 "That's EstateHawk."
      await at(1);
      await v.click('a:has-text("Open dashboard")', 0.6, 1.9);
      await v.page.waitForSelector('#leadTable tbody tr', { timeout: 10000 }).catch(() => {});

      // 2 "Every morning, we pull tax-delinquent lists ... best deals are always right at the top."
      await at(2);
      await v.focus('#stats', 2.6, 1.5);
      await v.focus('#leadTable tbody tr', 2.6, 1.8);

      // 3 "Want something specific? Just filter by how much is owed, or how many years they're behind."
      await at(3);
      await v.click('#fOwed', 1.0, 1.9); await v.wait(500); await esc();
      await v.click('#fYears', 1.0, 1.9); await v.wait(500); await esc();

      // 4 "Click any property, and there it is. The owner, the tax history, and exactly where the data came from."
      await at(4);
      await v.click('#leadTable tbody tr b', 0.6, 1.9);
      await v.page.waitForSelector('.timeline', { timeout: 10000 }).catch(() => {});
      await v.focus('.timeline', 2.2, 1.8);
      await v.scrollTo('#dataCard');
      await v.focus('#dataCard', 1.8, 1.8);

      // 5 "Flood zone, the state's tax-sale rules, and a max-offer calculator, all on one screen."
      await at(5);
      await v.scrollTo('#floodResearch'); await v.focus('#floodResearch', 0.9, 1.7);
      await v.scrollTo('#rulesResearch'); await v.focus('#rulesResearch', 0.9, 1.5);
      await v.scrollTo('#calcCard'); await v.focus('#calcCard', 1.0, 1.4);

      // 6 "Ready to reach out? Draft an offer letter in one click."
      await at(6);
      await v.scrollTo('#offerCard');
      await v.click('#oGen', 1.6, 1.8);
      await v.wait(1200); await esc();

      // 7 "See every lead on the map, and get an alert the moment something changes."
      await at(7);
      await v.scroll(-8000, 500);
      await v.click('#nav a[href="#/map"]', 0.5, 1.8);
      await v.page.waitForSelector('#bigMap', { timeout: 10000 }).catch(() => {});
      await v.focus('#mItems .pcard', 0.9, 1.7);
      await v.click('#nav a[href="#/alerts"]', 0.5, 1.8);
      await v.focus('#feed', 1.0, 1.5);

      // 8 "Then track every owner, from the first letter, to the closed deal."
      await at(8);
      await v.click('#nav a[href="#/outreach"]', 0.5, 1.8);
      await v.focus('#kanban', 2.4, 1.3);

      // 9 "No more stale lists. No more guessing. Start your free fourteen-day trial at getestatehawk.com. Your next deal is already waiting."
      await at(9);
      await v.click('#userBtn', 0.5, 1.8);
      await v.click(':text("Visit website")', 0.4, 1.8);
      await v.page.waitForLoadState('domcontentloaded').catch(() => {});
      await v.click('header a:has-text("Pricing")', 0.4, 1.8);
      await v.page.waitForSelector('.plan.pro', { timeout: 10000 }).catch(() => {});
      await v.focus('.plan.pro', 2.4, 1.6);
      await v.card('Your next deal is already waiting', 'Start free at getestatehawk.com', 5000);
    },
  },
];
