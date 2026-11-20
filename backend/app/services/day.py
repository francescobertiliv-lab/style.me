"""Il piano di un giorno: dress code, città, meteo, outfit. Lo usano la schermata Domani e la mail serale."""
import json
from datetime import date

from ..db import get_setting, row, rows
from . import calendar, composer, engine, trips, weather as wx


def _city(conn, city_id):
    return row(conn.execute("SELECT * FROM cities WHERE id = ?", (city_id,)))


def calendar_status(conn, d: date) -> dict:
    st = get_setting(conn, "calendar_status", {"ok": True, "message": ""})
    covered = conn.execute("SELECT 1 FROM ep_weeks WHERE week_start >= ?",
                           (calendar.monday(d).isoformat(),)).fetchone()
    if not covered:
        return {"ok": False, "message": "il calendario PE salvato non arriva a questa settimana"}
    return st


def outfits_for(conn, d: date) -> list[dict]:
    out = rows(conn.execute(
        "SELECT * FROM outfits WHERE date = ? AND status != 'scartato' "
        "ORDER BY CASE source WHEN 'manuale' THEN 0 WHEN 'viaggio' THEN 1 ELSE 2 END, id", (d.isoformat(),)))
    for o in out:
        o["items"] = rows(conn.execute(
            "SELECT g.id, g.name, c.name AS category, c.slot, g.color_hex, g.color_family, g.pattern, "
            "g.cutout, g.photo, g.formality FROM outfit_items oi JOIN garments g ON g.id = oi.garment_id "
            "JOIN categories c ON c.id = g.category_id WHERE oi.outfit_id = ? ORDER BY c.sort", (o["id"],)))
    return out


def build(conn, d: date, refresh: bool = False) -> dict:
    """Prepara (o rilegge) il piano del giorno."""
    trip = trips.trip_on(conn, d)
    info = calendar.day_info(conn, d, trip)
    home = get_setting(conn, "home_city_id", 1)
    if trip:
        city_id = trip["city_id"] or home
        lat, lon, city_name = trip["lat"], trip["lon"], trip["destination"]
    else:
        c = _city(conn, home)
        city_id, lat, lon, city_name = home, c["lat"], c["lon"], c["name"]
    w = wx.forecast(conn, lat, lon, d)

    if refresh:
        conn.execute("DELETE FROM outfits WHERE date = ? AND source = 'motore' AND status = 'proposto'",
                     (d.isoformat(),))
    existing = outfits_for(conn, d)
    missing: list[str] = []
    if not existing:
        res = engine.suggest(conn, d, city_id, info["dress_code"], w)
        missing = res["missing"]
        for o in res["outfits"]:
            image = composer.compose(o["items"])
            oid = conn.insert(
                "INSERT INTO outfits(date, city_id, trip_id, dress_code, day_type, weather, source, image, missing) "
                "VALUES (?,?,?,?,?,?, 'motore', ?, ?)",
                (d.isoformat(), city_id, trip["id"] if trip else None, info["dress_code"], info["week_label"],
                 json.dumps(w), image, json.dumps(missing)))
            for it in o["items"]:
                conn.execute("INSERT INTO outfit_items VALUES (?,?)", (oid, it["id"]))
        existing = outfits_for(conn, d)
    else:
        for o in existing:
            if o.get("missing"):
                missing = json.loads(o["missing"])
                break
    cal = calendar_status(conn, d)
    return {
        **info,
        "city": city_name,
        "weather": w,
        "weather_text": wx.describe(w),
        "weather_ok": bool(w.get("ok")),
        "calendar_ok": bool(cal["ok"]),
        "calendar_message": cal.get("message", ""),
        "trip": {"id": trip["id"], "destination": trip["destination"]} if trip else None,
        "outfits": [{"id": o["id"], "image": o["image"], "items": o["items"], "rating": o["rating"],
                     "status": o["status"], "source": o["source"]} for o in existing],
        "missing": missing,
    }
