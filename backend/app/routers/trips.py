"""Viaggi, valigia, rientro e modelli di viaggio."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_user
from ..db import get_db, rows
from ..services import day as dayplan, trips as tr

router = APIRouter(prefix="/api", dependencies=[Depends(require_user)])


@router.get("/trips")
def list_trips(db=Depends(get_db)):
    return rows(db.execute(
        "SELECT t.*, tt.name AS template FROM trips t JOIN trip_templates tt ON tt.id = t.template_id "
        "WHERE t.status != 'annullato' ORDER BY t.start_date DESC"))


class TripIn(BaseModel):
    template_id: int
    destination: str
    lat: float
    lon: float
    country: str
    start_date: date
    end_date: date
    city_id: int | None = None
    notes: str | None = None


@router.post("/trips")
def create_trip(body: TripIn, db=Depends(get_db)):
    if body.end_date < body.start_date:
        raise HTTPException(400, "Il ritorno è prima della partenza")
    z = tr.zones(body.country)
    tid = db.insert(
        "INSERT INTO trips(template_id, destination, lat, lon, country, schengen, eu, city_id, start_date, end_date, notes) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (body.template_id, body.destination, body.lat, body.lon, body.country.upper(), z["schengen"], z["eu"],
         body.city_id, body.start_date.isoformat(), body.end_date.isoformat(), body.notes))
    tr.plan(db, tid)
    return {"id": tid}


@router.put("/trips/{tid}")
def edit_trip(tid: int, body: TripIn, db=Depends(get_db)):
    z = tr.zones(body.country)
    db.execute(
        "UPDATE trips SET template_id=?, destination=?, lat=?, lon=?, country=?, schengen=?, eu=?, city_id=?, "
        "start_date=?, end_date=?, notes=? WHERE id=?",
        (body.template_id, body.destination, body.lat, body.lon, body.country.upper(), z["schengen"], z["eu"],
         body.city_id, body.start_date.isoformat(), body.end_date.isoformat(), body.notes, tid))
    tr.plan(db, tid)
    return {"ok": True}


@router.delete("/trips/{tid}")
def cancel_trip(tid: int, db=Depends(get_db)):
    db.execute("UPDATE trips SET status = 'annullato' WHERE id = ?", (tid,))
    return {"ok": True}


@router.get("/trips/{tid}")
def get_trip(tid: int, db=Depends(get_db)):
    t = tr.get(db, tid)
    if not t:
        raise HTTPException(404)
    days = []
    for d in tr.days_of(t):
        o = dayplan.outfits_for(db, d)
        info = dayplan.calendar.day_info(db, d, t)
        w = dayplan.wx.forecast(db, t["lat"], t["lon"], d)
        days.append({**info, "weather_text": dayplan.wx.describe(w),
                     "outfit": next((x for x in o if x["trip_id"] == tid), None)})
    lines = rows(db.execute(
        "SELECT p.*, g.status AS garment_status FROM packing_lines p LEFT JOIN garments g ON g.id = p.garment_id "
        "WHERE p.trip_id = ? ORDER BY p.phase, p.must_have DESC, p.section, p.sort", (tid,)))
    return {**t, "days": days, "packing": lines}


@router.post("/trips/{tid}/plan")
def replan(tid: int, db=Depends(get_db)):
    return tr.plan(db, tid)


class Check(BaseModel):
    checked: bool


@router.patch("/packing/{lid}")
def check(lid: int, body: Check, db=Depends(get_db)):
    db.execute("UPDATE packing_lines SET checked = ? WHERE id = ?", (int(body.checked), lid))
    return {"ok": True}


class Extra(BaseModel):
    phase: str = "andata"
    section: str = "altro"
    label: str
    qty: int = 1


@router.post("/trips/{tid}/packing")
def add_line(tid: int, body: Extra, db=Depends(get_db)):
    return {"id": db.insert("INSERT INTO packing_lines(trip_id, phase, section, label, qty, sort) VALUES (?,?,?,?,?,999)",
                            (tid, body.phase, body.section, body.label, body.qty))}


@router.post("/trips/{tid}/packed")
def packed(tid: int, db=Depends(get_db)):
    """Valigia chiusa: i capi passano a 'in valigia'. Gli oggetti 'sempre' non spuntati bloccano."""
    left = rows(db.execute("SELECT label FROM packing_lines WHERE trip_id = ? AND phase = 'andata' "
                           "AND must_have = 1 AND checked = 0", (tid,)))
    if left:
        raise HTTPException(409, "Mancano: " + ", ".join(r["label"] for r in left))
    return {"moved": tr.mark_packed(db, tid)}


class Back(BaseModel):
    choices: dict[int, str]


@router.post("/trips/{tid}/return")
def come_back(tid: int, body: Back, db=Depends(get_db)):
    tr.come_back(db, tid, body.choices)
    return {"ok": True}


# ---------- modelli ----------

@router.get("/trip-templates")
def templates(db=Depends(get_db)):
    out = rows(db.execute("SELECT * FROM trip_templates ORDER BY id"))
    common = rows(db.execute("SELECT * FROM trip_template_lines WHERE template_id IS NULL ORDER BY id"))
    for t in out:
        t["lines"] = rows(db.execute("SELECT * FROM trip_template_lines WHERE template_id = ? ORDER BY id", (t["id"],)))
    return {"templates": out, "common": common}


class TemplateIn(BaseModel):
    name: str
    from_calendar: int = 0
    spare_outfits: int = 1


@router.post("/trip-templates")
def add_template(body: TemplateIn, db=Depends(get_db)):
    return {"id": db.insert("INSERT INTO trip_templates(name, from_calendar, spare_outfits) VALUES (?,?,?)",
                            (body.name, body.from_calendar, body.spare_outfits))}


@router.put("/trip-templates/{tid}")
def edit_template(tid: int, body: TemplateIn, db=Depends(get_db)):
    db.execute("UPDATE trip_templates SET name=?, from_calendar=?, spare_outfits=? WHERE id=?",
               (body.name, body.from_calendar, body.spare_outfits, tid))
    return {"ok": True}


class LineIn(BaseModel):
    template_id: int | None = None
    section: str
    label: str
    qty: int = 1
    kit_id: int | None = None
    item_id: int | None = None
    applies_if: str = "sempre"
    must_have: int = 0
    on_return: int = 0


@router.post("/trip-template-lines")
def add_tpl_line(body: LineIn, db=Depends(get_db)):
    return {"id": db.insert(
        "INSERT INTO trip_template_lines(template_id, section, label, qty, kit_id, item_id, applies_if, must_have, on_return) "
        "VALUES (?,?,?,?,?,?,?,?,?)", tuple(body.model_dump().values()))}


@router.put("/trip-template-lines/{lid}")
def edit_tpl_line(lid: int, body: LineIn, db=Depends(get_db)):
    db.execute("UPDATE trip_template_lines SET template_id=?, section=?, label=?, qty=?, kit_id=?, item_id=?, "
               "applies_if=?, must_have=?, on_return=? WHERE id=?", (*body.model_dump().values(), lid))
    return {"ok": True}


@router.delete("/trip-template-lines/{lid}")
def del_tpl_line(lid: int, db=Depends(get_db)):
    db.execute("DELETE FROM trip_template_lines WHERE id = ?", (lid,))
    return {"ok": True}


@router.get("/geocode")
def geocode(q: str):
    """Cerca una città con il geocoder gratuito di Open-Meteo."""
    import httpx
    try:
        r = httpx.get("https://geocoding-api.open-meteo.com/v1/search",
                      params={"name": q, "count": 5, "language": "it"}, timeout=10)
        return [{"name": x["name"], "country": x.get("country_code", ""), "admin": x.get("admin1", ""),
                 "lat": x["latitude"], "lon": x["longitude"]} for x in r.json().get("results", [])]
    except Exception:
        return []
