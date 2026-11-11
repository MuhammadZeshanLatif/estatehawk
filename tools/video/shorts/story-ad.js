// Product part of the story ad (shorts/story-ad.md): voice sentences 6, 7, 8 and the end card. The story clips are AI video.
// Record: bash tools/video/run.sh --file shorts/story-ad.js --no-captions --out tools/video/out/story
// One v.mark(i) per sentence: 0 = "Every morning...", 1 = "The owner...", 2 = "A new lead...", 3 = end card.
module.exports = [
  {
    id: 'story-product',
    title: 'EstateHawk story ad, product part',
    run: async (v) => {
      const esc = () => v.page.keyboard.press('Escape').catch(() => {});
      await v.page.addInitScript(() => document.addEventListener('DOMContentLoaded', () => {
        const s = document.createElement('style'); s.textContent = '.demo-banner{display:none!important}'; document.head.appendChild(s);
      }));  // the admin-only demo notice does not belong in an ad
      await v.go('/app');
      await v.page.waitForSelector('#leadTable tbody tr', { timeout: 10000 }).catch(() => {});
      await v.cursorTo(900, 420);

      // 0 "Every morning, EstateHawk pulls tax-delinquent properties straight from county records, across Ohio and Texas."
      v.mark(0);
      await v.focus('#stats', 2.4, 1.5);
      await v.focus('#leadTable tbody tr', 2.6, 1.8);

      // 1 "The owner, how many years behind, how much is owed, and a score that tells him exactly who to call first."
      v.mark(1);
      await v.click('#leadTable tbody tr b', 0.6, 1.9);
      await v.page.waitForSelector('.timeline', { timeout: 10000 }).catch(() => {});
      await v.focus('.timeline', 2.0, 1.8);
      await v.scrollTo('#dataCard');
      await v.focus('#dataCard', 1.6, 1.7);

      // 2 "A new lead in his county? He knows the same day."
      v.mark(2);
      await v.scroll(-8000, 500);
      await v.click('#nav a[href="#/map"]', 0.5, 1.7);
      await v.page.waitForSelector('#bigMap', { timeout: 10000 }).catch(() => {});
      await v.wait(900);
      await v.click('#nav a[href="#/alerts"]', 0.5, 1.7);
      await v.focus('#feed', 1.4, 1.5);

      // 3 "EstateHawk. Find them first. Start your free trial at getestatehawk.com."
      v.mark(3);
      await esc();
      await v.card('EstateHawk', 'Find them first. getestatehawk.com', 7000);
    },
  },
];
