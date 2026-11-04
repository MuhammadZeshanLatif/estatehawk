"""Customer email (welcome, password reset, invites, contact form).

Render's free plan blocks SMTP ports, so mail goes out over HTTPS through Resend when RESEND_API_KEY is set.
SMTP (SMTP_HOST/SMTP_USER/SMTP_PASSWORD) is the fallback for a paid server or a local test.
Nothing configured -> the email is skipped and logged, the app keeps working.
"""
import html, logging, os, smtplib, ssl
from email.message import EmailMessage

import requests

log = logging.getLogger("estatehawk.mail")
esc = html.escape


def sender():
    return os.environ.get("MAIL_FROM") or "EstateHawk <support@getestatehawk.com>"


def configured():
    e = os.environ.get
    return bool(e("RESEND_API_KEY") or (e("SMTP_HOST") and e("SMTP_USER") and e("SMTP_PASSWORD")))


def layout(title, paragraphs, button=None, foot="You get this email because of your EstateHawk account."):
    """One simple branded email: logo line, heading, short paragraphs, one button."""
    ps = "".join(f'<p style="margin:0 0 14px;font-size:15px;line-height:1.55;color:#2f3d34">{p}</p>' for p in paragraphs)
    btn = (f'<p style="margin:22px 0"><a href="{esc(button[1])}" style="background:#1A4A30;color:#ffffff;text-decoration:none;'
           f'padding:12px 20px;border-radius:8px;font-weight:600;font-size:15px;display:inline-block">{esc(button[0])}</a></p>'
           f'<p style="margin:0 0 14px;font-size:12px;color:#6b7a70">Or open this link: <a href="{esc(button[1])}" style="color:#1A4A30">{esc(button[1])}</a></p>') if button else ""
    return (f'<!doctype html><html><body style="margin:0;background:#FAF7F0;font-family:Arial,Helvetica,sans-serif">'
            f'<div style="max-width:560px;margin:0 auto;padding:28px 20px">'
            f'<p style="margin:0 0 18px;font-size:18px;font-weight:700;color:#17301F">EstateHawk</p>'
            f'<div style="background:#ffffff;border:1px solid #E7DFD0;border-radius:12px;padding:26px">'
            f'<h1 style="margin:0 0 14px;font-size:20px;color:#17301F">{esc(title)}</h1>{ps}{btn}</div>'
            f'<p style="margin:16px 4px 0;font-size:12px;color:#6b7a70">{esc(foot)} Questions? Reply to this email or write to support@getestatehawk.com.<br>'
            f'EstateHawk, getestatehawk.com</p></div></body></html>')


def _text(paragraphs, button=None):
    import re
    plain = "\n\n".join(re.sub(r"<[^>]+>", "", p) for p in paragraphs)
    return plain + (f"\n\n{button[0]}: {button[1]}" if button else "") + "\n\nEstateHawk, getestatehawk.com"


def send(to, subject, title, paragraphs, button=None, reply_to=None, foot=None):
    """Returns True when handed to the mail service. Never raises: a failed email must not break signup or login."""
    if not to:
        return False
    body_html = layout(title, paragraphs, button, **({"foot": foot} if foot else {}))
    body_text = _text(paragraphs, button)
    e = os.environ.get
    try:
        if e("RESEND_API_KEY"):
            r = requests.post("https://api.resend.com/emails", timeout=20,
                              headers={"Authorization": f"Bearer {e('RESEND_API_KEY')}"},
                              json={"from": sender(), "to": [to], "subject": subject, "html": body_html, "text": body_text,
                                    **({"reply_to": reply_to} if reply_to else {})})
            if r.status_code >= 300:
                log.warning("resend %s: %s", r.status_code, r.text[:200])
                return False
            return True
        if e("SMTP_HOST") and e("SMTP_USER") and e("SMTP_PASSWORD"):
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = sender(), to, subject
            if reply_to:
                msg["Reply-To"] = reply_to
            msg.set_content(body_text)
            msg.add_alternative(body_html, subtype="html")
            port = int(e("SMTP_PORT") or 587)
            if port == 465:
                with smtplib.SMTP_SSL(e("SMTP_HOST"), port, timeout=30, context=ssl.create_default_context()) as s:
                    s.login(e("SMTP_USER"), e("SMTP_PASSWORD")); s.send_message(msg)
            else:
                with smtplib.SMTP(e("SMTP_HOST"), port, timeout=30) as s:
                    s.starttls(context=ssl.create_default_context()); s.login(e("SMTP_USER"), e("SMTP_PASSWORD")); s.send_message(msg)
            return True
        log.info("email skipped (no mail service set): %s to %s", subject, to)
    except Exception as ex:  # noqa: BLE001
        log.warning("email failed: %s", ex)
    return False
