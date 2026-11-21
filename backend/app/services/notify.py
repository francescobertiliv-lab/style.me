"""Avvisi: mail (canale principale) e web push (facoltativo). Tutto finisce in notification_log."""
import base64
import json

import httpx

from .. import config
from ..db import get_setting
from . import storage


def mail_config(conn) -> dict:
    """Chiave e indirizzi: dall'app (primo avvio) o, in mancanza, dalle variabili d'ambiente."""
    return {"key": get_setting(conn, "resend_api_key") or config.RESEND_API_KEY,
            "from": get_setting(conn, "email_from") or config.EMAIL_FROM,
            "to": get_setting(conn, "mail_to") or config.MAIL_TO}


def send_email(conn, subject: str, text: str, html: str | None = None, image_path: str | None = None) -> bool:
    """Mail con Resend. L'immagine dell'outfit va dentro la mail come allegato in linea."""
    m = mail_config(conn)
    if not (m["key"] and m["from"] and m["to"]):
        return False
    payload = {"from": m["from"], "to": [m["to"]], "subject": subject, "text": text}
    if html:
        payload["html"] = html.replace("{{image}}", "")
    data = storage.get(image_path) if image_path else None
    if html and data:
        payload["html"] = html.replace(
            "{{image}}", '<img src="cid:outfit" width="360" alt="outfit" style="border-radius:12px">')
        payload["attachments"] = [{"filename": "outfit.jpg", "content": base64.b64encode(data).decode(),
                                   "content_id": "outfit"}]
    r = httpx.post("https://api.resend.com/emails", json=payload,
                   headers={"Authorization": f"Bearer {m['key']}"}, timeout=20)
    if r.status_code == 422 and "attachments" in payload:  # senza immagine piuttosto che niente
        payload.pop("attachments")
        payload["html"] = html.replace("{{image}}", "")
        r = httpx.post("https://api.resend.com/emails", json=payload,
                       headers={"Authorization": f"Bearer {m['key']}"}, timeout=20)
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
        result["email"] = send_email(conn, title, body + f"\n\n{config.APP_URL}{url}", html, image)
    except httpx.HTTPStatusError as exc:
        result["email_error"] = f"Resend {exc.response.status_code}: {exc.response.text[:200]}"
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
