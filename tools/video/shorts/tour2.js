// Single-take product tour (about 45 s), no cuts: every page is reached by clicking, like a real person.
// Record: bash tools/video/run.sh --file shorts/tour2.js --no-captions
// Join:   python3 tools/video/voiceover.py VOICE.wav OUT.mp4 tools/video/out/estatehawk-demo-*.mp4 --music tools/video/out/music.wav --skip 0.8 --lead 0.4
// Times below are VOICE seconds (from tour-voice.txt, voice of 2026-11-10). O = where the voice starts in the raw recording.
const O = 1.2;
module.exports = [
  {
    id: 'tour',
    title: 'Single-take tour with voiceover',
    run: async (v) => {
      const at = (sec) => { v.log('at ' + sec); return v.until(sec + O); };
      // 0.0 "So... I've been building something for real estate investors, and it's almost ready."
      await v.go('/');
      await v.cursorTo(900, 500);
      await v.focus('h1', 2.2, 1.5);
      await at(3.6);
      await v.click('header a:has-text("Open dashboard"), a:has-text("Open dashboard")', 0.7, 1.9);
      await v.page.waitForSelector('#leadTable tbody tr', { timeout: 15000 }).catch(() => {});

      // 5.5 "This is EstateHawk. Every day, it pulls tax-delinquent lists ... scores every lead, so the best deals are always on top."
      await at(6.0);
      await v.focus('#leadTable tbody tr', 3.0, 1.7);
      await v.focus('#leadTable tbody tr td:nth-child(7), #leadTable tbody tr .score, #leadTable tbody tr', 2.2, 2.1);
      await at(15.4);
      await v.click('#leadTable tbody tr b', 0.6, 1.9);   // opens the deal page
      await v.page.waitForSelector('.timeline', { timeout: 15000 }).catch(() => {});

      // 16.2 "Open any property, and you get the owner, how many years they're behind, and how much they owe. And you can see exactly where the data came from."
      await at(16.6);
      await v.focus('.timeline', 3.0, 1.8);
      await v.scrollTo('#dataCard');
      await v.focus('#dataCard', 2.2, 1.8);

      // 24.3 "Flood zone, tax-sale rules, and a max-offer calculator are right there too."
      await at(24.3);
      await v.scrollTo('#floodResearch');
      await v.focus('#floodResearch', 1.2, 1.6);
      await v.scrollTo('#dealCalcResearch');
      await v.focus('#dealCalcResearch', 1.0, 1.4);

      // 29.2 "You can see every lead on the map..."
      await v.scroll(-6000, 700);
      await at(28.8);
      await v.click('#nav a[href="#/map"]', 0.5, 1.8);
      await v.page.waitForSelector('#bigMap', { timeout: 15000 }).catch(() => {});
      await v.focus('#bigMap', 1.0, 1.4);

      // 31.9 "...and get an alert the moment something changes."
      await at(31.5);
      await v.click('#nav a[href="#/alerts"]', 0.5, 1.8);
      await v.focus('.alert-row, table tbody tr', 1.0, 1.7);

      // 34.3 "We're starting with eighty counties in Ohio and Texas. Try it free for fourteen days, no card needed. Just go to getestatehawk dot com."
      await at(34.3);
      await v.click('#userBtn', 0.6, 1.8);
      await v.click('.dropdown a:has-text("Visit website"), .dropdown button:has-text("Visit website"), :text("Visit website")', 0.5, 1.8);
      await v.page.waitForLoadState('domcontentloaded').catch(() => {});
      await v.click('header a:has-text("Pricing"), nav a:has-text("Pricing")', 0.5, 1.8);
      await v.page.waitForSelector('.plan.pro', { timeout: 15000 }).catch(() => {});
      await v.focus('.plan.pro', 2.4, 1.6);
      await v.card('Try it free for 14 days', 'getestatehawk.com', 4000);
    },
  },
];
