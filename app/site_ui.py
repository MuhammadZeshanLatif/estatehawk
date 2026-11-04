"""Marketing website: design system (CSS), icons and the product mock-ups drawn in HTML/SVG.
Design source: design/home-design.png (ChatGPT, approved by Zeeshan). Keep it pixel-close to that file."""

CSS = r"""
@font-face{font-family:Fraunces;src:url(/site/fonts/fraunces.woff2) format('woff2');font-weight:300 900;font-style:normal;font-display:swap}
@font-face{font-family:Fraunces;src:url(/site/fonts/fraunces-italic.woff2) format('woff2');font-weight:300 900;font-style:italic;font-display:swap}
@font-face{font-family:Inter;src:url(/site/fonts/inter.woff2) format('woff2');font-weight:100 900;font-style:normal;font-display:swap}
:root{--bg:#FAF7F0;--band:#F2ECE1;--card:#FFFDF9;--line:#E7DFD0;--ink:#17301F;--text:#3D4A41;--muted:#6E776F;--green:#1A4A30;--green2:#215A3B;--leaf:#2E7D4F;--mint:#E3EFE4;--sand:#EFE7D8;--amber:#E2A13A;--amber2:#F6E3BE;--r:14px;--max:1320px;
--serif:Fraunces,ui-serif,Georgia,serif;--sans:Inter,ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 var(--sans);-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
img,svg{display:block;max-width:100%}a{color:inherit;text-decoration:none}button{font:inherit}
h1,h2,h3{color:var(--ink);font-family:var(--serif);font-weight:600;letter-spacing:-.02em;margin:0;line-height:1.08;font-variation-settings:"SOFT" 0,"WONK" 0}
h1{font-size:clamp(38px,4.1vw,58px)}h2{font-size:clamp(28px,2.7vw,38px)}h3{font-size:22px}
p{margin:0}.wrap{max-width:var(--max);margin:0 auto;padding:0 24px}
.ital{font-style:italic;font-weight:500}
.swoosh{position:relative;white-space:nowrap;display:inline-block}
.swoosh:after{content:"";position:absolute;left:-2%;right:-4%;bottom:-.16em;height:.32em;background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 16' preserveAspectRatio='none'%3E%3Cpath d='M2 12C55 2 140 2 198 9' fill='none' stroke='%23E2A13A' stroke-width='4.5' stroke-linecap='round'/%3E%3C/svg%3E") no-repeat center/100% 100%}
.uline{display:block;width:120px;height:12px;margin-top:10px;background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 12'%3E%3Cpath d='M2 9C40 2 85 2 118 6' fill='none' stroke='%23E2A13A' stroke-width='3.5' stroke-linecap='round'/%3E%3C/svg%3E") no-repeat}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;height:52px;padding:0 26px;border-radius:9px;font-weight:600;font-size:16px;border:1.5px solid transparent;cursor:pointer;transition:background .15s,transform .15s,box-shadow .15s;white-space:nowrap}
.btn svg{width:18px;height:18px}.btn:active{transform:translateY(1px)}
.btn-green{background:var(--green);color:#fff}.btn-green:hover{background:#123a25;box-shadow:0 8px 20px rgba(26,74,48,.22)}
.btn-line{background:#fff;color:var(--ink);border-color:#CFC6B5}.btn-line:hover{border-color:var(--green)}
.btn-cream{background:var(--amber2);color:var(--ink)}.btn-cream:hover{background:#f1d7a4}
.btn-sm{height:44px;padding:0 20px;font-size:15px;border-radius:8px}
.btn-block{width:100%}
/* header */
.hdr{position:sticky;top:0;z-index:50;background:rgba(250,247,240,.92);backdrop-filter:saturate(1.4) blur(10px);-webkit-backdrop-filter:saturate(1.4) blur(10px);border-bottom:1px solid transparent}
.hdr.scrolled{border-color:var(--line)}
.hdr .wrap{display:flex;align-items:center;height:78px;gap:28px}
.brand{display:flex;align-items:center;gap:10px;font:700 25px/1 var(--sans);color:var(--green);letter-spacing:-.02em}
.brand img{width:34px;height:40px}
.nav{display:flex;gap:34px;margin-left:auto;margin-right:auto}.nav a{font-weight:500;font-size:15.5px;color:var(--ink)}.nav a:hover,.nav a[aria-current]{color:var(--leaf)}
.hdr-cta{display:flex;align-items:center;gap:26px}.hdr-cta .signin{font-weight:500;color:var(--ink)}
.menu-btn{display:none;margin-left:auto;background:none;border:0;padding:8px;color:var(--ink)}
/* hero */
.hero{position:relative;overflow:hidden;padding:22px 0 26px}
.hero .wrap{position:relative;z-index:1;display:grid;grid-template-columns:.84fr 1.16fr;gap:44px;align-items:center}
.hero h1{max-width:640px;letter-spacing:-.028em}
.hero .lead{font-size:18px;line-height:1.55;color:var(--text);max-width:520px;margin:24px 0 30px}
.cta-row{display:flex;gap:16px;flex-wrap:wrap}
.ticks{display:flex;flex-wrap:nowrap;gap:12px 0;margin-top:28px;font-size:13px;color:var(--text);white-space:nowrap}
.ticks span{display:flex;align-items:center;gap:7px;padding:0 14px;border-left:1px solid var(--line)}.ticks span:first-child{padding-left:0;border:0}
.ticks svg{width:17px;height:17px;color:var(--green)}
.sun{position:absolute;right:-130px;top:-60px;width:520px;height:520px;border-radius:50%;background:radial-gradient(circle at 40% 40%,#F8E3BE 0,#F6E0B9 45%,rgba(246,224,185,0) 70%);pointer-events:none}
/* browser mock */
.browser{position:relative;background:#fff;border-radius:14px;box-shadow:0 30px 70px -20px rgba(23,48,31,.28),0 0 0 1px rgba(23,48,31,.08);overflow:hidden;font-family:var(--sans)}
.browser .bar{height:34px;display:flex;align-items:center;gap:7px;padding:0 14px;background:#F4F1EB;border-bottom:1px solid #E8E2D6}
.browser .bar i{width:10px;height:10px;border-radius:50%;display:block}.browser .bar i:nth-child(1){background:#F26B5F}.browser .bar i:nth-child(2){background:#F5BE4F}.browser .bar i:nth-child(3){background:#5FC454}
.browser .url{margin:0 auto;font-size:11px;color:#7d7a72;background:#fff;border-radius:6px;padding:3px 60px;display:flex;align-items:center;gap:5px}
.app{display:grid;grid-template-columns:160px 1fr;min-height:340px}
.app .side{background:var(--green);color:#E3EDE6;padding:16px 11px;font-size:12.5px}
.app .side .lg{display:flex;align-items:center;gap:7px;font-weight:700;font-size:14px;color:#fff;padding:2px 6px 18px}
.app .side .lg img{width:20px;height:24px;filter:brightness(0) invert(1)}
.app .side a{display:flex;align-items:center;gap:9px;padding:7px 9px;border-radius:7px;margin-bottom:2px}
.app .side a svg{width:14px;height:14px;opacity:.9}.app .side a.on{background:rgba(255,255,255,.14);color:#fff}
.app .main{padding:16px 16px 14px;background:#FCFBF8;min-width:0}
.app .top{display:flex;align-items:center;gap:8px;margin-bottom:10px}.app .top b{font-size:18px;color:var(--ink)}.app .top small{font-size:10.5px;color:var(--muted)}
.chip{display:inline-flex;align-items:center;gap:5px;font-size:11px;color:#3a463e;border:1px solid #E1DACB;background:#fff;border-radius:6px;padding:5px 8px;white-space:nowrap}
.chip svg{width:10px;height:10px}.chips{display:flex;gap:6px;margin-bottom:12px;flex-wrap:nowrap;overflow:hidden}
.split{display:grid;grid-template-columns:1fr 1.32fr;gap:10px}
.mapbox{border-radius:8px;overflow:hidden;border:1px solid #E6E0D3;position:relative;min-height:220px;background:#EEF1E6}
.mapbox svg.map{width:100%;height:100%;position:absolute;inset:0}
.zoom{position:absolute;right:7px;bottom:7px;background:#fff;border:1px solid #ddd;border-radius:5px;font-size:11px;line-height:16px;text-align:center;width:18px;color:#444}
.tbl{border:1px solid #E6E0D3;border-radius:8px;background:#fff;font-size:11px}
.tbl .th{display:grid;grid-template-columns:1fr 62px 62px;padding:7px 9px;color:var(--muted);border-bottom:1px solid #EEE8DC}
.tbl .tr{display:grid;grid-template-columns:1fr 62px 62px;align-items:center;padding:9px 10px;border-bottom:1px solid #F1ECE2}.tbl .tr:last-child{border:0}
.tbl .p{display:flex;align-items:center;gap:7px;min-width:0}.tbl .p img{width:36px;height:27px;border-radius:3px;object-fit:cover;flex:none}
.tbl .p b{display:block;font-size:11px;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.tbl .p span{color:var(--muted);font-size:9px;white-space:nowrap}
.score{display:inline-block;background:#DDEED6;color:#1E5B33;font-weight:700;border-radius:5px;padding:3px 7px;font-size:11px;text-align:center}
.tbl .amt{text-align:right;color:var(--ink);font-weight:500}
/* strip */
.strip{background:var(--band);border-radius:16px;display:grid;grid-template-columns:2.1fr repeat(3,1fr);align-items:center;padding:20px 34px;margin-top:8px}
.strip h2{font-size:24px;font-weight:500;letter-spacing:-.01em}
.strip .stat{display:flex;align-items:center;gap:14px;padding-left:30px;border-left:1px solid #DCD3C2}
.strip .stat svg{width:30px;height:30px;color:var(--green)}
.strip .stat b{display:block;font-size:22px;color:var(--ink);line-height:1.1;font-weight:700}.strip .stat span{font-size:14px;color:var(--text)}
/* sections */
.sec{padding:46px 0}.sec-tight{padding:30px 0}
.sec-head{text-align:center;max-width:820px;margin:0 auto 24px}.sec-head p{margin-top:8px;font-size:17px;color:var(--text)}
.steps{display:grid;grid-template-columns:1fr 36px 1fr 36px 1fr;align-items:center}
.step{display:flex;gap:20px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:22px 24px;height:100%}
.step .ill{flex:none;width:92px;height:92px}
.step .n{display:inline-grid;place-items:center;width:30px;height:30px;border-radius:50%;background:var(--amber2);color:var(--ink);font-weight:700;font-size:14px;margin-right:10px}
.step h3{display:flex;align-items:center;font-size:19px;margin-bottom:8px}.step p{font-size:14.5px;line-height:1.55}
.arrow{color:#6B7A6F;display:grid;place-items:center}.arrow svg{width:22px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.feat{display:flex;gap:18px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:20px 22px}
.ico{flex:none;width:58px;height:58px;border-radius:50%;background:var(--sand);display:grid;place-items:center;color:var(--green)}.ico svg{width:28px;height:28px;stroke-width:2}
.feat h3{font:700 17px/1.3 var(--sans);letter-spacing:-.01em;margin-bottom:5px}.feat p{font-size:14px;line-height:1.55}
.feat:hover{border-color:#cfc4ae;box-shadow:0 10px 30px -18px rgba(23,48,31,.35)}
/* property mock */
.shot{max-width:1140px;margin:10px auto 0}
.prop{display:grid;grid-template-columns:150px 1fr;min-height:420px}
.prop .main{padding:16px 18px;background:#FCFBF8}
.prop .nav2{display:flex;justify-content:space-between;align-items:center;font-size:11.5px;color:#47534b;margin-bottom:12px;white-space:nowrap}
.mini{display:inline-flex;align-items:center;gap:5px;white-space:nowrap;border:1px solid #DED7C8;background:#fff;border-radius:6px;padding:5px 9px;font-size:10.5px;color:#2b3a30;font-weight:500}
.mini.g{background:var(--green);border-color:var(--green);color:#fff}.mini svg{width:11px;height:11px}
.pgrid{display:grid;grid-template-columns:1fr 1.2fr 1.05fr;gap:16px}
.photo{border-radius:8px;overflow:hidden;aspect-ratio:3/2}.photo img{width:100%;height:100%;object-fit:cover}
.thumbs{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:6px}.thumbs img,.thumbs span{border-radius:5px;aspect-ratio:4/3;object-fit:cover;width:100%;height:auto}
.thumbs span{background:#ECE7DD;display:grid;place-items:center;font-size:11px;color:#56615a;font-weight:600}
.ptitle h3{font:700 22px/1.15 var(--sans);letter-spacing:-.02em}.ptitle p{font-size:11.5px;color:var(--muted);display:flex;gap:4px;align-items:center;margin-top:3px}.ptitle svg{width:11px}
.acts{display:flex;gap:6px;justify-content:flex-end;flex-wrap:nowrap}
.scorebox{border:1px solid #EAE3D5;border-radius:9px;background:#fff;padding:12px;margin-top:12px}
.scorebox .row1{display:grid;grid-template-columns:auto 1fr;gap:14px;align-items:center;padding-bottom:12px;border-bottom:1px solid #F0EADF}
.big92{font-size:10.5px;color:#47534b;text-align:center}.big92 b{display:block;background:#DDEED6;color:#1E5B33;border-radius:8px;font-size:21px;padding:6px 14px;margin-top:4px}
.why{font-size:10.5px;line-height:1.45;color:#46524a;display:flex;gap:6px}.why svg{width:12px;flex:none;color:var(--amber)}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);padding-top:10px;font-size:10px;color:var(--muted)}.kpis b{display:block;font-size:15px;color:var(--ink);margin-top:2px}
.owner{border:1px solid #EAE3D5;border-radius:9px;background:#fff;padding:12px;font-size:11px;color:#2d3b32;margin-top:12px}
.owner h4{margin:0 0 8px;font-size:12px;color:var(--ink)}.owner div{display:flex;gap:7px;align-items:flex-start;margin-bottom:6px}.owner svg{width:12px;flex:none;margin-top:2px;color:#56615a}
.tabs{display:flex;gap:18px;font-size:10.5px;color:#56615a;border-bottom:1px solid #ECE6DA;padding:0 6px 7px}.tabs b{color:var(--ink);border-bottom:2px solid var(--green);padding-bottom:6px;margin-bottom:-8px}
.notes{padding:10px 6px;font-size:10.5px}.notes div{display:flex;gap:8px;margin-bottom:9px}.notes small{display:block;color:var(--muted);font-size:9.5px}.notes svg{width:12px;color:#56615a;flex:none;margin-top:1px}
.lower{display:grid;grid-template-columns:1.05fr 2.25fr;gap:14px;margin-top:14px}
.lower .mapbox{min-height:150px}
/* pricing */
.pricing{display:grid;grid-template-columns:1.2fr 1fr 1fr 1fr;gap:20px;align-items:stretch}
.pintro h2{font-size:clamp(28px,2.7vw,38px)}.pintro p{margin-top:18px;font-size:16px}
.plan{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:24px 24px 22px;display:flex;flex-direction:column;position:relative}
.plan h3{font-size:22px}.price{display:flex;align-items:baseline;gap:8px;margin:6px 0 16px}.price b{font:700 38px/1 var(--sans);color:var(--ink);letter-spacing:-.03em}.price span{font-size:14px}
.plan ul{list-style:none;padding:0;margin:0 0 20px;flex:1}.plan li{display:flex;gap:9px;align-items:flex-start;font-size:14.5px;margin-bottom:7px}.plan li svg{width:16px;flex:none;margin-top:4px;color:var(--green)}
.plan.pro{background:var(--green);border-color:var(--green);color:#E7EFE9}.plan.pro h3,.plan.pro .price b{color:#fff}.plan.pro li svg{color:#BFE0C8}
.badge{position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:var(--amber);color:#2b2112;font-size:11px;font-weight:700;letter-spacing:.08em;padding:4px 12px;border-radius:999px}
/* faq */
.faqgrid{display:grid;grid-template-columns:1fr 2.6fr;gap:40px}
.faq details{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-bottom:8px;padding:0 18px}
.faq summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:12px;padding:11px 0;font-weight:600;color:var(--ink);font-size:15.5px}
.faq summary::-webkit-details-marker{display:none}.faq summary svg{width:18px;transition:transform .2s;flex:none}.faq details[open] summary svg{transform:rotate(180deg)}
.faq details p{padding:0 0 13px;font-size:14.5px}
/* cta band */
.band{background:var(--green);color:#E5EEE8;position:relative;overflow:hidden}
.band .wrap{display:flex;align-items:center;justify-content:space-between;gap:30px;padding-top:34px;padding-bottom:34px;position:relative}
.band h2{color:#fff;font-size:clamp(26px,2.6vw,36px)}.band p{margin-top:8px;font-size:16.5px}
.band .mark{position:absolute;left:60px;top:50%;transform:translateY(-38%);width:210px;height:210px;border-radius:50%;background:rgba(255,255,255,.06);display:grid;place-items:center}
.band .mark svg{margin-left:30px}
.band .txt{padding-left:240px}
/* footer */
.ftr{padding:34px 0 28px;font-size:14px}
.ftr .wrap{display:grid;grid-template-columns:1.4fr 1fr 1fr 1fr 1.3fr;gap:30px}
.ftr h4{margin:0 0 10px;font-size:14px;color:var(--ink)}.ftr ul{list-style:none;padding:0;margin:0}.ftr li{margin-bottom:6px}.ftr a:hover{color:var(--leaf)}
.ftr .about p{margin-top:12px;color:var(--muted)}.ftr .legal{color:var(--muted);border-left:1px solid var(--line);padding-left:28px}
/* inner pages */
.phero{padding:56px 0 26px;text-align:center}.phero p{max-width:640px;margin:16px auto 0;font-size:18px}
.eyebrow{display:inline-block;font-size:12.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--leaf);margin-bottom:14px}
.crumbs{font-size:13px;color:var(--muted);margin-bottom:10px}.crumbs a:hover{color:var(--leaf)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:56px;align-items:center}.row2.rev>:first-child{order:2}
.row2 h2{font-size:clamp(28px,3vw,38px)}.row2 p{margin-top:14px;font-size:17px}
.list{list-style:none;padding:0;margin:18px 0 0}.list li{display:flex;gap:10px;margin-bottom:10px;font-size:15.5px}.list svg{width:18px;flex:none;margin-top:4px;color:var(--green)}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:26px}
.prose{max-width:760px;margin:0 auto}.prose h2{font-size:28px;margin:38px 0 12px}.prose h3{font-size:21px;margin:26px 0 8px}.prose p,.prose li{font-size:17px;line-height:1.75}.prose p{margin-bottom:14px}.prose a{color:var(--leaf);text-decoration:underline}
.cgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.county{display:flex;justify-content:space-between;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;font-size:15px}.county b{color:var(--ink)}.county span{font-size:13px;color:var(--muted)}
.states{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}
.state{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:22px}.state h3{font-size:24px}.state p{margin-top:6px}.state:hover{border-color:#cfc4ae}
.form{max-width:440px;margin:0 auto;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:34px;box-shadow:0 30px 60px -40px rgba(23,48,31,.4)}
.form h1{font-size:34px;text-align:center}.form .sub{text-align:center;margin:8px 0 22px;color:var(--muted)}
.field{margin-bottom:14px}.field label{display:block;font-size:14px;font-weight:600;color:var(--ink);margin-bottom:6px}
.field input,.field select,.field textarea{width:100%;height:48px;border:1px solid #D7CEBD;border-radius:9px;background:#fff;padding:0 14px;font:16px var(--sans);color:var(--ink)}
.field textarea{height:120px;padding:12px 14px;resize:vertical}
.field input:focus,.field select:focus,.field textarea:focus{outline:0;border-color:var(--leaf);box-shadow:0 0 0 3px rgba(46,125,79,.15)}
.msg{display:none;margin-bottom:14px;padding:11px 14px;border-radius:9px;font-size:14.5px}.msg.err{display:block;background:#FDECEA;color:#9B2C22}.msg.ok{display:block;background:var(--mint);color:#1E5B33}
.hp{position:absolute;left:-5000px}
.alt{text-align:center;margin-top:16px;font-size:14.5px}.alt a{color:var(--leaf);font-weight:600}
.cmp{width:100%;border-collapse:collapse;font-size:15px;background:var(--card);border:1px solid var(--line);border-radius:var(--r);overflow:hidden}
.cmp th,.cmp td{padding:13px 16px;border-bottom:1px solid var(--line);text-align:center}.cmp th:first-child,.cmp td:first-child{text-align:left}.cmp thead th{background:var(--band);color:var(--ink)}
.cmp svg{width:18px;margin:0 auto;color:var(--green)}
.e404{text-align:center;padding:110px 0}.e404 h1{font-size:90px}
.skip{position:absolute;left:-999px}.skip:focus{left:12px;top:12px;z-index:99;background:#fff;padding:8px 12px}
/* responsive */
@media (max-width:1060px){.hero .wrap{grid-template-columns:1fr}.hero h1,.hero .lead{max-width:none}.pricing{grid-template-columns:1fr 1fr}.pintro{grid-column:1/-1}.ftr .wrap{grid-template-columns:1fr 1fr 1fr}.ftr .about,.ftr .legal{grid-column:1/-1;border:0;padding:0}}
@media (max-width:900px){.nav,.hdr-cta{display:none}.menu-btn{display:block}.hdr.open .nav,.hdr.open .hdr-cta{display:flex;position:absolute;left:0;right:0;background:var(--bg);flex-direction:column;align-items:flex-start;padding:16px 24px;gap:16px;border-bottom:1px solid var(--line)}
.hdr.open .nav{top:78px}.hdr.open .hdr-cta{top:250px}
.strip{grid-template-columns:1fr 1fr 1fr;gap:16px;padding:22px}.strip h2{grid-column:1/-1}.strip .stat{padding-left:0;border:0}
.steps{grid-template-columns:1fr;gap:12px}.arrow{transform:rotate(90deg);height:24px}.grid3{grid-template-columns:1fr 1fr}
.faqgrid,.row2{grid-template-columns:1fr;gap:26px}.row2.rev>:first-child{order:0}.pgrid{grid-template-columns:1fr 1fr}.pgrid>:last-child{grid-column:1/-1}
.band .wrap{flex-direction:column;align-items:flex-start}.band .txt{padding-left:0}.band .mark{display:none}}
@media (max-width:640px){.ticks{flex-wrap:wrap;white-space:normal}body{font-size:15.5px}.wrap{padding:0 18px}.hero{padding-top:18px}.hero .lead{font-size:17px}.btn{height:50px;padding:0 20px}.cta-row .btn{flex:1 1 100%}
.app,.prop{grid-template-columns:1fr}.app .side,.prop .side{display:none}.split{grid-template-columns:1fr}.mapbox{min-height:150px}
.grid3,.pricing,.strip{grid-template-columns:1fr}.ftr .wrap{grid-template-columns:1fr 1fr}.sec{padding:52px 0}.pgrid,.lower{grid-template-columns:1fr}.ticks span{border:0;padding-left:0;padding-right:16px}.sun{width:320px;height:320px;right:-150px}}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
"""

_P = {
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "play": '<path d="M8 5.5v13l11-6.5z" fill="currentColor" stroke="none"/>',
    "card": '<rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3 10h18M7 15h3"/>',
    "moon": '<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/>',
    "layers": '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
    "users": '<circle cx="9" cy="8" r="3.2"/><path d="M3 19c.6-3.3 3-5 6-5s5.4 1.7 6 5"/><circle cx="17" cy="9" r="2.5"/><path d="M16.5 14c2.3.2 4 1.7 4.5 4.5"/>',
    "pin": '<path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z" fill="currentColor" stroke="none"/><circle cx="12" cy="9.5" r="2.6" fill="#fff" stroke="none"/>',
    "pin-o": '<path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    "bars": '<rect x="4" y="13" width="4" height="7" rx="1" fill="currentColor" stroke="none"/><rect x="10" y="9" width="4" height="11" rx="1" fill="currentColor" stroke="none"/><rect x="16" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c.8-4.4 3.9-7 8-7s7.2 2.6 8 7"/>',
    "doc": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6M9 8h2"/>',
    "bell": '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    "team": '<circle cx="12" cy="7.5" r="2.8"/><circle cx="5.5" cy="10" r="2.2"/><circle cx="18.5" cy="10" r="2.2"/><path d="M7 19c.5-3 2.4-4.8 5-4.8s4.5 1.8 5 4.8M2 18c.3-2 1.6-3.3 3.4-3.5M22 18c-.3-2-1.6-3.3-3.4-3.5"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "chev": '<path d="M6 9l6 6 6-6"/>',
    "phone": '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    "home": '<path d="M4 11l8-7 8 7M6 9.5V20h12V9.5M10 20v-5h4v5"/>',
    "grid": '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
    "leads": '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 9h8M8 13h8M8 17h5"/>',
    "map": '<path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2z"/><path d="M9 4v14M15 6v14"/>',
    "county": '<path d="M5 4h14v16H5z"/><path d="M9 8h6M9 12h6M9 16h3"/>',
    "funnel": '<path d="M4 5h16l-6 7v6l-4 2v-8z"/>',
    "export": '<path d="M12 3v12M7 8l5-5 5 5M5 15v4h14v-4"/>',
    "filter": '<path d="M4 6h16M7 12h10M10 18h4"/>',
    "send": '<path d="M3 11l18-8-8 18-2-8z"/>',
    "bookmark": '<path d="M6 3h12v18l-6-4-6 4z"/>',
    "back": '<path d="M15 6l-6 6 6 6"/>',
    "fwd": '<path d="M9 6l6 6-6 6"/>',
    "spark": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" fill="currentColor" stroke="none"/>',
    "note": '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 9h8M8 13h5"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "target": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor"/>',
    "dollar": '<path d="M12 3v18M16.5 7.5c-.8-1.4-2.4-2.2-4.5-2.2-2.6 0-4.3 1.3-4.3 3.2 0 4.5 9 2.4 9 7 0 2-1.8 3.4-4.7 3.4-2.3 0-4-1-4.8-2.6"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    "lock": '<rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    "chart": '<path d="M4 19h16M7 16v-5M12 16V7M17 16v-8"/>',
}


def ic(name, cls=""):
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true"{f" class={cls!r}" if cls else ""}>{_P[name]}</svg>')


# -------------------------------------------------- step illustrations (flat, like the design)
ILL_MAP = """<svg class="ill" viewBox="0 0 90 90" aria-hidden="true"><path d="M10 26l22-8 24 8 24-8v48l-24 8-24-8-22 8z" fill="#CFE0BF"/><path d="M32 18v48l24 8V26z" fill="#BCD3A8"/><path d="M10 26l22-8v48l-22 8z" fill="#DCE9CF"/><path d="M45 8c-7.7 0-14 6-14 13.6C31 32 45 45 45 45s14-13 14-23.4C59 14 52.7 8 45 8z" fill="#16492F"/><circle cx="45" cy="21.5" r="5" fill="#fff"/></svg>"""
ILL_DB = """<svg class="ill" viewBox="0 0 90 90" aria-hidden="true"><ellipse cx="38" cy="66" rx="24" ry="8" fill="#1E5B33"/><rect x="14" y="52" width="48" height="14" fill="#1E5B33"/><ellipse cx="38" cy="52" rx="24" ry="8" fill="#2E7D4F"/><ellipse cx="38" cy="48" rx="24" ry="8" fill="#1E5B33"/><rect x="14" y="34" width="48" height="14" fill="#1E5B33"/><ellipse cx="38" cy="34" rx="24" ry="8" fill="#2E7D4F"/><ellipse cx="38" cy="30" rx="24" ry="8" fill="#E9C985"/><rect x="14" y="20" width="48" height="10" fill="#E9C985"/><ellipse cx="38" cy="20" rx="24" ry="8" fill="#F3DCA8"/><path d="M78 20a12 12 0 1 1-13.5-15.5A9.5 9.5 0 0 0 78 20z" fill="#E2A13A"/></svg>"""
ILL_HOUSE = """<svg class="ill" viewBox="0 0 90 90" aria-hidden="true"><rect x="62" y="20" width="7" height="14" fill="#8A5A3B"/><path d="M45 10L8 42h8v36h58V42h8z" fill="#F4E3C3"/><path d="M45 6L4 42l5 5 36-31 36 31 5-5z" fill="#1E5B33"/><rect x="24" y="48" width="16" height="16" fill="#E2A13A"/><path d="M32 48v16M24 56h16" stroke="#F4E3C3" stroke-width="2"/><rect x="50" y="50" width="14" height="28" fill="#1E5B33"/><rect x="2" y="78" width="86" height="4" rx="2" fill="#CFE0BF"/></svg>"""


def logo(href="/", alt="EstateHawk home"):
    return (f'<a class="brand" href="{href}" aria-label="{alt}"><img src="/site/logo-mark.svg" width="34" height="40" alt="">'
            f'<span>EstateHawk</span></a>')


def map_svg(pins, seed=0):
    """A light street map like the design (parks, river, roads) with green location pins."""
    roads = ("M-5 60 C40 55 80 70 130 62 S220 50 300 58", "M-5 140 C60 130 120 150 200 138 S260 128 300 135",
             "M60 -5 C70 40 55 90 70 140 S90 210 80 260", "M170 -5 C160 50 185 100 175 160 S165 220 185 260",
             "M-5 100 C70 105 150 92 300 100", "M230 -5 C225 60 240 140 230 260", "M120 -5 C125 80 110 160 125 260")
    r = "".join(f'<path d="{d}" stroke="#fff" stroke-width="{6 if i < 4 else 3.5}" fill="none"/>' for i, d in enumerate(roads))
    parks = ('<path d="M18 168c20-10 44-6 50 10s-8 32-30 30-34-28-20-40z" fill="#D7E6C8"/>'
             '<path d="M200 20c22-6 46 6 44 24s-26 26-44 18-22-36 0-42z" fill="#D7E6C8"/>'
             '<path d="M-5 210 C40 200 80 225 130 215 S210 195 300 205" stroke="#B9D4E6" stroke-width="10" fill="none"/>')
    p = "".join(f'<g transform="translate({x - 9} {y - 22})"><path d="M9 22s-8-7.3-8-13.2A8 8 0 0 1 17 8.8C17 14.7 9 22 9 22z" fill="#16492F"/>'
                f'<circle cx="9" cy="8.8" r="3.1" fill="#fff"/></g>' for x, y in pins)
    return (f'<svg class="map" viewBox="0 0 300 250" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
            f'<rect width="300" height="250" fill="#EEF1E6"/>{parks}{r}{p}</svg>')


SIDE = [("grid", "Dashboard"), ("leads", "Leads"), ("map", "Map"), ("county", "Counties"), ("funnel", "Pipeline"), ("users", "Team")]


def side_nav(active):
    items = "".join(f'<a class="{"on" if n == active else ""}">{ic(i)}{n}</a>' for i, n in SIDE)
    return f'<div class="side"><div class="lg"><img src="/site/logo-mark.svg" alt="" width="20" height="24">EstateHawk</div>{items}</div>'


def browser(inner, url="getestatehawk.com/app", label="EstateHawk app preview"):
    return (f'<div class="browser" role="img" aria-label="{label}"><div class="bar"><i></i><i></i><i></i>'
            f'<span class="url">{ic("lock")}{url}</span></div>{inner}</div>')


LEADS = [("house-main", "1287 Maple Ave", "Columbus, OH 43211", 92, "$12,480"), ("house-brick", "436 E Northwood St", "Columbus, OH 43224", 88, "$8,320"),
         ("house-grey", "2447 Lindell Rd", "Columbus, OH 43229", 85, "$6,910"), ("house-bungalow", "3820 Clifford Ave", "Columbus, OH 43227", 82, "$5,760")]


def leads_mock():
    rows = "".join(f'<div class="tr"><div class="p"><img src="/site/img/{img}-sm.webp" alt="" width="30" height="23" loading="lazy"><div style="min-width:0"><b>{a}</b><span>{c}</span></div></div>'
                   f'<div style="text-align:center"><span class="score">{s}</span></div><div class="amt">{o}</div></div>' for img, a, c, s, o in LEADS)
    inner = (f'<div class="app">{side_nav("Leads")}<div class="main"><div class="top"><b>Leads</b><small>1,248 properties</small>'
             f'<span class="chip" style="margin-left:auto">{ic("export")} Export</span></div>'
             f'<div class="chips"><span class="chip">County: Franklin, OH {ic("chev")}</span><span class="chip">Tax status: Delinquent {ic("chev")}</span>'
             f'<span class="chip">Min. score: 70+ {ic("chev")}</span><span class="chip">{ic("filter")} More filters</span></div>'
             f'<div class="split"><div class="mapbox">{map_svg([(58, 68), (150, 52), (96, 118), (210, 150), (70, 170), (180, 210)])}<span class="zoom">+<br>&minus;</span></div>'
             f'<div class="tbl"><div class="th"><span>Property</span><span style="text-align:center">Deal score</span><span style="text-align:right">Taxes owed</span></div>{rows}</div></div></div></div>')
    return browser(inner, label="EstateHawk leads list with a map of tax-delinquent properties")


def property_mock():
    inner = (f'<div class="prop app">{side_nav("Leads")}<div class="main">'
             f'<div class="nav2"><span style="display:flex;align-items:center;gap:4px">{ic("back")} Back to leads</span><span style="display:flex;gap:6px"><span class="mini">{ic("back")} Prev</span><span class="mini">Next {ic("fwd")}</span></span></div>'
             f'<div class="pgrid"><div><div class="photo"><img src="/site/img/house-main.webp" alt="White single-story house with a front porch, a tax-delinquent lead" width="600" height="400" loading="lazy"></div>'
             f'<div class="thumbs"><img src="/site/img/house-main-sm.webp" alt="" width="160" height="120" loading="lazy"><img src="/site/img/interior-living-sm.webp" alt="" width="160" height="120" loading="lazy">'
             f'<img src="/site/img/interior-kitchen-sm.webp" alt="" width="160" height="120" loading="lazy"><span>+6</span></div></div>'
             f'<div><div class="ptitle"><h3>1287 Maple Ave</h3><p>{ic("pin-o")} Columbus, OH 43211</p></div>'
             f'<div class="scorebox"><div class="row1"><div class="big92">AI Deal Score<b>92</b></div><div class="why">{ic("spark")}High equity, significant tax delinquency, and strong investment potential.</div></div>'
             f'<div class="kpis"><div>Est. value<b>$184,000</b></div><div>Taxes owed<b>$12,480</b></div><div>Years delinquent<b>3</b></div></div></div></div>'
             f'<div><div class="acts"><span class="mini g">{ic("send")} Send offer</span><span class="mini">{ic("phone")} Call owner</span><span class="mini">{ic("bookmark")} Save deal</span></div>'
             f'<div class="owner"><h4>Owner details</h4><div>{ic("user")}<b>James R. Whitaker</b></div><div>{ic("phone")}(614) 555-0187</div><div>{ic("mail")}jwhitaker@email.com</div>'
             f'<div>{ic("home")}1287 Maple Ave<br>Columbus, OH 43211</div></div></div></div>'
             f'<div class="lower"><div class="mapbox">{map_svg([(150, 125)])}</div><div><div class="tabs"><b>Notes &amp; activity</b><span>Property details</span><span>Tax history</span><span>Comparable sales</span>'
             f'<span class="mini" style="margin-left:auto">{ic("plus")} Add note</span></div><div class="notes"><div>{ic("note")}<span>Added to pipeline<small>Today at 9:14 AM by You</small></span></div>'
             f'<div>{ic("phone")}<span>Called owner, left voicemail<small>Yesterday at 3:27 PM</small></span></div></div></div></div></div></div>')
    return browser(inner, label="EstateHawk property page: photos, AI deal score, owner contact details and notes")


# -------------------------------------------------- small feature mock-ups (features page)
CSS += r"""
.mock{background:#fff;border-radius:16px;box-shadow:0 30px 60px -28px rgba(23,48,31,.35),0 0 0 1px rgba(23,48,31,.07);padding:22px;font-size:14px;color:#2b3a30}
.mock h4{margin:0 0 4px;font:700 17px/1.3 var(--sans);color:var(--ink)}.mock small{color:var(--muted);font-size:12.5px}
.mrow{display:flex;align-items:center;gap:12px;padding:11px 0;border-bottom:1px solid #F0EADF}.mrow:last-child{border:0}
.mrow .i{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;flex:none;background:var(--sand);color:var(--green)}.mrow .i svg{width:18px}
.mrow .r{margin-left:auto;font-weight:600;color:var(--ink);white-space:nowrap}
.tag{display:inline-block;font-size:11.5px;font-weight:600;border-radius:999px;padding:3px 10px;background:var(--mint);color:#1E5B33}.tag.a{background:var(--amber2);color:#7a5210}.tag.g{background:#EEE;color:#555}
.sc{display:grid;grid-template-columns:120px 1fr;gap:16px;align-items:center}.sc img{border-radius:10px;width:120px;height:90px;object-fit:cover}
.bigs{font:800 46px/1 var(--sans);color:#1E5B33;background:#DDEED6;border-radius:12px;padding:10px 16px;display:inline-block}
.bar{height:8px;border-radius:9px;background:#EFE9DD;overflow:hidden;margin-top:6px}.bar i{display:block;height:100%;background:var(--leaf);border-radius:9px}
.letter{background:#FFFEFA;border:1px solid #EEE6D6;border-radius:10px;padding:18px 20px;font:15px/1.65 var(--serif);color:#2b2b25}
.kan{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.kan>div{background:#F6F2EA;border-radius:10px;padding:10px}.kan b{display:block;font-size:12.5px;margin-bottom:8px;color:var(--ink)}
.kc{background:#fff;border-radius:8px;padding:9px;margin-bottom:8px;box-shadow:0 1px 0 rgba(0,0,0,.05);font-size:12px}.kc em{font-style:normal;color:var(--muted);display:block;font-size:11px}
"""


def score_mock():
    rows = [("Years behind on taxes", 86), ("Estimated equity", 92), ("Amount owed", 64), ("Out-of-state owner", 100)]
    bars = "".join(f'<div style="margin-top:10px"><div style="display:flex;justify-content:space-between;font-size:13px"><span>{t}</span><b>{v}</b></div><div class="bar"><i style="width:{v}%"></i></div></div>' for t, v in rows)
    return (f'<div class="mock"><div class="sc"><img src="/site/img/house-main-sm.webp" alt="" width="160" height="120" loading="lazy"><div><small>AI Deal Score</small><br><span class="bigs">92</span></div></div>'
            f'<p style="margin:14px 0 4px;display:flex;gap:8px;align-items:flex-start">{ic("spark").replace("<svg ", "<svg style=width:16px;color:#E2A13A;flex:none;margin-top:3px ")}High equity, 3 years behind and the owner lives out of state.</p>{bars}</div>')


def owner_mock():
    return (f'<div class="mock"><h4>James R. Whitaker</h4><small>Owner of 1287 Maple Ave, Columbus, OH</small>'
            f'<div style="margin-top:10px"><div class="mrow"><span class="i">{ic("phone")}</span><div>(614) 555-0187<br><small>Cell, found on 2 sources</small></div><span class="r"><span class="tag">Verified</span></span></div>'
            f'<div class="mrow"><span class="i">{ic("mail")}</span><div>jwhitaker@email.com<br><small>Email</small></div></div>'
            f'<div class="mrow"><span class="i">{ic("home")}</span><div>4410 Oak Ridge Dr, Tampa, FL 33611<br><small>Mailing address from the tax bill</small></div><span class="r"><span class="tag a">Out of state</span></span></div></div></div>')


def offer_mock():
    return (f'<div class="mock"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><h4>Offer letter</h4><span class="tag">{ic("spark").replace("<svg ", "<svg style=width:12px;display:inline;vertical-align:-1px ")} Written by AI</span></div>'
            f'<div class="letter">Dear James,<br><br>I am a local buyer interested in your property at <b>1287 Maple Ave</b>. I can pay the <b>$12,480</b> in back taxes at closing and offer <b>$105,000</b> cash, closing in 21 days.<br><br>Sincerely,<br>Sarah, Buckeye Home Buyers</div>'
            f'<div style="display:flex;gap:8px;margin-top:14px"><span class="mini g" style="font-size:13px;padding:8px 14px">{ic("send")} Send by email</span><span class="mini" style="font-size:13px;padding:8px 14px">{ic("doc")} Print letter</span></div></div>')


def alerts_mock():
    rows = [("bell", "New high-score deal: 2447 Lindell Rd", "Franklin County, score 91", "now"), ("doc", "38 new delinquent properties", "Hamilton County", "6:12 AM"),
            ("users", "Owner change: 436 E Northwood St", "Sold to a new owner", "yesterday"), ("clock", "Tax sale in 14 days", "Dallas County, 12 of your leads", "Mon")]
    r = "".join(f'<div class="mrow"><span class="i">{ic(i)}</span><div><b style="color:var(--ink);font-size:14px">{t}</b><br><small>{s}</small></div><span class="r" style="font-weight:400;color:var(--muted);font-size:12.5px">{w}</span></div>' for i, t, s, w in rows)
    return f'<div class="mock"><h4>Today\'s alerts</h4>{r}</div>'


def pipeline_mock():
    col = lambda t, cards: f'<div><b>{t}</b>{"".join(f"<div class=kc>{a}<em>{b}</em></div>" for a, b in cards)}</div>'
    return ('<div class="mock"><h4 style="margin-bottom:12px">Pipeline</h4><div class="kan">'
            + col("Contacted", [("1287 Maple Ave", "Called, voicemail"), ("3820 Clifford Ave", "Letter sent")])
            + col("Negotiating", [("2447 Lindell Rd", "Offer $96,500")])
            + col("Closed", [("436 E Northwood St", "Fee $12,000")]) + "</div></div>")

HAWK = '<svg viewBox="40 30 320 372" aria-hidden="true" style="width:150px;opacity:.16"><path fill="#fff" d="M150 96c37-7 79-1 106 22 17 14 29 32 34 53 9 15 10 33 2 50-5-10-14-18-26-20-38-4-86 15-116 48-16 18-28 36-38 52-12-31-14-67-8-99l14-10-16-14 22-8-16-18 24-4-12-18 26-2z"/></svg>'
