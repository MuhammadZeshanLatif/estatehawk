"""Server-rendered article navigation and conservative automatic related reading."""
import datetime as dt
import html
import math
import re
from html.parser import HTMLParser

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, value):
        self.parts.append(value)

def plain(value):
    parser = Text(); parser.feed(value)
    return " ".join(parser.parts)

def article_body(rendered):
    headings, seen, used = [], {}, set()
    def anchor(match):
        level, value = match.groups()
        title = plain(value)
        base = "section-" + (re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "heading")
        seen[base] = seen.get(base, 0) + 1
        ident = base if seen[base] == 1 else f"{base}-{seen[base]}"
        while ident in used:
            seen[base] += 1
            ident = f"{base}-{seen[base]}"
        used.add(ident)
        headings.append((level, ident, title))
        return f'<h{level} id="{ident}" tabindex="-1">{value}</h{level}>'
    result = re.sub(r"<h([23])>(.*?)</h[23]>", anchor, rendered)
    # Rendered text excludes image alt, URLs and Markdown delimiters.
    minutes = max(1, math.ceil(len(re.findall(r"\b[\w'-]+\b", plain(result))) / 225))
    return result, headings, minutes

STOP = set("a an and are as at be before by can do does for from guide how in into is it of on or property properties real estate should the to up vs what when where which who with your you investors investing find verify research".split())
NORMAL = {"liens": "lien", "taxes": "tax", "records": "record", "owners": "owner", "leads": "lead", "deeds": "deed"}
FAMILIES = {
    "title-review": ("quiet title", "title search", "lien search", "liens on", "municipal lien", "tax deed", "abstract of title", "title commitment", "chain of title"),
    "financing": ("loan", "financing", "mortgage", "land contract", "contract for deed"),
    "rental-analysis": ("cap rate", "cash on cash", "gross rent", "net operating", "rent roll"),
    "deed-review": ("warranty deed", "quitclaim", "grant deed"),
    "land-rights": ("easement", "encroachment", "landlocked", "property survey", "boundary survey"),
    "tax-sales": ("tax lien", "tax deed", "tax sale", "tax delinquent"),
    "owner-discovery": ("owner", "skip tracing", "absentee", "probate"),
    "team-workflow": ("lead follow", "lead management", "lead tracking"),
    "valuation": ("assessed", "market value", "appraised", "assessment"),
}

def related(current, candidates, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    def signals(item):
        title = item["title"].lower()
        words = {NORMAL.get(w, w) for w in re.findall(r"[a-z]+", title) if w not in STOP}
        families = {name for name, terms in FAMILIES.items() if any(t in title for t in terms)}
        return words, families
    words, families = signals(current)
    ranked, seen = [], set()
    for item in candidates:
        slug = item.get("slug")
        if not slug or slug == current["slug"] or slug in seen or item.get("status") != "published":
            continue
        try:
            published = dt.datetime.fromisoformat(str(item.get("published") or "").replace("Z", "+00:00"))
            if published.tzinfo is None:
                continue
            if published > now:
                continue
        except ValueError:
            continue
        seen.add(slug)
        other, groups = signals(item)
        shared = words & other
        family_match = bool(families & groups)
        if not family_match and len(shared) < 2:
            continue
        score = 4 * len(families & groups) + 2 * len(shared) + len(shared) / max(1, len(words | other))
        ranked.append((score, published.timestamp(), slug, item))
    ranked.sort(key=lambda row: (-row[0], -row[1], row[2]))
    return [row[3] for row in ranked[:3]]

CSS = """
.blog-shell{padding:30px 0 64px}.blog-shell>.wrap{max-width:1460px}.blog-grid{display:grid;grid-template-columns:205px minmax(0,1fr) 245px;gap:24px;align-items:start;margin-top:24px}
.blog-article{min-width:0;padding:30px;background:var(--card);border:1px solid var(--line);border-radius:18px;box-shadow:0 8px 28px #17301f05}.blog-article h1{font-size:clamp(32px,3vw,46px);line-height:1.12;margin:12px 0 18px;overflow-wrap:anywhere}.blog-deck{font-size:18px;line-height:1.65}.blog-meta{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;border-bottom:1px solid var(--line);padding:20px 0;margin-bottom:24px;font-size:12px;color:var(--muted)}.blog-byline{display:flex;align-items:center;gap:8px;color:var(--green);font-weight:600}.blog-cover{display:block;width:100%;height:auto;aspect-ratio:3/2;object-fit:contain;background:var(--band);border-radius:12px;margin-bottom:28px}
.blog-panel{padding:20px;border:1px solid var(--line);border-radius:14px;background:var(--card)}.blog-panel h2,.blog-toc summary{font:600 12px/1.5 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--green)}.blog-left,.blog-right{position:sticky;top:100px;max-height:calc(100dvh - 120px);overflow-y:auto;scrollbar-width:thin}.blog-toc ol{list-style:none;margin:16px 0 0;padding:0}.blog-toc a{display:block;font-size:13px;line-height:1.5;padding:8px 10px;border-left:2px solid transparent;border-radius:0 6px 6px 0;overflow-wrap:anywhere}.blog-toc a:hover,.blog-toc a[aria-current=true]{background:var(--mint);border-color:var(--green);color:var(--green)}.blog-toc .sub{padding-left:12px}.blog-toc .sub a{font-size:12px}.blog-toc summary{cursor:pointer}.blog-toc .back-top{border-top:1px solid var(--line);margin-top:16px;padding-top:16px}.blog-author img{margin:18px 0 12px}.blog-author strong{display:block;color:var(--green);font:600 24px/1.3 var(--serif)}.blog-author p{font-size:13px;margin:10px 0}.blog-author a{font-size:13px;color:var(--green);text-decoration:underline}.blog-related{margin-top:20px}.blog-related a{display:flex;gap:10px;align-items:center;padding:15px 0;border-top:1px solid var(--line);font:600 16px/1.3 var(--serif);color:var(--ink);overflow-wrap:anywhere}.blog-related h2{margin-bottom:12px}.blog-related img{width:60px;height:54px;object-fit:cover;border-radius:7px;flex-shrink:0}.blog-body{overflow-wrap:anywhere}.blog-body h2,.blog-body h3{margin:34px 0 14px;scroll-margin-top:105px}.blog-body h2{font-size:30px}.blog-body h3{font-size:23px}.blog-body p,.blog-body li{font-size:17px;line-height:1.85}.blog-body p,.blog-body ul{margin:0 0 18px}.blog-body a{color:var(--green);text-decoration:underline;text-underline-offset:3px}.blog-figure{margin:30px 0}.blog-figure img{display:block;width:100%;max-width:100%;height:auto;border-radius:12px}.blog-figure figcaption{margin-top:10px;color:var(--muted);font-size:13px;line-height:1.6}.blog-mobile-toc{display:none}.blog-shell a:focus-visible,.blog-shell summary:focus-visible{outline:3px solid var(--leaf);outline-offset:3px}.blog-more{margin-top:28px}
@media(min-width:1101px){.blog-grid:not(:has(.blog-left)){grid-template-columns:minmax(0,1fr) 245px}}
@media(max-width:1100px){.blog-grid{grid-template-columns:190px minmax(0,1fr)}.blog-grid:not(:has(.blog-left)){grid-template-columns:minmax(0,1fr)}.blog-right{grid-column:2;position:static;max-height:none;overflow:visible}.blog-grid:not(:has(.blog-left)) .blog-right{grid-column:1}.blog-right .blog-panel{max-width:100%}.blog-article{padding:26px}.blog-related a{font-size:18px}}
@media(max-width:760px){.blog-shell{padding-top:18px}.blog-shell>.wrap{padding:0 16px}.blog-grid,.blog-grid:not(:has(.blog-left)){display:flex;flex-direction:column;gap:20px}.blog-left{display:none}.blog-article,.blog-right{width:100%}.blog-article{padding:22px 18px}.blog-article h1{font-size:34px}.blog-mobile-toc{display:block;margin-bottom:24px}.blog-body h2{font-size:27px}.blog-meta{gap:10px;font-size:12px}.blog-deck{font-size:16px}.blog-right{position:static;max-height:none}.blog-toc ol{max-height:45dvh;overflow:auto}.blog-shell .crumbs{font-size:12px}.blog-body p,.blog-body li{font-size:16px}}
@media(prefers-reduced-motion:reduce){html:has(.blog-shell){scroll-behavior:auto}}
"""

JS = """<script>
(()=>{const desktop=window.matchMedia('(min-width:761px)');const links=[...document.querySelectorAll('.blog-left a[href^="#section-"]')];const headings=[...document.querySelectorAll('.blog-body h2[id],.blog-body h3[id]')];if(!headings.length)return;let queued=false;function update(){queued=false;if(!desktop.matches)return;let active=headings[0].id;for(const h of headings){if(h.getBoundingClientRect().top<=150)active=h.id;else break}for(const a of links){if(a.hash.slice(1)===active)a.setAttribute('aria-current','true');else a.removeAttribute('aria-current')}}addEventListener('scroll',()=>{if(!queued){queued=true;requestAnimationFrame(update)}},{passive:true});update()})();
</script>"""
