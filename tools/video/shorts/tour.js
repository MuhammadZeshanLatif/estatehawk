// Short voiceover tour (about 45 s). Each scene matches one sentence of tour-voice.txt.
// Record: bash tools/video/run.sh --file shorts/tour.js --split --no-captions
// Join:   python3 tools/video/voiceover.py VOICE.wav OUT.mp4 tools/video/out/estatehawk-t*.mp4 --music tools/video/out/music.wav --marks 5.47,16.23,24.3,29.22,31.9,34.25
// The camera zooms on every v.focus() and click (zoom.py). Scenes run a bit long; voiceover.py trims each to its sentence.
module.exports = [
  { id: 't1-intro', run: async (v) => { await v.card('EstateHawk', 'Launching soon', 7000); } },
  {
    id: 't2-deals',  // "This is EstateHawk. Every day it pulls ... best deals are always on top."
    run: async (v) => {
      await v.go('#/deals'); await v.wait(700);
      await v.focus('.kpi, .stat-card, .card', 2.2, 1.5);
      await v.focus('#leadTable tbody tr', 3.2, 1.9);
      await v.click('#fMore'); await v.wait(1500);
    },
  },
  {
    id: 't3-deal',  // "Open any property ... owner, years behind, how much they owe. ... where the data came from."
    run: async (v) => {
      const id = await v.topLeadId();
      await v.go('#/deal/' + encodeURIComponent(id)); await v.wait(500);
      await v.focus('.timeline', 3.0, 1.8);
      await v.scrollTo('#dataCard');
      await v.focus('#dataCard', 2.8, 1.8);
    },
  },
  {
    id: 't4-research',  // "Flood zone, tax-sale rules, and a max-offer calculator are right there too."
    run: async (v) => {
      const id = await v.topLeadId();
      await v.go('#/deal/' + encodeURIComponent(id));
      await v.scrollTo('#floodResearch'); await v.wait(200);
      await v.focus('#floodResearch', 1.4, 1.7);
      await v.scrollTo('#dealCalcResearch');
      await v.focus('#dealCalcResearch', 1.8, 1.4);
    },
  },
  {
    id: 't5-map',  // "You can see every lead on the map..."
    run: async (v) => {
      await v.go('#/map'); await v.wait(300);
      await v.focus('#bigMap', 1.6, 1.5);
    },
  },
  {
    id: 't6-alerts',  // "...and get an alert the moment something changes."
    run: async (v) => { await v.go('#/alerts'); await v.wait(200); await v.focus('.alert-row, table tbody tr, .card', 1.6, 1.8); },
  },
  {
    id: 't7-pricing',  // "Eighty counties in Ohio and Texas. Free for fourteen days ... getestatehawk dot com."
    run: async (v) => {
      await v.go('/pricing'); await v.wait(300);
      await v.focus('.plan.pro', 3.2, 1.6);
      await v.card('Try it free for 14 days', 'getestatehawk.com', 6000);
    },
  },
];
