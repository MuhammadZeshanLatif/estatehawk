"""Gemini API (Google AI Studio key) for offer emails/letters and score explanations.

Set GEMINI_API_KEY in the .env file (Settings > Integrations can save it too).
Everything has a template fallback, so the app works without a key.
"""
import json, os, re
import requests

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def keys():
    return [v for v in dict.fromkeys((os.environ.get(k) or "").strip() for k in ("GEMINI_API_KEY", "GEMINI_API_KEY_BACKUP")) if v]


def key():
    return keys()[0] if keys() else ""


def model():
    return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()


def enabled():
    return bool(key())


def generate(prompt, max_tokens=900, temperature=0.6, timeout=60):
    if not keys():
        raise RuntimeError("Gemini is not configured")
    errors = []
    for credential in keys():
        try:
            r = requests.post(API.format(model=model()), params={"key": credential}, timeout=timeout, json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
            })
            if r.status_code != 200:
                raise RuntimeError(f"Gemini error {r.status_code}: {r.text[:200]}")
            data = r.json()
            result = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]).strip()
            if result:
                return result
            raise RuntimeError("Gemini returned an empty answer")
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError, RuntimeError) as e:
            errors.append(str(e)[:200])
    raise RuntimeError("Both Gemini keys failed: " + "; ".join(errors))


def test():
    return generate("Reply with the single word: OK", max_tokens=5, temperature=0)


def _first_name(owner):
    o = (owner or "").replace("&", " ").split()
    # county format is LAST FIRST ...
    if len(o) >= 2:
        return o[1].title()
    return "there"


def template_offer(p, terms, profile):
    addr = f"{p.get('street', '').title()}, {p.get('city', '').title()}".strip(", ")
    name = profile.get("name") or "a local buyer"
    company = profile.get("company") or ""
    subject = f"Quick question about your property at {p.get('street', '').title()}"
    lines = [
        f"Hi {_first_name(p.get('owner_name'))},",
        "",
        f"My name is {name}{' with ' + company if company else ''}. I buy houses in {p.get('city', '').title() or 'your area'} "
        f"and came across your property at {addr} in the county records.",
        "",
        "If you have thought about selling, I would like to make you a simple, as-is offer. "
        "I can cover the back taxes at closing, so you would not need to pay them first or fix anything.",
        "",
        "Here is what I can offer:",
        f"- Offer price: ${terms['price']:,.0f}",
        f"- Financing: {terms['financing']}",
        f"- Closing: in about {terms['closing_days']} days, or on your timeline",
        f"- Seller credits: {terms['seller_credits']}",
        f"- Earnest money deposit: ${terms['earnest']:,.0f}",
        "",
        "No pressure at all. If you are open to it, reply or call me and we can talk for five minutes.",
        "",
        "Best regards,",
        name,
    ]
    if profile.get("phone"):
        lines.append(profile["phone"])
    if profile.get("email"):
        lines.append(profile["email"])
    return subject, "\n".join(lines)


def ai_offer(p, terms, profile):
    prompt = f"""Write a short, warm, honest first-contact letter/email from a real estate investor to a property owner
who is behind on property taxes. Do not mention their tax problem harshly; be respectful, no pressure, no false promises.
Plain English, 120-170 words, no emojis. Return JSON with keys "subject" and "body" only.

Owner (county format LAST FIRST): {p.get('owner_name')}
Property: {p.get('street')}, {p.get('city')} {p.get('state')} {p.get('zip')}
Investor: {profile.get('name')} {('(' + profile.get('company') + ')') if profile.get('company') else ''}, phone {profile.get('phone') or 'n/a'}, email {profile.get('email') or 'n/a'}
Offer terms to list as bullets: price ${terms['price']:,.0f}; financing {terms['financing']}; closing in about {terms['closing_days']} days;
seller credits: {terms['seller_credits']}; earnest money ${terms['earnest']:,.0f}. Mention the buyer can pay the back taxes at closing."""
    txt = generate(prompt)
    m = re.search(r"\{.*\}", txt, re.S)
    data = json.loads(m.group(0))
    return data["subject"].strip(), data["body"].strip()


def offer(p, terms, profile):
    if enabled():
        try:
            s, b = ai_offer(p, terms, profile)
            return s, b, "gemini"
        except Exception as e:  # fall back quietly, note the source
            s, b = template_offer(p, terms, profile)
            return s, b, f"template (Gemini failed: {str(e)[:80]})"
    s, b = template_offer(p, terms, profile)
    return s, b, "template"


def ai_reasons(p, parts):
    prompt = f"""You are a real estate deal analyst. In exactly 3 bullet points (each: a 2-4 word title, a colon, then one short sentence),
explain why this tax-delinquent property scored {p.get('score')}/100 for a wholesaler. Use only these facts, no invented data.
Return JSON list of objects with "title" and "text".
Facts: {json.dumps({k: p.get(k) for k in ('years_behind', 'total_due', 'amount_owed', 'appraised_total', 'est_equity', 'mail_state', 'state', 'owner_occupied', 'land_use', 'improvement_value')})}
Score parts (points): {json.dumps(parts)}"""
    txt = generate(prompt, max_tokens=400, temperature=0.3)
    m = re.search(r"\[.*\]", txt, re.S)
    return [(d["title"], d["text"]) for d in json.loads(m.group(0))][:3]
