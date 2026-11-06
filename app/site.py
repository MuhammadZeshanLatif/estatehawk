"""Marketing website (server-rendered, multi-page, SEO-ready, no frameworks: fast by design).
Pages are plain HTML with inline CSS; numbers (leads, counties) come live from the database."""
import datetime as dt
import html
import json
import os
import re
import time

from . import db, plans
from .site_ui import ILL_DB, ILL_HOUSE, ILL_MAP, alerts_mock, browser, ic, leads_mock, logo, offer_mock, owner_mock, pipeline_mock, property_mock, score_mock
from . import site_ui

SITE_NAME = "EstateHawk"
CONTACT_EMAIL = "support@getestatehawk.com"
CANONICAL = "https://getestatehawk.com"
STATE_NAMES = {"OH": "Ohio", "TX": "Texas", "PA": "Pennsylvania", "FL": "Florida", "IN": "Indiana", "GA": "Georgia", "MI": "Michigan"}
esc = html.escape


def base_url(request=None):
    url = os.environ.get("SITE_URL")
    if url:
        return url.rstrip("/")
    if request is not None:
        host = request.url.hostname or ""
        if host in ("localhost", "127.0.0.1") or host.endswith(".local"):
            return str(request.base_url).rstrip("/")
    return CANONICAL


# ------------------------------------------------------------------ live numbers (cached)
_cache = {"t": 0, "v": None}


def stats():
    if _cache["v"] and time.time() - _cache["t"] < 600:
        return _cache["v"]
    try:
        leads = db.q1("SELECT COUNT(*) n FROM parcels WHERE is_active=1 AND demo=0")["n"]
        rows = db.q("""SELECT c.id, c.name, c.state, c.last_sync,
                       (SELECT COUNT(*) FROM parcels p WHERE p.county_id=c.id AND p.is_active=1) n,
                       (SELECT COUNT(*) FROM parcels p WHERE p.county_id=c.id AND p.is_active=1
                          AND (p.lat IS NOT NULL OR COALESCE(p.street,'') <> '')) good
                       FROM counties c WHERE c.enabled=1 AND c.demo=0 ORDER BY c.state, c.name""")
    except Exception:
        leads, rows = 0, []
    counties = [r for r in rows if r["n"]]
    v = {"leads": leads, "counties": counties, "n_counties": len(counties), "states": sorted({r["state"] for r in counties})}
    _cache.update(t=time.time(), v=v)
    return v


def round_down(n):
    for step in (100000, 10000, 1000, 100, 10):
        if n >= step * 2:
            return f"{n // step * step:,}+"
    return f"{n:,}"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ------------------------------------------------------------------ layout
NAV = [("/features", "Features"), ("/how-it-works", "How it works"), ("/pricing", "Pricing"), ("/counties", "Counties")]

JS = """<script>
(function(){var h=document.querySelector('.hdr');addEventListener('scroll',function(){h.classList.toggle('scrolled',scrollY>8)},{passive:true});
var b=document.querySelector('.menu-btn');if(b)b.onclick=function(){var o=h.classList.toggle('open');b.setAttribute('aria-expanded',o)};
document.querySelectorAll('form[data-api]').forEach(function(f){f.addEventListener('submit',async function(e){e.preventDefault();
var m=f.querySelector('.msg'),btn=f.querySelector('button[type=submit]'),t=btn.innerHTML;m.className='msg';btn.disabled=true;btn.textContent='Please wait...';
var d={};new FormData(f).forEach(function(v,k){d[k]=v});
if(f.dataset.passwordRules){var p=d.password||'',error=p.length<9||p.length>128?'Use 9 to 128 characters.':!/[A-Za-z]/.test(p)||!/[0-9]/.test(p)||!(/[^A-Za-z0-9\\s]/.test(p))?'Add a letter, a number, and a special character.':d.confirm_password!==p?'Passwords do not match.':'';
if(error){m.className='msg err';m.textContent=error;btn.disabled=false;btn.innerHTML=t;return}}
try{var r=await fetch(f.dataset.api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});var j=await r.json().catch(function(){return{}});
if(!r.ok)throw new Error(j.detail||'Something went wrong. Please try again.');
if(f.dataset.next){location.href=f.dataset.next;return}m.className='msg ok';m.textContent=f.dataset.ok||'Thanks!';f.reset();}
catch(err){m.className='msg err';m.textContent=err.message}btn.disabled=false;btn.innerHTML=t;})});
var q=new URLSearchParams(location.search),fm=document.querySelector('form .msg'),cm=document.getElementById('c-msg');if(cm&&q.get('topic')==='county'&&!cm.value){cm.value='Please add this county (name and state): ';}if(q.get('error')&&fm){fm.className='msg err';fm.textContent=q.get('error')}
document.querySelectorAll('a.g-btn[data-signup]').forEach(function(a){a.addEventListener('click',function(e){var s=document.getElementById('s-county'),c=document.getElementById('s-company');
if(!s.value){e.preventDefault();fm.className='msg err';fm.textContent='Choose your first county first, then continue with Google.';s.focus();return}
a.href='/api/auth/google/start?mode=signup&county_id='+encodeURIComponent(s.value)+'&company='+encodeURIComponent(c?c.value:'')})});
document.querySelectorAll('[data-toggle-password]').forEach(function(b){b.addEventListener('click',function(){var i=document.getElementById(b.dataset.togglePassword),show=i.type==='password';i.type=show?'text':'password';b.querySelector('span').textContent=show?'Hide':'Show';b.setAttribute('aria-label',show?'Hide password':'Show password');b.setAttribute('aria-pressed',show?'true':'false')})});})();
</script>"""


def password_fields(prefix):
    eye = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>'
    return (f'<div class="field"><label for="{prefix}-pw">Password</label><div class="pw-wrap"><input id="{prefix}-pw" name="password" type="password" autocomplete="new-password" minlength="9" maxlength="128" required><button type="button" class="pw-toggle" data-toggle-password="{prefix}-pw" aria-label="Show password" aria-pressed="false">{eye}<span>Show</span></button></div>'
            f'<p class="pw-hint">9–128 characters, including a letter, a number and a special character.</p></div>'
            f'<div class="field"><label for="{prefix}-confirm">Confirm password</label><div class="pw-wrap"><input id="{prefix}-confirm" name="confirm_password" type="password" autocomplete="new-password" required><button type="button" class="pw-toggle" data-toggle-password="{prefix}-confirm" aria-label="Show password" aria-pressed="false">{eye}<span>Show</span></button></div></div>')

GOOGLE_G = ('<svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/>'
            '<path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>'
            '<path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/>'
            '<path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>')


def google_button(label, signup=False):
    """'Continue with Google' plus an 'or' line; nothing when Google sign-in is not set up."""
    from . import google_auth
    if not google_auth.configured():
        return ""
    return (f'<a class="g-btn" href="/api/auth/google/start"{" data-signup" if signup else ""}>{GOOGLE_G}<span>{label}</span></a>'
            f'<div class="or"><span>or {"sign up" if signup else "sign in"} with email</span></div>')


def header(path):
    nav = "".join(f'<a href="{h}"{" aria-current=page" if path.startswith(h) else ""}>{t}</a>' for h, t in NAV)
    return (f'<a class="skip" href="#main">Skip to content</a><header class="hdr"><div class="wrap">{logo()}<nav class="nav" aria-label="Main">{nav}</nav>'
            f'<div class="hdr-cta"><a class="signin" href="/login">Sign in</a><a class="btn btn-green btn-sm" href="/signup">Start free trial</a></div>'
            f'<button class="menu-btn" aria-label="Open menu" aria-expanded="false">{ic("menu")}</button></div></header>')


def footer():
    year = dt.date.today().year
    col = lambda t, links: f'<div><h4>{t}</h4><ul>{"".join(f"<li><a href={h!r}>{n}</a></li>" for h, n in links)}</ul></div>'
    return (f'<footer class="ftr"><div class="wrap"><div class="about">{logo()}<p>Official county data. Real estate opportunities.</p></div>'
            + col("Product", [("/features", "Features"), ("/how-it-works", "How it works"), ("/pricing", "Pricing"), ("/counties", "Counties")])
            + col("Resources", [("/guides", "Guides"), ("/faq", "Help center"), ("/counties/ohio", "Ohio tax-delinquent lists"), ("/counties/texas", "Texas tax sales")])
            + col("Company", [("/about", "About"), ("/contact", "Contact"), ("/terms", "Terms of service"), ("/privacy", "Privacy policy"), ("/refund-policy", "Refund policy")])
            + f'<div class="legal"><p>Powered by official county treasurer records.</p><p style="margin-top:4px">&copy; {year} EstateHawk. All rights reserved.</p></div></div></footer>')


def cta_band(title="Start finding off-market deals today.", sub="Get tax-delinquent property leads, updated nightly from official county records."):
    return (f'<section class="band" aria-label="Start your free trial"><div class="mark">{site_ui.HAWK}</div>'
            f'<div class="wrap"><div class="txt"><h2>{title}</h2><p>{sub}</p></div><a class="btn btn-cream" href="/signup">Start your free trial {ic("arrow")}</a></div></section>')


def page(request, path, title, desc, body, schema=None, js=False, noindex=False, status=200):
    url = base_url(request) + path
    ld = "".join(f'<script type="application/ld+json">{json.dumps(s, separators=(",", ":"))}</script>' for s in (schema or []))
    org = {"@context": "https://schema.org", "@type": "Organization", "name": SITE_NAME, "url": base_url(request), "logo": base_url(request) + "/site/logo-mark.svg",
           "email": CONTACT_EMAIL}
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{url}">'
            f'{"<meta name=robots content=noindex>" if noindex else ""}'
            f'<meta property="og:type" content="website"><meta property="og:site_name" content="{SITE_NAME}"><meta property="og:title" content="{esc(title)}">'
            f'<meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{base_url(request)}/site/og.jpg">'
            f'<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#1A4A30">'
            f'<link rel="icon" href="/site/logo-mark.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/site/icon-180.png">'
            f'<link rel="preload" href="/site/fonts/fraunces.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="/site/fonts/inter.woff2" as="font" type="font/woff2" crossorigin>'
            f'<style>{site_ui.CSS}</style><link rel="stylesheet" href="/static/chat-widget.css"><script type="application/ld+json">{json.dumps(org, separators=(",", ":"))}</script>{ld}</head>'
            f'<body>{header(path)}<main id="main">{body}</main>{footer()}{JS}<script src="/static/chat-widget.js" defer></script></body></html>')


def crumbs(request, items):
    """Breadcrumb trail + its schema. items: [(path, name)], last one = current page."""
    trail = " / ".join(f'<a href="{p}">{esc(n)}</a>' if i < len(items) - 1 else esc(n) for i, (p, n) in enumerate([("/", "Home")] + items))
    schema = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": base_url(request) + p} for i, (p, n) in enumerate([("/", "Home")] + items)]}
    return f'<div class="crumbs">{trail}</div>', schema


# ------------------------------------------------------------------ shared blocks
def strip_block():
    s = stats()
    return (f'<section class="wrap" aria-label="EstateHawk in numbers"><div class="strip"><h2>Data from official county treasurer records</h2>'
            f'<div class="stat">{ic("users")}<div><b>{round_down(s["leads"]) if s["leads"] else "100,000+"}</b><span>leads</span></div></div>'
            f'<div class="stat">{ic("pin")}<div><b>{round_down(s["n_counties"]) if s["n_counties"] else "80+"}</b><span>counties</span></div></div>'
            f'<div class="stat">{ic("moon")}<div><span style="font-size:16px;color:var(--ink)">updated<br>nightly</span></div></div></div></section>')


STEPS = [(ILL_MAP, "Choose counties", "Select the counties you want to invest in, from our growing nationwide coverage."),
         (ILL_DB, "EstateHawk scans nightly", "We pull tax-delinquent and off-market records from official county data every night."),
         (ILL_HOUSE, "Review and reach out", "Get AI-scored leads, owner contact info, and the tools to make an offer before anyone else.")]


def steps_block(head=True):
    arrow = f'<div class="arrow" aria-hidden="true">{ic("arrow")}</div>'
    cards = arrow.join(f'<div class="step">{ill}<div><h3><span class="n">{i + 1}</span>{t}</h3><p>{d}</p></div></div>' for i, (ill, t, d) in enumerate(STEPS))
    h = ('<div class="sec-head"><h2>How <span class="ital">EstateHawk</span> works</h2><p>A simple, powerful process to find and contact motivated property owners.</p></div>' if head else "")
    return f'<section class="sec-tight" id="how"><div class="wrap">{h}<div class="steps">{cards}</div></div></section>'


FEATURES = [("bars", "Deal score", "AI analyzes equity, taxes, ownership, and market data to surface the best opportunities.", "deal-score"),
            ("user", "Owner contact finder", "Access owner contact information, including mailing address, phone, and email (when available).", "owner-contacts"),
            ("pin", "Map view", "See all your leads on an interactive map to quickly spot opportunities in the areas you want.", "map-view"),
            ("doc", "AI offer letters", "Generate personalized, ready-to-send offer letters in seconds.", "ai-offers"),
            ("bell", "Alerts", "Get notified when new high-score leads are found in your selected counties.", "alerts"),
            ("team", "Team pipeline", "Work with your team, assign leads, track outreach, and close deals together.", "team-pipeline")]


def features_block(head=True, link=True):
    cards = "".join(f'<{"a" if link else "div"} class="feat"{f" href=/features#{a}" if link else ""}><span class="ico">{ic(i)}</span><div><h3>{t}</h3><p>{d}</p></div></{"a" if link else "div"}>'
                    for i, t, d, a in FEATURES)
    h = ('<div class="sec-head"><h2>Powerful tools for off-market real estate</h2><p>Everything you need to find, evaluate, and acquire tax-delinquent properties.</p></div>' if head else "")
    return f'<section class="sec-tight"><div class="wrap">{h}<div class="grid3">{cards}</div></div></section>'


def plan_cards():
    P = plans.PLANS
    def cnt(n):
        return "All counties" if n is None else f"{n} {'county' if n == 1 else 'counties'}"
    rows = {
        "starter": [cnt(P["starter"]["counties"]), "AI-scored property leads", "Owner contact information", "Map search and filtering", "CSV export"],
        "pro": [cnt(P["pro"]["counties"]), "Everything in Starter", "AI offer letters", "Alerts and saved searches", f"Team collaboration (up to {P['pro']['users']} users)"],
        "agency": [cnt(P["agency"]["counties"]), "Everything in Pro", "Advanced team pipeline", f"Up to {P['agency']['users']} team members", "Priority support"],
    }
    out = ""
    for key in ("starter", "pro", "agency"):
        pro = key == "pro"
        li = "".join(f"<li>{ic('check')}{x}</li>" for x in rows[key])
        out += (f'<div class="plan{" pro" if pro else ""}">{"<span class=badge>RECOMMENDED</span>" if pro else ""}<h3>{P[key]["label"]}</h3>'
                f'<div class="price"><b>${P[key]["price"]}</b><span>per month</span></div><ul>{li}</ul>'
                f'<a class="btn {"btn-cream" if pro else "btn-line"} btn-block" href="/signup?plan={key}">Start free trial</a></div>')
    return out


def pricing_block(head_tag="h2"):
    return (f'<section class="sec" id="pricing"><div class="wrap pricing"><div class="pintro"><{head_tag}>Simple, transparent pricing</{head_tag}><span class="uline"></span>'
            f'<p>Choose the plan that fits your investment goals. All plans include a 14-day free trial.</p></div>{plan_cards()}</div></section>')


def faqs():
    s = stats()
    n = s["n_counties"] or 80
    return [
        ("Which counties do you cover?", f"We currently cover {n} counties across {len(s['states']) or 3} states, pulled from official county treasurer and tax-sale records, and we add more regularly. See the full list on the Counties page."),
        ("How fresh is the data?", "Every county list is downloaded again every night. New delinquent properties, owner changes and paid-off taxes show up in your account the next morning."),
        ("Is there a free trial?", "Yes. Every plan starts with a 14-day free trial with one county. No credit card is needed to start."),
        ("Can I collaborate with my team?", "Yes. Pro and Agency plans let you invite team members, assign leads and track every call, letter and offer in a shared pipeline."),
        ("Where does the data come from?", "From public records published by county treasurers, auditors and their tax-sale attorneys. We collect, clean, score and map it so you do not have to."),
        ("What is a deal score?", "A 0 to 100 score that weighs how many years the taxes are behind, the estimated equity, the amount owed, out-of-state ownership and vacancy signals. Higher means a more motivated seller and a better margin."),
        ("Can I cancel anytime?", "Yes. Plans are month to month. You can cancel or change your plan whenever you want, and your plan runs until the end of the month you paid for. Payments are not refunded, which is why every plan starts with a 14-day free trial."),
    ]


def faq_block(items=None, side=True):
    items = items or faqs()[:4]
    det = "".join(f'<details{" open" if i == 0 else ""}><summary>{q}{ic("chev")}</summary><p>{a}</p></details>' for i, (q, a) in enumerate(items))
    left = ('<div><h2>Frequently<br>asked questions</h2><span class="uline"></span><p style="margin-top:16px">Have another question?<br>'
            '<a href="/contact" style="color:var(--leaf);font-weight:600">Contact our team</a>, we are here to help.</p></div>' if side else "")
    return f'<section class="sec-tight" style="padding-bottom:44px"><div class="wrap faqgrid faq">{left}<div>{det}</div></div></section>'


def faq_schema(items):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}


def app_schema(request):
    P = plans.PLANS
    return {"@context": "https://schema.org", "@type": "SoftwareApplication", "name": SITE_NAME, "applicationCategory": "BusinessApplication",
            "operatingSystem": "Web", "url": base_url(request),
            "description": "Tax-delinquent property leads from official county records, updated nightly and scored by AI, for real estate investors and wholesalers.",
            "offers": [{"@type": "Offer", "name": P[k]["label"], "price": str(P[k]["price"]), "priceCurrency": "USD"} for k in ("starter", "pro", "agency")]}


# ------------------------------------------------------------------ pages
def home(request):
    hero = (f'<section class="hero"><div class="sun" aria-hidden="true"></div><div class="wrap"><div>'
            f'<h1>Find motivated sellers before they hit the <span class="swoosh">market.</span></h1>'
            f'<p class="lead">Tax-delinquent property leads from official county records, updated every night, scored by AI.</p>'
            f'<div class="cta-row"><a class="btn btn-green" href="/signup">Start 14-day free trial {ic("arrow")}</a>'
            f'<a class="btn btn-line" href="/how-it-works">{ic("play")} See how it works</a></div>'
            f'<div class="ticks"><span>{ic("card")}No credit card required</span><span>{ic("moon")}Updated nightly</span><span>{ic("layers")}Official county data</span></div>'
            f'</div><div>{leads_mock()}</div></div></section>')
    body = (hero + strip_block() + '<div style="height:14px"></div>' + steps_block() + features_block()
            + f'<section class="sec-tight"><div class="wrap shot">{property_mock()}</div></section>' + pricing_block() + faq_block() + cta_band())
    return page(request, "/", "EstateHawk | Tax-Delinquent Property Leads for Real Estate Investors",
                "Find motivated sellers before they hit the market. Tax-delinquent property leads from official county records, updated nightly, scored by AI. Start a 14-day free trial.",
                body, [app_schema(request), faq_schema(faqs()[:4])])


DEEP = [
    ("deal-score", "Deal score", "Know which deals to chase first", "Every lead gets a 0 to 100 score so your team spends the day on the owners most likely to sell, with room for profit.",
     ["Years behind on taxes and total amount owed", "Estimated equity from county appraised values", "Out-of-state and absentee owners flagged", "One-line plain-English reason for every score"]),
    ("owner-contacts", "Owner contact finder", "Reach the owner, not a dead end", "We pull the mailing address from county records and look up phone numbers and emails, so you can call, text or mail the same day.",
     ["Mailing address straight from the tax bill", "Phone and email lookups (when available)", "Duplicates merged into one clean contact", "Private owners clearly marked"]),
    ("map-view", "Map view", "See the whole county at a glance", "Every property is placed on the map. Filter by score, taxes owed, equity or type and the list follows the map as you move.",
     ["Filter by score, equity, years behind and owed", "List updates as you zoom and drag", "Street view and satellite in one click", "Save searches for next time"]),
    ("ai-offers", "AI offer letters", "Send a professional offer in seconds", "Draft a personal offer letter from the property data and your terms, then send it by email or print a batch for the mail.",
     ["Offer price suggested from value and debt", "Your terms, closing days and earnest money", "Batch letters for a whole list", "Edit everything before you send"]),
    ("alerts", "Alerts", "Be first when a deal appears", "When a new high-score property lands in your counties, an owner changes or an auction date gets close, you hear about it.",
     ["New delinquent properties every morning", "Owner change and tax-paid alerts", "Auction and tax-sale date reminders", "Email, Slack, SMS or WhatsApp"]),
    ("team-pipeline", "Team pipeline", "Run your acquisitions like a team", "Move deals from new lead to closed, assign them to teammates, keep every call and note in one place and track your fees.",
     ["Drag-and-drop stages from new to closed", "Notes, tasks and follow-up reminders", "Assignment fees tracked in reports", "Roles for owners and team members"]),
]


def features(request):
    bc, bs = crumbs(request, [("/features", "Features")])
    rows = ""
    for i, (a, label, t, d, pts) in enumerate(DEEP):
        visual = {"deal-score": score_mock, "owner-contacts": owner_mock, "map-view": leads_mock, "ai-offers": offer_mock,
                  "alerts": alerts_mock, "team-pipeline": pipeline_mock}[a]()
        li = "".join(f"<li>{ic('check')}{p}</li>" for p in pts)
        rows += (f'<section class="sec-tight" id="{a}"><div class="wrap row2{" rev" if i % 2 else ""}"><div><span class="eyebrow">{label}</span><h2>{t}</h2><p>{d}</p>'
                 f'<ul class="list">{li}</ul></div><div>{visual}</div></div></section>')
    body = (f'<section class="phero"><div class="wrap">{bc}<span class="eyebrow">Features</span><h1>Everything you need to win <span class="swoosh">off-market</span> deals</h1>'
            f'<p>From the county record to a signed contract: find, score, contact and close, in one tool built for wholesalers and investors.</p></div></section>'
            + features_block(head=False, link=True) + rows + cta_band())
    return page(request, "/features", "Features | EstateHawk Tax-Delinquent Lead Software",
                "Deal scores, owner contact finder, map view, AI offer letters, alerts and a team pipeline: every tool to find and close tax-delinquent property deals.", body, [bs])


def how(request):
    bc, bs = crumbs(request, [("/how-it-works", "How it works")])
    detail = [("Pick your counties", "Choose the counties where you buy. Start with one on the free trial and add more as you grow. Every county comes from its official treasurer, auditor or tax-sale list."),
              ("We download and clean the list every night", "Our system reads each county list overnight, removes duplicates, fixes addresses, places every property on the map and notes what changed since yesterday."),
              ("Every property gets a deal score", "We weigh years behind, amount owed, estimated equity, absentee ownership and vacancy into one score, with a short reason you can read in a second."),
              ("We find the owner", "Mailing address from the tax bill, plus phone and email lookups where available. Private owners are marked so you do not waste time."),
              ("You reach out first", "Call, text, email or mail a letter written by AI. Track every touch in your pipeline and close the deal before it goes to auction.")]
    tl = "".join(f'<div class="card" style="display:flex;gap:18px"><span class="step"><span class="n" style="margin:0">{i + 1}</span></span><div><h3 style="font-size:21px;margin-bottom:6px">{t}</h3><p>{d}</p></div></div>'
                 .replace('<span class="step">', '<span>') for i, (t, d) in enumerate(detail))
    body = (f'<section class="phero"><div class="wrap">{bc}<span class="eyebrow">How it works</span><h1>From county record to <span class="swoosh">signed deal</span></h1>'
            f'<p>EstateHawk does the boring part every night, so every morning you start with a fresh list of motivated sellers.</p></div></section>'
            + steps_block(head=False)
            + f'<section class="sec"><div class="wrap row2"><div style="display:grid;gap:14px">{tl}</div><div>{leads_mock()}<div style="height:18px"></div>{property_mock()}</div></div></section>'
            + faq_block(faqs()[:5]) + cta_band())
    howto = {"@context": "https://schema.org", "@type": "HowTo", "name": "How to find tax-delinquent property leads with EstateHawk",
             "step": [{"@type": "HowToStep", "position": i + 1, "name": t, "text": d} for i, (t, d) in enumerate(detail)]}
    return page(request, "/how-it-works", "How It Works | EstateHawk", "See how EstateHawk turns official county tax-delinquent records into scored, mapped leads with owner contacts every night.",
                body, [bs, howto, faq_schema(faqs()[:5])])


def pricing(request):
    bc, bs = crumbs(request, [("/pricing", "Pricing")])
    P = plans.PLANS
    yes, no = ic("check"), '<span style="color:#b9b2a4">&mdash;</span>'
    cnt = lambda n: "All" if n is None else str(n)
    table = [("Counties", *(cnt(P[k]["counties"]) for k in ("starter", "pro", "agency"))), ("Team members", *(str(P[k]["users"]) for k in ("starter", "pro", "agency"))),
             ("AI deal scores", yes, yes, yes), ("Map, filters and saved searches", yes, yes, yes), ("Owner contact finder", yes, yes, yes),
             ("CSV export", yes, yes, yes), ("AI offer letters", no, yes, yes), ("Alerts (email, Slack, SMS)", no, yes, yes), ("Team pipeline and roles", no, yes, yes), ("Priority support", no, no, yes)]
    rows = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>" for r in table)
    cmp = (f'<section class="sec-tight"><div class="wrap"><div class="sec-head"><h2>Compare plans</h2></div><div style="overflow-x:auto"><table class="cmp"><thead><tr><th>Feature</th>'
           f'<th>Starter</th><th>Pro</th><th>Agency</th></tr></thead><tbody>{rows}</tbody></table></div></div></section>')
    items = [f for f in faqs() if f[0] in ("Is there a free trial?", "Can I cancel anytime?", "Which counties do you cover?", "Can I collaborate with my team?")]
    body = (f'<section class="phero" style="padding-bottom:0"><div class="wrap">{bc}</div></section>' + pricing_block("h1") + cmp + faq_block(items) + cta_band())
    return page(request, "/pricing", "Pricing | EstateHawk Plans from $49/month", "Simple, transparent pricing for tax-delinquent property leads. Starter $49, Pro $99, Agency $249 per month. Every plan starts with a 14-day free trial.",
                body, [bs, app_schema(request), faq_schema(items)])


def counties(request):
    bc, bs = crumbs(request, [("/counties", "Counties")])
    s = stats()
    by = {}
    for c in s["counties"]:
        by.setdefault(c["state"], []).append(c)
    cards = "".join(f'<a class="state" href="/counties/{slug(STATE_NAMES.get(st, st))}"><h3>{STATE_NAMES.get(st, st)}</h3><p>{len(cs)} counties, {sum(c["n"] for c in cs):,} active leads</p>'
                    f'<p style="color:var(--leaf);font-weight:600;margin-top:12px">View counties {ic("arrow").replace("<svg ", "<svg style=display:inline;width:16px;vertical-align:-3px ")}</p></a>' for st, cs in by.items())
    body = (f'<section class="phero"><div class="wrap">{bc}<span class="eyebrow">Coverage</span><h1>{s["n_counties"]} counties and <span class="swoosh">growing</span></h1>'
            f'<p>Tax-delinquent and tax-sale property lists from official county sources, refreshed every night. {s["leads"]:,} active leads right now.</p></div></section>'
            f'<section class="sec-tight"><div class="wrap"><div class="states">{cards}</div>'
            f'<p style="text-align:center;margin-top:28px">Need a county we do not cover yet? <a href="/contact?topic=county" style="color:var(--leaf);font-weight:600">Request a county</a> and we will check its records.</p></div></section>'
            + cta_band())
    return page(request, "/counties", f"Coverage: {s['n_counties']} Counties | EstateHawk", "See every county EstateHawk covers: tax-delinquent and tax-sale property lists from official records in Ohio, Texas and more, updated nightly.", body, [bs])


def county_state(request, state_slug):
    s = stats()
    code = next((k for k, v in STATE_NAMES.items() if slug(v) == state_slug), None)
    cs = [c for c in s["counties"] if c["state"] == code]
    if not cs:
        return None
    name = STATE_NAMES[code]
    bc, bs = crumbs(request, [("/counties", "Counties"), (f"/counties/{state_slug}", name)])
    total = sum(c["n"] for c in cs)
    def cov(c):
        pct = round(100 * (c.get("good") or 0) / c["n"]) if c["n"] else 0
        try:
            when = dt.date.fromisoformat((c.get("last_sync") or "")[:10]).strftime("%b %-d")
        except ValueError:
            when = ""
        return (f'<span>{c["n"]:,} leads</span><small style="flex-basis:100%;font-size:12.5px;color:var(--muted);margin-top:4px">'
                f'{"Full" if pct >= 90 else "Good" if pct >= 60 else "Limited"} data, {pct}% with address'
                f'{", updated " + when if when else ""}</small>')
    grid = "".join(f'<div class="county" style="flex-wrap:wrap">{"<b>" + esc(c["name"]) + "</b>"}{cov(c)}</div>' for c in sorted(cs, key=lambda c: -c["n"]))
    kind = "tax sale" if code == "TX" else "tax-delinquent"
    intro = (f"Texas counties sell tax-defaulted homes at constable and sheriff sales. EstateHawk tracks every listed property across {len(cs)} Texas counties, with value, minimum bid and sale status, so you can reach owners before the auction."
             if code == "TX" else f"{name} counties publish who is behind on property taxes. EstateHawk downloads those lists every night across {len(cs)} {name} counties, scores every property and finds the owner so you can make an offer first.")
    body = (f'<section class="phero"><div class="wrap">{bc}<span class="eyebrow">{name}</span><h1>{name} {kind} property <span class="swoosh">list</span></h1>'
            f'<p>{intro}</p></div></section><section class="sec-tight"><div class="wrap"><div class="strip" style="margin:0 0 26px"><h2>{name} right now</h2>'
            f'<div class="stat">{ic("users")}<div><b>{total:,}</b><span>active leads</span></div></div><div class="stat">{ic("pin")}<div><b>{len(cs)}</b><span>counties</span></div></div>'
            f'<div class="stat">{ic("moon")}<div><span style="font-size:16px;color:var(--ink)">updated<br>nightly</span></div></div></div><div class="cgrid">{grid}</div><p style="margin-top:18px;font-size:14px;color:var(--muted)">"Full" means at least 9 in 10 leads come with a street address or map location from county records. <a href="/contact?topic=county" style="color:var(--leaf);font-weight:600">Request another county</a>.</p></div></section>'
            + cta_band(f"Get the {name} list today.", f"Start a 14-day free trial and see every {kind} property in your {name} county."))
    return page(request, f"/counties/{state_slug}", f"{name} Tax Delinquent Property List ({total:,} Leads) | EstateHawk",
                f"Daily {name} {kind} property list from {len(cs)} counties: {total:,} active leads with deal scores, maps and owner contacts. Start free for 14 days.", body, [bs])


GUIDES = [
    ("what-is-a-tax-delinquent-property", "What is a tax-delinquent property (and why investors want them)?",
     "A plain-English guide to tax-delinquent properties, why their owners are often motivated to sell, and how investors use public county lists to find them.",
     """<p>A property becomes <b>tax delinquent</b> when the owner misses a property tax payment by the county's due date. In Ohio and most other states, the county adds penalties and interest, and after a set period it publishes the property on a <b>delinquent tax list</b>.</p>
<h2>Why tax-delinquent owners are often motivated sellers</h2><p>An owner who stops paying property tax is usually under some kind of pressure: an inherited house nobody lives in, a landlord who is tired, a job loss, or an owner who lives out of state. If the debt is not paid, the county can eventually foreclose and sell the property at a tax sale. Many owners would rather sell quietly for a fair price than lose everything at auction.</p>
<h2>Where the lists come from</h2><p>The lists are public records. County treasurers and auditors publish them online, in newspapers or as downloadable files, and in Texas the tax attorneys publish upcoming tax sales. The hard part is that every county uses a different format and the lists change every day.</p>
<h2>How investors use them</h2><ul><li>Filter for owners several years behind with high equity.</li><li>Look for absentee or out-of-state owners.</li><li>Reach out with a respectful, fair cash offer before the tax sale.</li></ul>
<p>EstateHawk collects these lists every night, scores every property and finds the owner, so you can spend your time talking to sellers instead of cleaning spreadsheets.</p>"""),
    ("how-to-find-tax-delinquent-properties", "How to find tax-delinquent properties in your county",
     "Step-by-step: where counties publish delinquent tax lists, what to look for in each record, and how to turn the list into real conversations with owners.",
     """<p>Finding tax-delinquent properties takes three things: the official list, a way to judge which properties are worth your time, and a way to reach the owner.</p>
<h2>1. Get the official list</h2><p>Start at your county treasurer or auditor website and look for "delinquent tax list", "forfeited land" or "tax sale". Some counties offer a searchable site, others a PDF or a spreadsheet, and some only publish in the local newspaper once a year.</p>
<h2>2. Clean and score the records</h2><p>Each row usually has the parcel number, owner name, property address and amount owed. Add the appraised value to estimate equity, check how many years are owed, and compare the mailing address with the property address to spot absentee owners.</p>
<h2>3. Find and contact the owner</h2><p>The mailing address on the tax bill is your first contact. Phone and email lookups help you reach owners faster. Keep notes on every touch so nobody gets called twice in a day.</p>
<h2>4. Repeat every day</h2><p>Lists change constantly: new properties are added, others are paid off. The investors who win are the ones who see the change first. That is exactly what EstateHawk automates for you.</p>"""),
    ("how-to-make-an-offer-on-a-tax-delinquent-property", "How to make an offer on a tax-delinquent property",
     "How to price and present a fair cash offer to an owner who is behind on property taxes, with a simple formula and a respectful approach that gets replies.",
     """<p>Owners behind on taxes hear from many buyers. A clear, respectful offer stands out.</p>
<h2>A simple pricing formula</h2><p>Start from the estimated value, apply your discount for repairs and profit (many wholesalers use 60 to 70 percent), then subtract the taxes owed, because you will pay those at closing. Example: value $180,000 x 65% = $117,000, minus $12,000 in back taxes = an offer near $105,000.</p>
<h2>What to say</h2><ul><li>Introduce yourself and how you found the property (public county records).</li><li>Explain that you can pay the back taxes at closing and close fast.</li><li>Give a clear number, your closing timeline and the earnest money.</li><li>Make it easy to reply: phone, text or email.</li></ul>
<h2>Follow up</h2><p>Most deals come from the second to fifth contact. Track every letter and call, and follow up when the auction date gets close.</p><p>EstateHawk suggests an offer price for every lead and writes the letter for you with AI.</p>"""),
]


def guides(request):
    bc, bs = crumbs(request, [("/guides", "Guides")])
    cards = "".join(f'<a class="card" href="/guides/{s}" style="display:block"><span class="eyebrow">Guide</span><h3 style="font-size:23px">{t}</h3><p style="margin-top:10px">{d}</p>'
                    f'<p style="color:var(--leaf);font-weight:600;margin-top:14px">Read the guide</p></a>' for s, t, d, _ in GUIDES)
    body = (f'<section class="phero"><div class="wrap">{bc}<span class="eyebrow">Guides</span><h1>Learn tax-delinquent <span class="swoosh">investing</span></h1>'
            f'<p>Practical guides for wholesalers and investors: finding motivated sellers in public county records and turning them into deals.</p></div></section>'
            f'<section class="sec-tight"><div class="wrap grid3">{cards}</div></section>' + cta_band())
    return page(request, "/guides", "Guides: Tax-Delinquent Real Estate Investing | EstateHawk", "Free guides on finding tax-delinquent properties, motivated sellers and how to make offers, from the EstateHawk team.", body, [bs])


def guide(request, s):
    g = next((x for x in GUIDES if x[0] == s), None)
    if not g:
        return None
    _, t, d, content = g
    bc, bs = crumbs(request, [("/guides", "Guides"), (f"/guides/{s}", t)])
    art = {"@context": "https://schema.org", "@type": "Article", "headline": t, "description": d, "author": {"@type": "Organization", "name": SITE_NAME},
           "publisher": {"@type": "Organization", "name": SITE_NAME, "logo": {"@type": "ImageObject", "url": base_url(request) + "/site/logo-mark.svg"}},
           "mainEntityOfPage": base_url(request) + f"/guides/{s}", "datePublished": "2026-11-04"}
    body = (f'<article><section class="phero" style="text-align:left"><div class="wrap prose">{bc}<span class="eyebrow">Guide</span><h1 style="font-size:clamp(34px,4.4vw,52px)">{t}</h1>'
            f'<p style="margin:16px 0 0;font-size:19px">{d}</p></div></section><section class="sec-tight"><div class="wrap prose">{content}</div></section></article>' + cta_band())
    return page(request, f"/guides/{s}", f"{t} | EstateHawk", d, body, [bs, art])


def about(request):
    bc, bs = crumbs(request, [("/about", "About")])
    body = (f'<section class="phero"><div class="wrap">{bc}<span class="eyebrow">About</span><h1>Public records, made <span class="swoosh">useful</span></h1>'
            f'<p>EstateHawk turns scattered county tax records into a clean, scored list of motivated sellers, every single night.</p></div></section>'
            f'<section class="sec-tight"><div class="wrap row2"><div><h2>Why we built EstateHawk</h2><p>Every county publishes who is behind on property taxes, but each one does it differently: '
            f'websites, spreadsheets, PDFs, newspaper notices. Investors spent hours copying lists that were out of date by the next day.</p>'
            f'<p>We built a system that reads those official sources every night, cleans and maps every property, scores it and finds the owner. '
            f'You open EstateHawk in the morning and start making calls.</p><ul class="list"><li>{ic("check")}Only official public records</li><li>{ic("check")}Updated every night</li>'
            f'<li>{ic("check")}Built for wholesalers, investors and their teams</li></ul></div><div>{leads_mock()}</div></div></section>' + strip_block() + '<div style="height:60px"></div>' + cta_band())
    return page(request, "/about", "About EstateHawk", "EstateHawk turns official county tax-delinquent records into scored, mapped leads with owner contacts for real estate investors.", body, [bs])


def contact(request):
    bc, bs = crumbs(request, [("/contact", "Contact")])
    body = (f'<section class="phero" style="padding-bottom:10px"><div class="wrap">{bc}<span class="eyebrow">Contact</span><h1>Talk to the <span class="swoosh">team</span></h1>'
            f'<p>Questions about coverage, a county you need, or a team plan? Send us a message and we will reply within one business day.</p></div></section>'
            f'<section class="sec-tight"><div class="wrap"><form class="form" data-api="/api/public/contact" data-ok="Thanks! We got your message and will reply soon." novalidate>'
            f'<div class="msg" role="status"></div><div class="field"><label for="c-name">Name</label><input id="c-name" name="name" autocomplete="name" required></div>'
            f'<div class="field"><label for="c-email">Email</label><input id="c-email" name="email" type="email" autocomplete="email" required></div>'
            f'<div class="field"><label for="c-msg">Message</label><textarea id="c-msg" name="message" required></textarea></div>'
            f'<input class="hp" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">'
            f'<button class="btn btn-green btn-block" type="submit">Send message {ic("send")}</button>'
            f'<p class="alt">Or email <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p></form></div></section>')
    return page(request, "/contact", "Contact EstateHawk", "Get in touch with the EstateHawk team about county coverage, team plans or anything else.", body, [bs])


def faq_page(request):
    bc, bs = crumbs(request, [("/faq", "Help center")])
    items = faqs()
    body = (f'<section class="phero"><div class="wrap">{bc}<span class="eyebrow">Help center</span><h1>Questions, <span class="swoosh">answered</span></h1>'
            f'<p>Everything about our data, pricing and how EstateHawk works.</p></div></section>' + faq_block(items, side=True) + cta_band())
    return page(request, "/faq", "Help Center & FAQ | EstateHawk", "Answers about EstateHawk coverage, data freshness, the free trial, team plans and deal scores.", body, [bs, faq_schema(items)])


def legal(request, kind):
    if kind == "privacy":
        t, d = "Privacy policy", "How EstateHawk collects, uses and protects your information."
        txt = """<p>EstateHawk ("we") provides software that organizes public property tax records. This policy explains what we collect about our users.</p>
<h2>What we collect</h2><ul><li>Account details you give us: name, email, company and password (stored hashed).</li><li>What you do in the app, such as notes, pipeline stages and searches, so the product works.</li><li>Basic technical logs (IP address, browser) for security.</li></ul>
<h2>Property data</h2><p>Property and owner information in EstateHawk comes from public records published by county governments and from public contact lookups. You are responsible for using it lawfully, including do-not-call and anti-spam rules.</p>
<h2>How we use your information</h2><p>To run your account, send alerts you ask for, provide support and keep the service secure. We do not sell your personal information.</p>
<h2>Your choices</h2><p>You can update or delete your account at any time by contacting us at """ + CONTACT_EMAIL + """.</p>"""
    elif kind == "refund":
        t, d = "Refund policy", "How cancellations and refunds work for EstateHawk plans."
        txt = """<p>Every plan starts with a 14-day free trial, so you can try EstateHawk and see the data for your county before you pay anything.</p>
<h2>No refunds, cancel anytime</h2><p>Because paid plans give instant access to lead data, payments are not refunded. You can cancel at any time from Manage billing in the app or by emailing us. Your plan stays active until the end of the month you paid for, and you are not charged again.</p>
<h2>Billing mistakes</h2><p>If you were charged by mistake, for example twice for the same month, tell us within 30 days and we refund the extra charge in full.</p>
<h2>How payments work</h2><p>Payments are processed by our payment partner Creem, who acts as the merchant of record and sends your receipts.</p>
<h2>Contact</h2><p>Email """ + CONTACT_EMAIL + """ with your account email and we will reply within one business day.</p>"""
    else:
        t, d = "Terms of service", "The terms for using EstateHawk."
        txt = """<p>By creating an account you agree to these terms.</p><h2>The service</h2><p>EstateHawk organizes public property tax records, scores them and helps you contact owners. Data comes from official sources but can contain errors or be out of date; always verify before you act.</p>
<h2>Your account</h2><p>Keep your login safe. Plans are billed monthly and you may cancel anytime. Free trials last 14 days.</p><h2>Payments</h2><p>Payments are processed by our payment partner Creem, the merchant of record, who handles card payments, receipts and sales tax. See our <a href="/refund-policy">refund policy</a>.</p>
<h2>Acceptable use</h2><p>Use the data lawfully. Follow do-not-call, telemarketing, anti-spam and fair-housing laws. Do not resell raw data or scrape the service.</p>
<p><b>AI features.</b> EstateHawk uses AI to draft offer letters and explain deal scores. You may use these features only for real estate outreach and research. You must not use them, or ask them, to create sexually explicit, pornographic, adult or other NSFW content; content that harasses, threatens, discriminates or deceives; or anything unlawful. We may block such requests, remove the content and suspend accounts that break this rule. You are responsible for reviewing any AI draft before you send it.</p>
<h2>Liability</h2><p>The service is provided as is. We are not liable for investment decisions you make with it.</p><h2>Contact</h2><p>Questions: """ + CONTACT_EMAIL + """</p>"""
    slug = "refund-policy" if kind == "refund" else kind
    bc, bs = crumbs(request, [(f"/{slug}", t)])
    body = (f'<section class="phero" style="text-align:left"><div class="wrap prose">{bc}<h1 style="font-size:46px">{t}</h1><p style="margin:12px 0 0">Last updated November 2026</p></div></section>'
            f'<section class="sec-tight"><div class="wrap prose">{txt}</div></section>')
    return page(request, f"/{slug}", f"{t} | EstateHawk", d, body, [bs])


def login(request):
    eye = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>'
    body = (f'<section class="sec" style="padding-top:56px"><div class="wrap"><form class="form" data-api="/api/auth/login" data-next="/app" novalidate>'
            f'<h1>Welcome back</h1><p class="sub">Sign in to your EstateHawk account.</p><div class="msg" role="alert"></div>'
            f'{google_button("Continue with Google")}'
            f'<div class="field"><label for="l-email">Email</label><input id="l-email" name="email" type="email" autocomplete="email" required></div>'
            f'<div class="field"><label for="l-pw">Password</label><div class="pw-wrap"><input id="l-pw" name="password" type="password" autocomplete="current-password" required><button type="button" class="pw-toggle" data-toggle-password="l-pw" aria-label="Show password" aria-pressed="false">{eye}<span>Show</span></button></div></div>'
            f'<p class="alt" style="margin:-6px 0 14px;text-align:right"><a href="/forgot-password">Forgot password?</a></p>'
            f'<button class="btn btn-green btn-block" type="submit">Sign in {ic("arrow")}</button>'
            f'<p class="alt">New to EstateHawk? <a href="/signup">Start a free trial</a></p></form></div></section>')
    return page(request, "/login", "Sign in | EstateHawk", "Sign in to your EstateHawk account.", body, noindex=True)


def check_email(request, email):
    body = (f'<section class="sec" style="padding-top:56px"><div class="wrap"><div class="form" style="text-align:center">'
            f'<div style="font-size:36px;margin-bottom:8px">✉</div><h1>Check your email</h1>'
            f'<p class="sub">We sent a confirmation link to <b>{esc(email)}</b>. Open it to activate your dashboard.</p>'
            f'<p class="pw-hint">Check your spam folder if needed. This page will continue automatically after confirmation.</p>'
            f'<div class="msg" id="verify-msg" role="status"></div>'
            f'<button class="btn btn-green btn-block" type="button" id="verify-resend" style="margin-top:20px">Resend confirmation email</button>'
            f'<button class="btn btn-line btn-block" type="button" id="verify-logout" style="margin-top:10px">Use another account</button>'
            f'</div></div></section><script>(function(){{'
            f'var msg=document.getElementById("verify-msg"),resend=document.getElementById("verify-resend");'
            f'resend.onclick=async function(){{resend.disabled=true;try{{var r=await fetch("/api/auth/resend-verify",{{method:"POST"}});if(!r.ok)throw Error((await r.json()).detail||"Could not resend.");msg.className="msg ok";msg.textContent="A fresh confirmation link is on its way."}}catch(e){{msg.className="msg err";msg.textContent=e.message}}resend.disabled=false}};'
            f'document.getElementById("verify-logout").onclick=async function(){{await fetch("/api/auth/logout",{{method:"POST"}});location.href="/login"}};'
            f'setInterval(async function(){{try{{var r=await fetch("/api/auth/me",{{cache:"no-store"}});if(r.ok&&(await r.json()).user.email_verified!==0)location.href="/app#/deals"}}catch(e){{}}}},5000);'
            f'}})();</script>')
    return page(request, "/check-email", "Confirm your email | EstateHawk", "Confirm your email to open EstateHawk.", body, noindex=True)


def forgot(request):
    body = (f'<section class="sec" style="padding-top:56px"><div class="wrap"><form class="form" data-api="/api/auth/forgot" '
            f'data-ok="If that email has an account, a reset link is on its way. Check your inbox and spam folder." novalidate>'
            f'<h1>Reset your password</h1><p class="sub">Enter your account email and we will send you a link to choose a new password.</p><div class="msg" role="alert"></div>'
            f'<div class="field"><label for="f-email">Email</label><input id="f-email" name="email" type="email" autocomplete="email" required></div>'
            f'<button class="btn btn-green btn-block" type="submit">Send reset link {ic("arrow")}</button>'
            f'<p class="alt"><a href="/login">Back to sign in</a></p></form></div></section>')
    return page(request, "/forgot-password", "Reset password | EstateHawk", "Reset the password of your EstateHawk account.", body, noindex=True)


def reset(request):
    invite = request.query_params.get("invite") == "1"
    title = "Choose your password" if invite else "Choose a new password"
    body = (f'<section class="sec" style="padding-top:56px"><div class="wrap"><form class="form" data-api="/api/auth/reset" data-next="/app" data-password-rules="1" novalidate>'
            f'<h1>{title}</h1><p class="sub">{"Welcome to EstateHawk. Pick a password to finish setting up your login." if invite else "Pick a new password for your EstateHawk account."}</p><div class="msg" role="alert"></div>'
            f'<input type="hidden" name="token" value="{esc(request.query_params.get("token", ""))}">'
            f'{password_fields("r")}'
            f'<button class="btn btn-green btn-block" type="submit">Save password and sign in {ic("arrow")}</button>'
            f'<p class="alt"><a href="/forgot-password">Need a new link?</a></p></form></div></section>')
    return page(request, "/reset-password", f"{title} | EstateHawk", "Choose a password for your EstateHawk account.", body, noindex=True)


def signup(request):
    s = stats()
    # only counties whose leads come with an address or a map point: a new trial must see photos and real addresses
    ready = [c for c in s["counties"] if c.get("good", 0) >= 0.6 * c["n"]]
    opts = "".join(f'<option value="{c["id"]}">{esc(c["name"])}, {c["state"]} ({c["n"]:,} leads)</option>' for c in sorted(ready, key=lambda c: (c["state"], c["name"])))
    body = (f'<section class="sec" style="padding-top:46px"><div class="wrap"><form class="form" data-api="/api/auth/signup" data-next="/check-email" data-password-rules="1" novalidate>'
            f'<h1>Start your free trial</h1><p class="sub">14 days free. One county. No credit card.</p><div class="msg" role="alert"></div>'
            f'<div class="field"><label for="s-county">Your first county</label><select id="s-county" name="county_id" required><option value="">Choose a county</option>{opts}</select></div>'
            f'<div class="field"><label for="s-company">Company (optional)</label><input id="s-company" name="company" autocomplete="organization"></div>'
            f'{google_button("Sign up with Google", signup=True)}'
            f'<div class="field"><label for="s-name">Your name</label><input id="s-name" name="name" autocomplete="name" required></div>'
            f'<div class="field"><label for="s-email">Work email</label><input id="s-email" name="email" type="email" autocomplete="email" required></div>'
            f'{password_fields("s")}'
            f'<input class="hp" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">'
            f'<button class="btn btn-green btn-block" type="submit">Create my account {ic("arrow")}</button>'
            f'<p class="alt" style="font-size:13px;color:var(--muted)">By signing up you agree to our <a href="/terms">terms</a> and <a href="/privacy">privacy policy</a>.</p>'
            f'<p class="alt">Already have an account? <a href="/login">Sign in</a></p></form></div></section>')
    return page(request, "/signup", "Start Your Free Trial | EstateHawk", "Create your EstateHawk account: 14 days free, one county, no credit card.", body)


def not_found(request):
    body = (f'<section class="e404"><div class="wrap"><h1>404</h1><p style="font-size:19px;margin:10px 0 26px">This page is off the map.</p>'
            f'<a class="btn btn-green" href="/">Back to home {ic("arrow")}</a></div></section>')
    return page(request, "/404", "Page not found | EstateHawk", "This page does not exist.", body, noindex=True)


# ------------------------------------------------------------------ routing, sitemap, robots
STATIC_PAGES = {"": home, "features": features, "how-it-works": how, "pricing": pricing, "counties": counties, "guides": guides,
                "about": about, "contact": contact, "faq": faq_page, "login": login, "signup": signup, "forgot-password": forgot, "reset-password": reset,
                "privacy": lambda r: legal(r, "privacy"), "terms": lambda r: legal(r, "terms"), "refund-policy": lambda r: legal(r, "refund")}


def render(request, path):
    """Return HTML for a site path, or None if it is not a site page."""
    path = path.strip("/")
    if path in STATIC_PAGES:
        return STATIC_PAGES[path](request)
    parts = path.split("/")
    if len(parts) == 2 and parts[0] == "counties":
        return county_state(request, parts[1])
    if len(parts) == 2 and parts[0] == "guides":
        return guide(request, parts[1])
    return None


def sitemap(request):
    b = base_url(request)
    today = dt.date.today().isoformat()
    urls = [("", "1.0", "daily"), ("features", "0.9", "monthly"), ("how-it-works", "0.8", "monthly"), ("pricing", "0.9", "monthly"),
            ("counties", "0.9", "daily"), ("guides", "0.7", "weekly"), ("about", "0.5", "yearly"), ("contact", "0.5", "yearly"),
            ("faq", "0.6", "monthly"), ("signup", "0.7", "yearly"), ("privacy", "0.2", "yearly"), ("terms", "0.2", "yearly"), ("refund-policy", "0.2", "yearly")]
    urls += [(f"counties/{slug(STATE_NAMES.get(st, st))}", "0.8", "daily") for st in stats()["states"]]
    urls += [(f"guides/{g[0]}", "0.6", "monthly") for g in GUIDES]
    body = "".join(f"<url><loc>{b}/{u}</loc><lastmod>{today}</lastmod><changefreq>{f}</changefreq><priority>{p}</priority></url>" for u, p, f in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'


def robots(request):
    return f"User-agent: *\nAllow: /\nDisallow: /app\nDisallow: /api/\nDisallow: /login\n\nSitemap: {base_url(request)}/sitemap.xml\n"
