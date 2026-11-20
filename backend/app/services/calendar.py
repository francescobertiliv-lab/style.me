"""Tipo di giornata e dress code, dal calendario PE di the361.

the361 oggi non espone un endpoint: il calendario sta nel codice della pagina.
Se `the361_url` risponde con un JSON del tipo
  {"weeks": [{"weekOf": "2027-01-04", "type": "green"}, ...], "holidays": ["2027-01-01", ...]}
(oppure direttamente la lista delle settimane) lo salviamo in ep_weeks.
Se non risponde, usiamo l'ultima copia salvata e lo diciamo nella notifica.
"""
import json
from datetime import date, datetime, timedelta

import httpx

from ..db import get_setting, row

WEEK_LABELS = {
    "committee": "settimana di commissione",
    "group": "settimana di gruppo",
    "plenary": "plenaria a Strasburgo",
    "plenary-brussels": "mini-plenaria a Bruxelles",
    "green": "settimana verde",
    "recess": "pausa",
}
DRESS_LABELS = {"completo": "completo", "informale": "informale", "libero": "libero"}


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_type(conn, d: date) -> str:
    r = conn.execute(
        "SELECT week_type FROM ep_weeks WHERE week_start = ?", (monday(d).isoformat(),)
    ).fetchone()
    return r["week_type"] if r else "committee"


def day_info(conn, d: date, trip: dict | None = None) -> dict:
    """Dress code del giorno: forzatura a mano > festivo > regola della settimana."""
    wt = week_type(conn, d)
    override = row(conn.execute("SELECT * FROM day_overrides WHERE date = ?", (d.isoformat(),)))
    holiday = conn.execute("SELECT 1 FROM ep_holidays WHERE date = ?", (d.isoformat(),)).fetchone()
    if override:
        code, reason = override["dress_code"], override["note"] or "scelto da te"
    elif holiday and d.weekday() < 5:
        code, reason = "libero", "festivo"
    else:
        r = conn.execute(
            "SELECT dress_code FROM dress_rules WHERE week_type = ? AND weekday = ?",
            (wt, d.weekday()),
        ).fetchone()
        # Regola di base se manca: lun–gio completo, venerdì informale, weekend libero.
        if r:
            code = r["dress_code"]
        else:
            code = "completo" if d.weekday() < 4 else "informale" if d.weekday() == 4 else "libero"
        reason = WEEK_LABELS.get(wt, wt)
    return {
        "date": d.isoformat(),
        "week_type": wt,
        "week_label": WEEK_LABELS.get(wt, wt),
        "dress_code": code,
        "reason": reason,
        "overridden": bool(override),
        "trip_id": trip["id"] if trip else None,
    }


def _parse(payload) -> tuple[list[dict], list[str]]:
    if isinstance(payload, list):
        return payload, []
    return payload.get("weeks", []), payload.get("holidays", [])


def refresh(conn, timeout: float = 10.0) -> dict:
    """Aggiorna ep_weeks da the361. Ritorna {"ok": bool, "message": str}."""
    url = get_setting(conn, "the361_url")
    if not url:
        return {"ok": False, "message": "URL di the361 non impostato"}
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        weeks, holidays = _parse(resp.json())
    except Exception as exc:  # rete, JSON non valido, 404...
        return {"ok": False, "message": f"the361 non risponde ({type(exc).__name__})"}
    now = datetime.now().isoformat(timespec="seconds")
    n = 0
    for w in weeks:
        start = w.get("weekOf") or w.get("week_start")
        kind = w.get("type") or w.get("week_type")
        if not start or not kind:
            continue
        place = "Strasburgo" if kind == "plenary" else "Bruxelles" if kind == "plenary-brussels" else None
        conn.execute(
            "INSERT INTO ep_weeks(week_start, week_type, place, raw, fetched_at) VALUES (?,?,?,?,?) "
            "ON CONFLICT(week_start) DO UPDATE SET week_type=excluded.week_type, "
            "place=excluded.place, raw=excluded.raw, fetched_at=excluded.fetched_at",
            (start, kind, place, json.dumps(w), now),
        )
        n += 1
    for h in holidays:
        conn.execute("INSERT INTO ep_holidays(date) VALUES (?) ON CONFLICT DO NOTHING", (h,))
    return {"ok": True, "message": f"{n} settimane aggiornate"}
