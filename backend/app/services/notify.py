"""Avvisi: mail (canale principale) e web push (facoltativo). Tutto finisce in notification_log."""
import json
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

from .. import config


def send_email(subject: str, text: str, html: str | None = None, image_path: str | None = None) -> bool:
    if not (config.SMTP_HOST and config.MAIL_TO):
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.MAIL_FROM or config.SMTP_USER
    msg["To"] = config.MAIL_TO
    msg.set_content(text)
    if html:
        cid = make_msgid()
        body = html.replace("{{image}}", f'<img src="cid:{cid[1:-1]}" width="360" alt="outfit">' if image_path else "")
        msg.add_alternative(body, subtype="html")
        if image_path:
            full = config.PHOTOS_DIR / image_path
            if full.exists():
                msg.get_payload()[1].add_related(full.read_bytes(), "image", "jpeg", cid=cid)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as s:
        s.starttls()
        if config.SMTP_USER:
            s.login(config.SMTP_USER, config.SMTP_PASSWORD)
        s.send_message(msg)
    return True


def send_push(conn, title: str, body: str, url: str = "/") -> int:
    if not config.VAPID_PRIVATE_KEY:
        return 0
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        return 0
    sent = 0
    for sub in conn.execute("SELECT * FROM push_subscriptions").fetchall():
        try:
            webpush(
                subscription_info={"endpoint": sub["endpoint"], "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}},
                data=json.dumps({"title": title, "body": body, "url": url}),
                vapid_private_key=config.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": config.VAPID_SUBJECT},
            )
            sent += 1
        except WebPushException as exc:
            # 404/410: l'abbonamento non esiste più
            if exc.response is not None and exc.response.status_code in (404, 410):
                conn.execute("DELETE FROM push_subscriptions WHERE id = ?", (sub["id"],))
    return sent


def notify(conn, kind: str, title: str, body: str, *, url: str = "/", html: str | None = None,
           image: str | None = None, sources: dict | None = None) -> dict:
    """Manda la mail e il push. Non solleva mai: un avviso fallito non deve bloccare l'app."""
    result = {"email": False, "push": 0}
    try:
        result["email"] = send_email(title, body + f"\n\n{config.APP_URL}{url}", html, image)
    except Exception as exc:
        result["email_error"] = type(exc).__name__
    try:
        result["push"] = send_push(conn, title, body, url)
    except Exception as exc:
        result["push_error"] = type(exc).__name__
    conn.execute(
        "INSERT INTO notification_log(kind, title, body, sources) VALUES (?,?,?,?)",
        (kind, title, body, json.dumps({**(sources or {}), "delivery": result})),
    )
    return result
