// Short voiceover tour (about 45 s). Each scene matches one sentence of the voiceover in tour-voice.txt.
// Record: bash tools/video/run.sh --file shorts/tour.js --split --no-captions
// Scenes run long on purpose; tools/video/voiceover.py trims each one to its voice line.
module.exports = [
  { id: 't1-intro', run: async (v) => { await v.card('EstateHawk', 'Launching soon', 7000); } },
  {
    id: 't2-deals',
    run: async (v) => {
      await v.go('#/deals'); await v.wait(1500);
      await v.hover('#leadTable tbody tr'); await v.wait(1500);
      await v.scroll(350, 2500); await v.wait(3000); await v.scroll(-350, 1500); await v.wait(3000);
    },
  },
  {
    id: 't3-deal',
    run: async (v) => {
      const id = await v.topLeadId();
      await v.go('#/deal/' + encodeURIComponent(id)); await v.wait(3500);
      await v.scrollTo('#dataCard'); await v.wait(6000);
    },
  },
  {
    id: 't4-research',
    run: async (v) => {
      const id = await v.topLeadId();
      await v.go('#/deal/' + encodeURIComponent(id)); await v.wait(300);
      await v.scrollTo('#floodResearch'); await v.wait(3000);
      await v.scrollTo('#dealCalcResearch'); await v.wait(5000);
    },
  },
  {
    id: 't5-map',
    run: async (v) => {
      await v.go('#/map'); await v.wait(1200);
      const b = await v.page.locator('#bigMap').boundingBox().catch(() => null);
      if (b) { await v.cursorTo(b.x + b.width / 2, b.y + b.height / 2); await v.page.mouse.wheel(0, -300); }
      await v.wait(4000);
    },
  },
  { id: 't6-alerts', run: async (v) => { await v.go('#/alerts'); await v.wait(5000); } },
  {
    id: 't7-pricing',
    run: async (v) => {
      await v.go('/pricing'); await v.wait(5000);
      await v.card('Try it free for 14 days', 'getestatehawk.com', 6000);
    },
  },
];
