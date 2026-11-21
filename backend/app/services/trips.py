"""Viaggi: giorni, dress code, meteo, outfit e lista della valigia."""
from datetime import date, timedelta

from ..db import get_setting, row, rows
from . import calendar, engine, weather as wx

SCHENGEN = set("AT BE CH CZ DE DK EE ES FI FR GR HR HU IS IT LI LT LU LV MT NL NO PL PT SE SI SK BG RO".split())
EU = set("AT BE BG CY CZ DE DK EE ES FI FR GR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK".split())


def zones(country: str) -> dict:
    c = country.upper()
    return {"schengen": int(c in SCHENGEN), "eu": int(c in EU)}


def days_of(trip: dict) -> list[date]:
    start, end = date.fromisoformat(trip["start_date"]), date.fromisoformat(trip["end_date"])
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def get(conn, trip_id: int) -> dict | None:
    return row(conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)))


def trip_on(conn, d: date) -> dict | None:
    """Il viaggio in corso in quel giorno, se c'è."""
    return row(conn.execute(
        "SELECT * FROM trips WHERE status != 'annullato' AND start_date <= ? AND end_date >= ? "
        "ORDER BY start_date LIMIT 1", (d.isoformat(), d.isoformat())))


def plan(conn, trip_id: int) -> dict:
    """Ricalcola outfit e valigia. Mantiene le spunte già fatte."""
    trip = get(conn, trip_id)
    home = get_setting(conn, "home_city_id", 1)
    days = days_of(trip)
    nights = max(len(days) - 1, 0)

    # outfit, un giorno alla volta
    conn.execute("DELETE FROM outfits WHERE trip_id = ? AND source = 'viaggio' AND status = 'proposto'", (trip_id,))
    reserved, prefer, plan_days, not_clean = set(), set(), [], {}
    extra_cities = [trip["city_id"]] if trip["city_id"] and trip["city_id"] != home else []
    for d in days:
        info = calendar.day_info(conn, d, trip)
        w = wx.forecast(conn, trip["lat"], trip["lon"], d)
        res = engine.suggest(conn, d, home, info["dress_code"], w, extra_city_ids=extra_cities,
                             reserved=frozenset(reserved), prefer=frozenset(prefer), n=1)
        if not res["outfits"]:  # riprovo includendo i capi da lavare o in tintoria
            res = engine.suggest(conn, d, home, info["dress_code"], w, extra_city_ids=extra_cities,
                                 reserved=frozenset(reserved), prefer=frozenset(prefer), n=1,
                                 allowed_status=("pulito", "da_lavare", "tintoria", "valigia"))
        items = res["outfits"][0]["items"] if res["outfits"] else []
        # salvo il giorno anche senza outfit, con cosa manca, così la schermata del viaggio lo dice
        outfit_id = conn.insert(
            "INSERT INTO outfits(date, city_id, trip_id, dress_code, day_type, weather, source, missing) "
            "VALUES (?,?,?,?,?,?, 'viaggio', ?)",
            (d.isoformat(), trip["city_id"], trip_id, info["dress_code"], info["week_label"], _json(w),
             _json(res["missing"])))
        if items:
            for it in items:
                conn.execute("INSERT INTO outfit_items VALUES (?,?)", (outfit_id, it["id"]))
                reserved.add(it["id"])
                prefer.add(it["id"])
        plan_days.append({**info, "weather": w, "weather_text": wx.describe(w), "outfit_id": outfit_id,
                          "items": items, "missing": res["missing"]})

    # capi da mettere in valigia: tutto tranne quello che indosso il primo giorno
    # e quello che è già nella città di destinazione
    worn_first = {i["id"] for i in plan_days[0]["items"]} if plan_days else set()
    packed_ids = []
    for pd in plan_days[1:]:
        for it in pd["items"]:
            if it["id"] not in worn_first and it["id"] not in packed_ids:
                packed_ids.append(it["id"])
    garments = {g["id"]: g for g in rows(conn.execute(
        f"SELECT g.*, c.name AS category FROM garments g JOIN categories c ON c.id = g.category_id "
        f"WHERE g.id IN ({','.join('?' * len(packed_ids + list(worn_first))) or 'NULL'})",
        packed_ids + list(worn_first)))}
    packed = [garments[i] for i in packed_ids if garments[i]["city_id"] != trip["city_id"] or not trip["city_id"]]
    # scorta: camicie o maglie in più, dello stesso registro dei giorni del viaggio
    spare = conn.execute("SELECT spare_outfits FROM trip_templates WHERE id = ?", (trip["template_id"],)).fetchone()
    spare_n = spare["spare_outfits"] if spare else 0
    if spare_n and plan_days:
        formal = sum(1 for p in plan_days if p["dress_code"] == "completo") > len(plan_days) / 2
        taken = {g["id"] for g in packed} | worn_first
        extra = rows(conn.execute(
            "SELECT g.*, c.name AS category FROM garments g JOIN categories c ON c.id = g.category_id "
            "WHERE c.slot = 'top' AND g.status = 'pulito' AND g.archived = 0 AND g.city_id = ? "
            "ORDER BY ABS(g.formality - ?), g.id", (home, 4 if formal else 2)))
        for g in [g for g in extra if g["id"] not in taken][:spare_n]:
            g["name"] = f"{g['name']} (scorta)"
            packed.append(g)
    for g in list(garments.values()):
        if g["status"] in ("da_lavare", "tintoria"):
            not_clean[g["id"]] = {"id": g["id"], "name": g["name"], "status": g["status"]}

    _write_packing(conn, trip, packed, nights)
    return {"trip": trip, "days": plan_days, "packed": [_short(g) for g in packed],
            "not_ready": list(not_clean.values()), "nights": nights}


def _write_packing(conn, trip, packed, nights):
    checked = {(r["phase"], r["label"]) for r in conn.execute(
        "SELECT phase, label FROM packing_lines WHERE trip_id = ? AND checked = 1", (trip["id"],))}
    conn.execute("DELETE FROM packing_lines WHERE trip_id = ?", (trip["id"],))
    lines = []
    lines_tpl = rows(conn.execute(
        "SELECT l.*, k.name AS kit_name FROM trip_template_lines l LEFT JOIN kits k ON k.id = l.kit_id "
        "WHERE l.template_id IS NULL OR l.template_id = ? ORDER BY l.must_have DESC, l.id", (trip["template_id"],)))
    for l in lines_tpl:
        if l["applies_if"] == "fuori_schengen" and trip["schengen"]:
            continue
        if l["applies_if"] == "fuori_ue" and trip["eu"]:
            continue
        lines.append(("andata", l["section"], l["label"], l["qty"], None, l["kit_id"], l["item_id"], l["must_have"]))
        if l["on_return"]:
            lines.append(("ritorno", l["section"], l["label"], l["qty"], None, l["kit_id"], l["item_id"], l["must_have"]))
    for g in packed:
        lines.append(("andata", "vestiti", g["name"], 1, g["id"], None, None, 0))
    if nights:
        for it in conn.execute("SELECT * FROM items WHERE per_night > 0 ORDER BY name"):
            lines.append(("andata", "vestiti", it["name"], (nights + 1) * it["per_night"], None, None, it["id"], 0))
    if packed:
        lines.append(("ritorno", "vestiti", "Tutti i vestiti dall'armadio e dal bagno", 1, None, None, None, 1))
    for i, (phase, section, label, qty, gid, kid, iid, must) in enumerate(lines):
        conn.execute(
            "INSERT INTO packing_lines(trip_id, phase, section, label, qty, garment_id, kit_id, item_id, "
            "must_have, checked, sort) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (trip["id"], phase, section, label, qty, gid, kid, iid, must, int((phase, label) in checked), i))


def mark_packed(conn, trip_id: int) -> int:
    """I capi della valigia passano a 'in valigia'."""
    cur = conn.execute(
        "UPDATE garments SET status = 'valigia' WHERE id IN "
        "(SELECT garment_id FROM packing_lines WHERE trip_id = ? AND phase = 'andata' AND garment_id IS NOT NULL)",
        (trip_id,))
    conn.execute("UPDATE trips SET status = 'in_corso' WHERE id = ?", (trip_id,))
    return cur.rowcount


def come_back(conn, trip_id: int, choices: dict[int, str]) -> None:
    """choices: {garment_id: 'pulito' | 'da_lavare'}. I capi tornano a casa."""
    home = get_setting(conn, "home_city_id", 1)
    for gid, status in choices.items():
        if status not in ("pulito", "da_lavare"):
            continue
        conn.execute("UPDATE garments SET status = ?, city_id = ? WHERE id = ? AND status = 'valigia'",
                     (status, home, gid))
    conn.execute("UPDATE trips SET status = 'rientrato' WHERE id = ?", (trip_id,))


def create_plenary_trips(conn, today: date) -> int:
    """Crea i viaggi a Strasburgo per le plenarie future che non ne hanno ancora uno."""
    cfg = get_setting(conn, "plenary_trip", {"week_types": ["plenary"], "depart_weekday": 0, "return_weekday": 3})
    tpl = conn.execute("SELECT id FROM trip_templates WHERE from_calendar = 1 ORDER BY id LIMIT 1").fetchone()
    city = conn.execute("SELECT * FROM cities WHERE name LIKE 'Strasburgo%'").fetchone()
    if not tpl or not city:
        return 0
    made = 0
    weeks = conn.execute(
        f"SELECT week_start FROM ep_weeks WHERE week_type IN ({','.join('?' * len(cfg['week_types']))}) "
        "AND week_start >= ? AND week_start NOT IN (SELECT ep_week FROM trips WHERE ep_week IS NOT NULL)",
        (*cfg["week_types"], calendar.monday(today).isoformat())).fetchall()
    for w in weeks:
        mon = date.fromisoformat(w["week_start"])
        start = mon + timedelta(days=cfg["depart_weekday"])
        end = mon + timedelta(days=cfg["return_weekday"])
        if end < today:
            continue
        conn.execute(
            "INSERT INTO trips(template_id, destination, lat, lon, country, schengen, eu, city_id, start_date, "
            "end_date, source, ep_week) VALUES (?,?,?,?,?,1,1,?,?,?, 'the361', ?)",
            (tpl["id"], city["name"], city["lat"], city["lon"], city["country"], city["id"],
             start.isoformat(), end.isoformat(), w["week_start"]))
        made += 1
    return made


def _short(g):
    return {"id": g["id"], "name": g["name"], "category": g.get("category"), "status": g["status"],
            "cutout": g.get("cutout")}


def _json(x):
    import json
    return json.dumps(x)
