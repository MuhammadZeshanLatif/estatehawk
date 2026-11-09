// EstateHawk demo video scenes. One scene = one part of the video.
// To show a NEW FEATURE: add a scene object below (id, title, caption, run). Nothing else needs to change.
//
// Each run(v) gets helpers from record.js:
//   v.go(path)                 open a website path ('/pricing') or app route ('#/map')
//   v.caption(text, ms)        show a caption at the bottom (stays until the next caption)
//   v.click(selector)          animated cursor moves to the element, then clicks (skips quietly if missing)
//   v.type(selector, text)     click and type like a person
//   v.scroll(px, ms)           smooth scroll the page (negative = up)
//   v.scrollTo(selector)       smooth scroll an element into view
//   v.hover(selector)          move the cursor onto an element
//   v.wait(ms)                 pause
//   v.topLeadId()              id of the highest-scored lead (for the deal page)
//   v.page                     raw Playwright page, for anything special
// Keep captions short and plain. Video is for US real estate investors.

module.exports = [
  {
    id: 'intro',
    title: 'Title card',
    run: async (v) => { await v.card('EstateHawk', 'Tax-delinquent leads, straight from the county', 3200); },
  },
  {
    id: 'home',
    title: 'Website home page',
    run: async (v) => {
      await v.go('/');
      await v.caption('Fresh tax-delinquent leads from official county records', 0);
      await v.wait(2200);
      await v.scroll(700, 2500);
      await v.scroll(700, 2500);
      await v.scroll(-1400, 1500);
    },
  },
  {
    id: 'deals',
    title: 'Leads list and filters',
    run: async (v) => {
      await v.go('#/deals');
      await v.caption('Every lead is scored, so the best deals come first', 0);
      await v.wait(2500);
      await v.hover('#leadTable tbody tr');
      await v.wait(800);
      await v.caption('Filter by years behind, amount owed and score', 0);
      await v.click('#fMore');
      await v.wait(1500);
      await v.page.keyboard.press('Escape').catch(() => {});
      await v.scroll(500, 1800);
      await v.scroll(-500, 1200);
    },
  },
  {
    id: 'deal',
    title: 'Deal page',
    run: async (v) => {
      const id = await v.topLeadId();
      await v.go('#/deal/' + encodeURIComponent(id));
      await v.caption('Owner, tax history and a deal score you can explain', 0);
      await v.wait(2500);
      await v.scrollTo('#dataCard');
      await v.caption('Source and freshness on every lead', 0);
      await v.wait(2200);
      await v.scrollTo('#floodResearch');
      await v.caption('Flood zone, tax-sale rules and comparable sales', 0);
      await v.wait(2500);
      await v.scrollTo('#dealCalcResearch');
      await v.caption('Built-in maximum offer calculator', 0);
      await v.wait(2500);
      await v.scroll(-3000, 1500);
    },
  },
  {
    id: 'offer',
    title: 'AI offer letter',
    run: async (v) => {
      const id = await v.topLeadId();
      await v.go('#/deal/' + encodeURIComponent(id) + '?offer=1');
      await v.caption('Draft an offer letter in one click', 0);
      await v.wait(3500);
    },
  },
  {
    id: 'map',
    title: 'Map',
    run: async (v) => {
      await v.go('#/map');
      await v.caption('See every lead on the map', 0);
      await v.wait(3000);
      const box = await v.page.locator('#bigMap').boundingBox().catch(() => null);
      if (box) {
        await v.cursorTo(box.x + box.width / 2, box.y + box.height / 2);
        await v.page.mouse.wheel(0, -400); await v.wait(1500);
        await v.page.mouse.wheel(0, 300); await v.wait(1200);
      }
    },
  },
  {
    id: 'auctions',
    title: 'Auction calendar',
    run: async (v) => {
      await v.go('#/auctions');
      await v.caption('Upcoming tax sales with minimum bids', 0);
      await v.wait(3000);
      await v.scroll(500, 1800);
    },
  },
  {
    id: 'alerts',
    title: 'Alerts',
    run: async (v) => {
      await v.go('#/alerts');
      await v.caption('Get alerted when a lead is new, paid off or changes owner', 0);
      await v.wait(3200);
    },
  },
  {
    id: 'outreach',
    title: 'Outreach pipeline',
    run: async (v) => {
      await v.go('#/outreach');
      await v.caption('Track every owner you contact, from first letter to deal', 0);
      await v.wait(3200);
      await v.scroll(400, 1500);
    },
  },
  {
    id: 'counties',
    title: 'Counties and data quality',
    run: async (v) => {
      await v.go('#/counties');
      await v.caption('Every county shows its sync status and data grade', 0);
      await v.wait(3200);
    },
  },
  {
    id: 'reports',
    title: 'Reports',
    run: async (v) => {
      await v.go('#/reports');
      await v.caption('Reports on leads, outreach and conversions', 0);
      await v.wait(2500);
      await v.scroll(600, 2000);
    },
  },
  {
    id: 'calculator',
    title: 'Free public profit calculator',
    run: async (v) => {
      await v.go('/deal-profit-calculator');
      await v.caption('Free deal profit calculator, no login needed', 0);
      await v.wait(3000);
      await v.scroll(400, 1500);
    },
  },
  {
    id: 'pricing',
    title: 'Pricing',
    run: async (v) => {
      await v.go('/pricing');
      await v.caption('Plans from $49 a month. 14-day free trial, no card needed', 0);
      await v.wait(3500);
    },
  },
  {
    id: 'outro',
    title: 'End card',
    run: async (v) => { await v.card('Start your free trial', 'getestatehawk.com', 3500); },
  },
];
