"""Lavori pianificati. Un cron chiama /api/cron/tick ogni 10 minuti la sera e una volta al mattino:
qui decidiamo cosa fare in base all'ora locale. Ogni lavoro gira al massimo una volta al giorno."""
import html as h
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .. import config
from ..db import get_setting, rows, set_setting
from . import calendar, day as dayplan, notify, trips

DRESS = {"completo": "Completo", "informale": "Informale", "libero": "Libero"}


def now_local(conn) -> datetime:
    return datetime.now(ZoneInfo(get_setting(conn, "timezone", "Europe/Brussels"))).replace(tzinfo=None)


def tick(conn, now: datetime | None = None) -> dict:
    now = now or now_local(conn)
    today = now.date()
    done = {}

    if get_setting(conn, "last_maintenance") != today.isoformat():
        status = calendar.refresh(conn)
        set_setting(conn, "calendar_status", {**status, "at": now.isoformat(timespec="minutes")})
        done["calendar"] = status
        done["plenary_trips"] = trips.create_plenary_trips(conn, today)
        set_setting(conn, "last_maintenance", today.isoformat())

    hh, mm = map(int, get_setting(conn, "notify_time", "20:30").split(":"))
    at = datetime.combine(today, time(hh, mm))
    if at <= now < at + timedelta(hours=3) and get_setting(conn, "last_evening") != today.isoformat():
        set_setting(conn, "last_evening", today.isoformat())  # prima di spedire: mai due mail
        done["evening"] = evening(conn, today)

    for r in rows(conn.execute(
            "SELECT * FROM reminders WHERE done = 0 AND sent_at IS NULL AND due_at <= ?",
            (now.isoformat(timespec="minutes"),))):
        notify.notify(conn, r["kind"], r["title"], r["title"], url=r["link"] or "/")
        conn.execute("UPDATE reminders SET sent_at = ? WHERE id = ?", (now.isoformat(timespec="minutes"), r["id"]))
        done.setdefault("reminders", 0)
        done["reminders"] = done["reminders"] + 1
    return done


def evening(conn, today: date) -> dict:
    """La mail della sera: domani, il meteo, l'outfit, e gli avvisi dei viaggi."""
    tomorrow = today + timedelta(days=1)
    plan = dayplan.build(conn, tomorrow)
    lines, blocks = [], []

    head = f"{DRESS[plan['dress_code']]} · {plan['reason']} · {plan['city']} · {plan['weather_text']}"
    lines.append(head)
    outfit = plan["outfits"][0] if plan["outfits"] else None
    if outfit:
        names = [i["name"] for i in outfit["items"]]
        lines.append("Outfit: " + ", ".join(names))
        blocks.append("{{image}}<ul>" + "".join(f"<li>{h.escape(n)}</li>" for n in names) + "</ul>")
    for m in plan["missing"]:
        lines.append(m)
        blocks.append(f"<p><b>Cosa manca:</b> {h.escape(m)}</p>")

    problems = []
    if not plan["calendar_ok"]:
        problems.append(f"the361: {plan['calendar_message']}. Uso le regole di base.")
    if not plan["weather_ok"]:
        problems.append("Meteo non disponibile: niente filtri su pioggia e temperatura.")
    for p in problems:
        lines.append(p)
        blocks.append(f"<p style='color:#8a5a00'>{h.escape(p)}</p>")

    alert_days = get_setting(conn, "trip_alert_days", 2)
    for t in rows(conn.execute("SELECT * FROM trips WHERE status IN ('pianificato','in_corso')")):
        start, end = date.fromisoformat(t["start_date"]), date.fromisoformat(t["end_date"])
        link = f"{config.APP_URL}/viaggi/{t['id']}"
        if start - timedelta(days=alert_days) == today:
            p = trips.plan(conn, t["id"])
            todo = [f"{g['name']} ({g['status'].replace('_', ' ')})" for g in p["not_ready"]]
            msg = f"Tra {alert_days} giorni parti per {t['destination']}."
            msg += (" Da preparare: " + ", ".join(todo) + ".") if todo else " I capi che servono sono pronti."
            lines.append(msg)
            blocks.append(f"<p>{h.escape(msg)} <a href='{link}'>Apri il viaggio</a></p>")
        if start == tomorrow:
            msg = f"Domani parti per {t['destination']}. Fai la valigia con la checklist."
            lines.append(f"{msg} {link}/valigia")
            blocks.append(f"<p><b>{h.escape(msg)}</b> <a href='{link}/valigia'>Checklist</a></p>")
        if end == tomorrow and start < tomorrow:
            msg = "Domani rientri: caricatori, cuscino, tappi? Controlla la checklist di ritorno."
            lines.append(f"{msg} {link}/rientro")
            blocks.append(f"<p><b>{h.escape(msg)}</b> <a href='{link}/rientro'>Checklist di ritorno</a></p>")

    title = f"Domani: {DRESS[plan['dress_code']].lower()}, {plan['weather_text']}"
    html = ("<div style='font-family:Inter,Arial,sans-serif;color:#1b1d22;max-width:420px'>"
            f"<p style='color:#6b6a66'>{h.escape(head)}</p>" + "".join(blocks) + "</div>")
    return notify.notify(conn, "sera", title, "\n".join(lines), url="/", html=html,
                         image=outfit["image"] if outfit else None,
                         sources={"the361": plan["calendar_ok"], "meteo": plan["weather_ok"]})
