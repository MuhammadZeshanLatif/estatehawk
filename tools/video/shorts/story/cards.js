// Renders the story-ad end cards and split-screen labels as 1920x1080 PNGs (transparent where needed).
// node cards.js OUTDIR
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const out = process.argv[2] || '.';
const icon = fs.readFileSync(path.join(__dirname, '../../../../web/icon.svg'), 'utf8');
const font = `<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800&display=swap" rel="stylesheet">`;
const base = `*{margin:0;box-sizing:border-box}body{width:1920px;height:1080px;font-family:Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased}`;
const card = (line, sub) => `<html><head>${font}<style>${base}
body{background:radial-gradient(ellipse at 50% 40%,#1E5E3B 0%,#14532D 45%,#0B2E1A 100%);color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
.logo{display:flex;align-items:center;gap:26px;margin-bottom:56px}.logo svg{width:120px;height:140px;filter:drop-shadow(0 8px 24px rgba(0,0,0,.35))}
.logo svg path:first-child{fill:#fff}.logo svg path:nth-child(2){fill:#14532D}.logo svg path:nth-child(3){fill:#fff}
.logo b{font-size:104px;font-weight:800;letter-spacing:-.03em}
h1{font-size:64px;font-weight:700;letter-spacing:-.02em;margin-bottom:28px}
p{font-size:40px;font-weight:500;color:#CDE8D4}p u{text-decoration:none;color:#fff;font-weight:700;border-bottom:4px solid #6FCF8E;padding-bottom:4px}
</style></head><body><div class="logo">${icon}<b>EstateHawk</b></div><h1>${line}</h1><p>${sub}</p></body></html>`;
const label = (a, b) => `<html><head>${font}<style>${base}body{background:transparent}
.l{position:absolute;top:54px;padding:14px 30px;border-radius:999px;font-size:30px;font-weight:800;letter-spacing:.12em}
.a{left:${480}px;transform:translateX(-50%);background:rgba(20,20,20,.72);color:#E8E8E8}
.b{left:${1440}px;transform:translateX(-50%);background:#14532D;color:#fff;box-shadow:0 6px 20px rgba(0,0,0,.3)}
.d{position:absolute;left:957px;top:0;width:6px;height:1080px;background:#fff}</style></head>
<body><div class="d"></div><div class="l a">${a}</div><div class="l b">${b}</div></body></html>`;
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  const shots = [
    ['card-dan.png', card('Your next deal is already waiting.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['card-split.png', card('Same market. Different morning.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['card-mail.png', card('Same budget. Different list.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['card-vet.png', card('Reach owners before the auction does.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['card-county.png', card('Your move, county.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['card-firstdeal.png', card('Your first deal is closer than you think.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['card-trucker.png', card('Build the life you are working for.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['card-fatherson.png', card('Old-school hustle. New-school data.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['card-partner.png', card('Don\'t quit. Upgrade.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['card-calls.png', card('Timing is everything.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['card-weekend.png', card('Same weekend. Different life.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['card-years.png', card('Same guy. Better data.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['card-driving.png', card('Save the gas.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['card-vlog.png', card('Your morning, upgraded.', 'Start your free trial at <u>getestatehawk.com</u>'), false],
    ['labels-years.png', label('2025', '2026 &middot; WITH ESTATEHAWK'), true],
    ['labels.png', label('THE OLD WAY', 'WITH ESTATEHAWK'), true],
  ];
  for (const [f, html, transparent] of shots) {
    await p.setContent(html, { waitUntil: 'networkidle' }).catch(() => {});
    await p.waitForTimeout(400);
    await p.screenshot({ path: path.join(out, f), omitBackground: transparent });
  }
  await b.close();
})();
