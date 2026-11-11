// Urdu idea pitch (not an ad): Zeeshan explains EstateHawk as his first launched startup idea (for the InnoClub assignment).
// Voice: tools/video/shorts/pitch-urdu-voice.txt (Google AI Studio, voice Koda, emotion tags). One v.mark(i) per sentence.
// Record: bash tools/video/run.sh --file shorts/pitch-urdu.js --no-captions --out tools/video/out/pitch
// Join:   python3 tools/video/fit.py tools/video/out/pitch/estatehawk-demo.mp4 VOICE.wav OUT.mp4 --t <sentence starts> --music tools/video/out/music.wav
module.exports = [
  {
    id: 'pitch',
    title: 'EstateHawk idea pitch in Urdu',
    run: async (v) => {
      const esc = () => v.page.keyboard.press('Escape').catch(() => {});
      // 0 "Assalam o alaikum, main Zeeshan hoon ... mera pehla startup idea ... EstateHawk."
      await v.card('EstateHawk', 'My first startup idea', 2600);
      await v.go('/');
      v.mark(0);
      await v.cursorTo(980, 560);
      await v.focus('h1', 3.4, 1.5);
      await v.wait(2200);

      // 1 "America mein har saal lakhon ghar maalikan property tax waqt par ada nahi kar paate ... investors aise ghar dhoondte hain."
      v.mark(1);
      await v.scroll(500, 5200);
      await v.wait(2500);
      await v.scroll(300, 3000);

      // 2 "Masla ye tha ke ye listen har county ki alag website par bikhri hoti hain ... data purana hota hai."
      v.mark(2);
      await v.scroll(350, 4500);  // stay above the pricing section: this is a pitch, not an ad
      await v.wait(3200);
      await v.scroll(-1150, 2000);

      // 3 "To maine socha ... roz sarkari county record se ... har property ko score de."
      v.mark(3);
      await v.click('a:has-text("Open dashboard")', 0.6, 1.8);
      await v.page.waitForSelector('#leadTable tbody tr', { timeout: 10000 }).catch(() => {});
      await v.focus('#stats', 2.2, 1.4);
      await v.focus('#leadTable tbody tr', 2.4, 1.7);

      // 4 "Kisi bhi property par click karein ... maalik ka naam, kitne saal ka tax, kitni raqam, data kahan se aaya."
      v.mark(4);
      await v.click('#leadTable tbody tr b', 0.6, 1.8);
      await v.page.waitForSelector('.timeline', { timeout: 10000 }).catch(() => {});
      await v.focus('.timeline', 2.2, 1.7);
      await v.scrollTo('#dataCard');
      await v.focus('#dataCard', 1.8, 1.7);

      // 5 "Saath mein naqsha bhi hai, aur alerts bhi."
      v.mark(5);
      await v.scroll(-8000, 500);
      await v.click('#nav a[href="#/map"]', 0.5, 1.7);
      await v.page.waitForSelector('#bigMap', { timeout: 10000 }).catch(() => {});
      await v.click('#nav a[href="#/alerts"]', 0.5, 1.7);
      await v.focus('#feed', 1.0, 1.4);

      // 6 "Abhi ye Ohio aur Texas ki 80 counties mein chal raha hai ... aur bhi kai ideas hain."
      v.mark(6);
      await v.click('#nav a[href="#/counties"]', 0.5, 1.7);
      await v.focus('#cGrid .card', 2.8, 1.5);
      await v.wait(3500);

      // 7 "Agar aap dekhna chahein to getestatehawk.com ... apni raye bhi dijiye ga. Bohat shukriya."
      v.mark(7);
      await esc();
      await v.card('getestatehawk.com', 'Your feedback means a lot. Thank you.', 14000);  // long, so the end of the video stays on the card
    },
  },
];
