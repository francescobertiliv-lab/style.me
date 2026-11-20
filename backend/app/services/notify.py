"""Avvisi: mail (canale principale) e web push (facoltativo). Tutto finisce in notification_log."""
import base64
import json

import httpx

from .. import config
from . import storage


def send_email(subject: str, text: str, html: str | None = None, image_path: str | None = None) -> bool:
    """Mail con Resend. L'immagine dell'outfit va dentro la mail come allegato in linea."""
    if not (config.RESEND_API_KEY and config.EMAIL_FROM and config.MAIL_TO):
        return False
    payload = {"from": config.EMAIL_FROM, "to": [config.MAIL_TO], "subject": subject, "text": text}
    if html:
        payload["html"] = html.replace("{{image}}", "")
    data = storage.get(image_path) if image_path else None
    if html and data:
        payload["html"] = html.replace(
            "{{image}}", '<img src="cid:outfit" width="360" alt="outfit" style="border-radius:12px">')
        payload["attachments"] = [{"filename": "outfit.jpg", "content": base64.b64encode(data).decode(),
                                   "content_id": "outfit"}]
    r = httpx.post("https://api.resend.com/emails", json=payload,
                   headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"}, timeout=20)
    if r.status_code == 422 and "attachments" in payload:  # senza immagine piuttosto che niente
        payload.pop("attachments")
        payload["html"] = html.replace("{{image}}", "")
        r = httpx.post("https://api.resend.com/emails", json=payload,
                       headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"}, timeout=20)
    r.raise_for_status()
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
