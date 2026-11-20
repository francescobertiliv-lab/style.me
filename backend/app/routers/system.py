"""Impostazioni, calendario PE, dress code, stato delle fonti, push e cron."""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from .. import config
from ..auth import require_user
from ..db import get_db, get_setting, rows, set_setting
from ..services import calendar, jobs, notify

router = APIRouter(prefix="/api", dependencies=[Depends(require_user)])
cron = APIRouter(prefix="/api/cron")

EDITABLE = ("notify_time", "trip_alert_days", "the361_url", "home_city_id", "timezone", "rain", "climate", "plenary_trip")


@router.get("/settings")
def settings(db=Depends(get_db)):
    return {k: get_setting(db, k) for k in EDITABLE}


@router.put("/settings")
def save_settings(body: dict, db=Depends(get_db)):
    for k, v in body.items():
        if k in EDITABLE:
            set_setting(db, k, v)
    return {"ok": True}


@router.get("/status")
def status(db=Depends(get_db)):
    return {
        "calendar": get_setting(db, "calendar_status", {}),
        "mail": bool(config.RESEND_API_KEY and config.MAIL_TO),
        "push": bool(config.VAPID_PUBLIC_KEY),
        "photos": "supabase" if config.SUPABASE_URL else "locale",
        "last_evening": get_setting(db, "last_evening"),
        "log": rows(db.execute("SELECT * FROM notification_log ORDER BY id DESC LIMIT 10")),
    }


@router.post("/notify/test")
def test(db=Depends(get_db)):
    return notify.notify(db, "prova", "Prova da Style.me", "Se leggi questo, gli avvisi funzionano.")


@router.post("/notify/evening-now")
def evening_now(db=Depends(get_db)):
    """Manda subito la mail della sera (per provarla)."""
    return jobs.evening(db, jobs.now_local(db).date())


@router.post("/calendar/refresh")
def refresh(db=Depends(get_db)):
    s = calendar.refresh(db)
    set_setting(db, "calendar_status", s)
    return s


@router.get("/calendar")
def ep_calendar(db=Depends(get_db)):
    return {"weeks": rows(db.execute("SELECT week_start, week_type, place FROM ep_weeks ORDER BY week_start")),
            "holidays": [r["date"] for r in db.execute("SELECT date FROM ep_holidays ORDER BY date")],
            "labels": calendar.WEEK_LABELS}


class Week(BaseModel):
    week_type: str


@router.put("/calendar/{week_start}")
def set_week(week_start: str, body: Week, db=Depends(get_db)):
    db.execute("INSERT INTO ep_weeks(week_start, week_type, fetched_at) VALUES (?,?, 'a mano') "
               "ON CONFLICT(week_start) DO UPDATE SET week_type = excluded.week_type, fetched_at = 'a mano'",
               (week_start, body.week_type))
    return {"ok": True}


@router.get("/dress-rules")
def dress_rules(db=Depends(get_db)):
    return rows(db.execute("SELECT * FROM dress_rules ORDER BY week_type, weekday"))


class DressRule(BaseModel):
    week_type: str
    weekday: int
    dress_code: str


@router.put("/dress-rules")
def set_dress_rule(body: DressRule, db=Depends(get_db)):
    db.execute("INSERT INTO dress_rules(week_type, weekday, dress_code) VALUES (?,?,?) "
               "ON CONFLICT(week_type, weekday) DO UPDATE SET dress_code = excluded.dress_code",
               (body.week_type, body.weekday, body.dress_code))
    return {"ok": True}


@router.get("/push/key")
def push_key():
    return {"key": config.VAPID_PUBLIC_KEY}


class Sub(BaseModel):
    endpoint: str
    keys: dict
    device: str | None = None


@router.post("/push/subscribe")
def subscribe(body: Sub, db=Depends(get_db)):
    db.execute("INSERT INTO push_subscriptions(endpoint, p256dh, auth, device) VALUES (?,?,?,?) "
               "ON CONFLICT(endpoint) DO UPDATE SET p256dh = excluded.p256dh, auth = excluded.auth",
               (body.endpoint, body.keys["p256dh"], body.keys["auth"], body.device))
    return {"ok": True}


@cron.api_route("/tick", methods=["GET", "POST"])
def tick(authorization: str = Header(""), db=Depends(get_db)):
    """Chiamato da GitHub Actions ogni 10 minuti la sera e dal cron di Vercel come riserva."""
    if not config.CRON_SECRET or authorization != f"Bearer {config.CRON_SECRET}":
        raise HTTPException(401)
    return jobs.tick(db)
