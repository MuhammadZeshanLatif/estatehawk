"""Alert delivery: Email (SMTP, e.g. Gmail app password), Slack (incoming webhook), SMS / WhatsApp (Twilio).
All credentials come from .env. A channel is used only if it is switched on in Settings AND configured."""
import os, smtplib, ssl
from email.message import EmailMessage
import requests


def configured():
    e = os.environ.get
    return {
        "email": bool(e("SMTP_HOST") and e("SMTP_USER") and e("SMTP_PASSWORD") and e("ALERT_EMAIL_TO")),
        "slack": bool(e("SLACK_WEBHOOK_URL")),
        "sms": bool(e("TWILIO_SID") and e("TWILIO_TOKEN") and e("TWILIO_FROM") and e("ALERT_PHONE_TO")),
        "whatsapp": bool(e("TWILIO_SID") and e("TWILIO_TOKEN") and e("TWILIO_WHATSAPP_FROM") and e("ALERT_PHONE_TO")),
        "gemini": bool(e("GEMINI_API_KEY")),
    }


def send_email(subject, body):
    e = os.environ.get
    msg = EmailMessage()
    msg["From"] = e("SMTP_FROM") or e("SMTP_USER")
    msg["To"] = e("ALERT_EMAIL_TO")
    msg["Subject"] = subject
    msg.set_content(body)
    port = int(e("SMTP_PORT") or 587)
    with smtplib.SMTP(e("SMTP_HOST"), port, timeout=30) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(e("SMTP_USER"), e("SMTP_PASSWORD"))
        s.send_message(msg)


def send_slack(text):
    r = requests.post(os.environ["SLACK_WEBHOOK_URL"], json={"text": text}, timeout=20)
    r.raise_for_status()


def _twilio(to, frm, body):
    sid, tok = os.environ["TWILIO_SID"], os.environ["TWILIO_TOKEN"]
    r = requests.post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                      auth=(sid, tok), data={"To": to, "From": frm, "Body": body[:1500]}, timeout=20)
    r.raise_for_status()


def send_sms(body):
    _twilio(os.environ["ALERT_PHONE_TO"], os.environ["TWILIO_FROM"], body)


def send_whatsapp(body):
    _twilio("whatsapp:" + os.environ["ALERT_PHONE_TO"], "whatsapp:" + os.environ["TWILIO_WHATSAPP_FROM"], body)


def deliver(channels, subject, body):
    """channels: dict from settings. Returns {channel: 'sent'|'error ...'}"""
    ok = configured()
    res = {}
    for ch, fn in (("email", lambda: send_email(subject, body)), ("slack", lambda: send_slack(f"*{subject}*\n{body}")),
                   ("sms", lambda: send_sms(f"{subject}\n{body}")), ("whatsapp", lambda: send_whatsapp(f"{subject}\n{body}"))):
        if channels.get(ch) and ok.get(ch):
            try:
                fn()
                res[ch] = "sent"
            except Exception as ex:
                res[ch] = f"error: {ex}"[:200]
    return res
