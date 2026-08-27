"""
System-level SMTP — used ONLY for pre-auth or cross-tenant emails:
  - signup verification OTP
  - password reset OTP
  - new-user invite (sent before the invitee has any company SMTP)

Uses wecode18@gmail.com as the hardcoded OTP sender. common_site_config.json
values override these defaults if present, but the app works on any device
without manual SMTP configuration.
"""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

import frappe

# ── Hardcoded OTP SMTP (wecode18@gmail.com) ───────────────────────────────────
# This is the single, fixed sender for all system OTPs (signup, password reset,
# invites). It never changes per-company. On a new device this works out of the
# box without any configuration. common_site_config.json values override these.
_DEFAULT_SMTP = {
    "server":     "smtp.gmail.com",
    "port":       587,
    "login":      "wecode18@gmail.com",
    "password":   "jznv fhwc gzkz wvpg",
    "use_tls":    True,
    "use_ssl":    False,
    "from_email": "wecode18@gmail.com",
    "from_name":  "Books by Tareqix",
}


def _conf() -> dict:
    """Return SMTP config: common_site_config.json values take priority,
    hardcoded wecode18 defaults fill any missing keys."""
    c = frappe.conf
    return {
        "server":     c.get("mail_server")   or _DEFAULT_SMTP["server"],
        "port":       int(c.get("mail_port") or _DEFAULT_SMTP["port"]),
        "login":      c.get("mail_login")    or _DEFAULT_SMTP["login"],
        "password":   c.get("mail_password") or _DEFAULT_SMTP["password"],
        "use_tls":    bool(c.get("use_tls", _DEFAULT_SMTP["use_tls"])),
        "use_ssl":    bool(c.get("use_ssl",  _DEFAULT_SMTP["use_ssl"])),
        "from_email": c.get("auto_email_id") or _DEFAULT_SMTP["from_email"],
        "from_name":  c.get("email_sender_name") or _DEFAULT_SMTP["from_name"],
    }


def get_system_smtp_config() -> dict:
    """Public accessor for the platform (wecode18@gmail.com) SMTP config dict.
    Same shape as the per-company SMTP config, so it can be passed to the shared
    low-level sender in utils/email_company._smtp_send."""
    return _conf()


def send_system_email(to: str, subject: str, html: str, text_fallback: str = "") -> bool:
    """Send a single email via the system SMTP. Returns True on success.
    Never raises — logs errors and returns False so callers can degrade gracefully."""
    cfg = _conf()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((cfg["from_name"], cfg["from_email"]))
    msg["To"] = to

    if text_fallback:
        msg.attach(MIMEText(text_fallback, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if cfg["use_ssl"]:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["server"], cfg["port"], context=ctx, timeout=15) as server:
                server.login(cfg["login"], cfg["password"])
                server.sendmail(cfg["from_email"], [to], msg.as_string())
        else:
            with smtplib.SMTP(cfg["server"], cfg["port"], timeout=15) as server:
                server.ehlo()
                if cfg["use_tls"]:
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                server.login(cfg["login"], cfg["password"])
                server.sendmail(cfg["from_email"], [to], msg.as_string())
        return True
    except Exception as exc:
        frappe.log_error(f"System SMTP send failed for {to}: {exc}", "Books System SMTP")
        return False
