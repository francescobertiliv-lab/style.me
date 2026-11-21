"""Guardaroba: capi, foto, categorie, città, colori, sarta."""
import json
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from .. import config
from ..auth import require_user
from ..db import get_db, get_setting, row, rows
from ..services import images, storage

router = APIRouter(prefix="/api", dependencies=[Depends(require_user)])

STATUSES = ("pulito", "da_lavare", "tintoria", "valigia", "sarta")


@router.get("/media/{path:path}")
def media(path: str):
    if ".." in path:
        raise HTTPException(400)
    url = storage.signed_url(path)
    if url:
        return RedirectResponse(url)
    full = config.PHOTOS_DIR / path
    if not full.exists():
        raise HTTPException(404)
    return FileResponse(full)


@router.get("/categories")
def categories(db=Depends(get_db)):
    return rows(db.execute("SELECT * FROM categories ORDER BY sort, name"))


class CategoryIn(BaseModel):
    name: str
    slot: str
    repeat_days: int | None = None
    default_formality: int = 3
    default_weight: int = 2
    sort: int = 0


@router.post("/categories")
def add_category(body: CategoryIn, db=Depends(get_db)):
    cid = db.insert("INSERT INTO categories(name, slot, repeat_days, default_formality, default_weight, sort) "
                    "VALUES (?,?,?,?,?,?)", tuple(body.model_dump().values()))
    return {"id": cid}


@router.put("/categories/{cid}")
def edit_category(cid: int, body: CategoryIn, db=Depends(get_db)):
    db.execute("UPDATE categories SET name=?, slot=?, repeat_days=?, default_formality=?, default_weight=?, sort=? "
               "WHERE id=?", (*body.model_dump().values(), cid))
    return {"ok": True}


@router.get("/cities")
def cities(db=Depends(get_db)):
    return rows(db.execute("SELECT * FROM cities ORDER BY is_home DESC, name"))


class CityIn(BaseModel):
    name: str
    lat: float
    lon: float
    country: str


@router.post("/cities")
def add_city(body: CityIn, db=Depends(get_db)):
    return {"id": db.insert("INSERT INTO cities(name, lat, lon, country) VALUES (?,?,?,?)",
                            (body.name, body.lat, body.lon, body.country.upper()))}


@router.get("/color-families")
def color_families(db=Depends(get_db)):
    return rows(db.execute("SELECT * FROM color_families ORDER BY tone, depth, name"))


# ---------- capi ----------

GARMENT_SQL = """
  SELECT g.*, c.name AS category, c.slot,
         (SELECT MAX(o.date) FROM outfits o JOIN outfit_items oi ON oi.outfit_id = o.id
          WHERE oi.garment_id = g.id AND o.status = 'indossato') AS last_worn
  FROM garments g JOIN categories c ON c.id = g.category_id
"""


@router.get("/garments")
def list_garments(status: str | None = None, city_id: int | None = None, slot: str | None = None,
                  archived: int = 0, to_review: int | None = None, db=Depends(get_db)):
    q, p = GARMENT_SQL + " WHERE g.archived = ?", [archived]
    if to_review is not None:
        q, p = q + " AND g.to_review = ?", p + [to_review]
    if status:
        q, p = q + " AND g.status = ?", p + [status]
    if city_id:
        q, p = q + " AND g.city_id = ?", p + [city_id]
    if slot:
        q, p = q + " AND c.slot = ?", p + [slot]
    return rows(db.execute(q + " ORDER BY c.sort, g.color_family, g.name", p))


@router.post("/garments/photo")
async def upload_photo(photo: UploadFile = File(...), cutout: UploadFile | None = File(None), db=Depends(get_db)):
    """Primo passo del nuovo capo: salva la foto e propone gli attributi."""
    saved = images.save_upload(await photo.read(), await cutout.read() if cutout else None)
    proposal = images.propose_attributes(db, saved["image"])
    return {"photo": saved["photo"], "cutout": saved["cutout"], "proposal": proposal}


@router.post("/garments/quick")
async def quick_add(photo: UploadFile = File(...), cutout: UploadFile | None = File(None),
                    category_id: int = Form(...), city_id: int | None = Form(None), db=Depends(get_db)):
    """Importazione in serie: una foto, la categoria scelta prima, il resto lo propongo io.
    Il capo entra subito nel guardaroba e finisce nella coda "Da sistemare"."""
    cat = row(db.execute("SELECT * FROM categories WHERE id = ?", (category_id,)))
    if not cat:
        raise HTTPException(400, "Categoria sconosciuta")
    saved = images.save_upload(await photo.read(), await cutout.read() if cutout else None)
    p = images.propose_attributes(db, saved["image"])
    base = f"{cat['name'].capitalize()} {p['color_family']}"
    same = db.execute("SELECT COUNT(*) AS n FROM garments WHERE name = ? OR name LIKE ?",
                      (base, base + " %")).fetchone()["n"]
    name = f"{base} {same + 1}" if same else base
    city = city_id or get_setting(db, "home_city_id", 1)
    gid = db.insert(
        f"INSERT INTO garments({COLS}, to_review) VALUES ({','.join('?' * 22)})",
        (name, category_id, None, p["color_hex"], p["color_family"], json.dumps(p["colors"]), p["pattern"],
         cat["default_formality"], cat["default_weight"], None, 1, 0, None, None, None, None,
         "pulito", city, saved["photo"], saved["cutout"], None, 1))
    return {"id": gid, "name": name, "cutout": saved["cutout"]}


class GarmentIn(BaseModel):
    name: str
    category_id: int
    color_hex: str
    color_family: str
    colors: list[dict] = []
    pattern: str = "tinta unita"
    formality: int
    weight: int
    material: str | None = None
    rain_ok: int = 1
    rain_gear: int = 0
    set_key: str | None = None
    size: str | None = None
    brand: str | None = None
    price_eur: float | None = None
    bought_on: str | None = None
    status: str = "pulito"
    city_id: int
    photo: str
    cutout: str | None = None
    notes: str | None = None


def _garment_values(b: GarmentIn):
    if b.status not in STATUSES:
        raise HTTPException(400, "Stato non valido")
    rain_ok = 0 if (b.material or "").lower().startswith("scamosc") else b.rain_ok
    return (b.name, b.category_id, b.set_key or None, b.color_hex, b.color_family, json.dumps(b.colors), b.pattern,
            b.formality, b.weight, b.material, rain_ok, b.rain_gear, b.size, b.brand, b.price_eur, b.bought_on,
            b.status, b.city_id, b.photo, b.cutout, b.notes)


COLS = ("name, category_id, set_key, color_hex, color_family, colors, pattern, formality, weight, material, "
        "rain_ok, rain_gear, size, brand, price_eur, bought_on, status, city_id, photo, cutout, notes")


@router.post("/garments")
def create_garment(body: GarmentIn, wishlist_id: int | None = None, db=Depends(get_db)):
    gid = db.insert(f"INSERT INTO garments({COLS}) VALUES ({','.join('?' * 21)})", _garment_values(body))
    if wishlist_id:
        db.execute("UPDATE wishlist SET status = 'comprato', garment_id = ? WHERE id = ?", (gid, wishlist_id))
    return {"id": gid}


@router.get("/garments/{gid}")
def get_garment(gid: int, db=Depends(get_db)):
    g = row(db.execute(GARMENT_SQL + " WHERE g.id = ?", (gid,)))
    if not g:
        raise HTTPException(404)
    g["colors"] = json.loads(g["colors"] or "[]")
    g["worn"] = rows(db.execute(
        "SELECT o.date, o.rating FROM outfits o JOIN outfit_items oi ON oi.outfit_id = o.id "
        "WHERE oi.garment_id = ? AND o.status = 'indossato' ORDER BY o.date DESC LIMIT 20", (gid,)))
    g["tailor"] = rows(db.execute("SELECT * FROM tailor_jobs WHERE garment_id = ? ORDER BY id DESC", (gid,)))
    return g


@router.put("/garments/{gid}")
def update_garment(gid: int, body: GarmentIn, db=Depends(get_db)):
    sets = ", ".join(f"{c.strip()} = ?" for c in COLS.split(","))
    db.execute(f"UPDATE garments SET {sets}, to_review = 0 WHERE id = ?", (*_garment_values(body), gid))
    return {"ok": True}


@router.post("/garments/{gid}/reviewed")
def reviewed(gid: int, db=Depends(get_db)):
    """Controllato: va bene com'è."""
    db.execute("UPDATE garments SET to_review = 0 WHERE id = ?", (gid,))
    return {"ok": True}


class Quick(BaseModel):
    status: str | None = None
    city_id: int | None = None


@router.patch("/garments/{gid}")
def quick_update(gid: int, body: Quick, db=Depends(get_db)):
    """Stato e città con un tocco."""
    if body.status:
        if body.status not in STATUSES:
            raise HTTPException(400, "Stato non valido")
        db.execute("UPDATE garments SET status = ? WHERE id = ?", (body.status, gid))
    if body.city_id:
        db.execute("UPDATE garments SET city_id = ? WHERE id = ?", (body.city_id, gid))
    return {"ok": True}


@router.delete("/garments/{gid}")
def archive_garment(gid: int, db=Depends(get_db)):
    db.execute("UPDATE garments SET archived = 1 WHERE id = ?", (gid,))
    return {"ok": True}


# ---------- sarta ----------

class TailorIn(BaseModel):
    garment_id: int
    kind: str
    note: str | None = None


@router.get("/tailor")
def tailor_list(db=Depends(get_db)):
    return rows(db.execute(
        "SELECT t.*, g.name AS garment, g.cutout FROM tailor_jobs t JOIN garments g ON g.id = t.garment_id "
        "ORDER BY CASE t.status WHEN 'da_portare' THEN 0 WHEN 'dalla_sarta' THEN 1 ELSE 2 END, t.id DESC"))


@router.post("/tailor")
def tailor_add(body: TailorIn, db=Depends(get_db)):
    if body.kind not in ("orlo", "spalle", "lunghezza_giacca", "stringere", "altro"):
        raise HTTPException(400, "Intervento non valido")
    return {"id": db.insert("INSERT INTO tailor_jobs(garment_id, kind, note) VALUES (?,?,?)",
                            (body.garment_id, body.kind, body.note))}


class TailorStatus(BaseModel):
    status: str
    cost_eur: float | None = None


@router.patch("/tailor/{tid}")
def tailor_status(tid: int, body: TailorStatus, db=Depends(get_db)):
    job = row(db.execute("SELECT * FROM tailor_jobs WHERE id = ?", (tid,)))
    if not job or body.status not in ("da_portare", "dalla_sarta", "fatto"):
        raise HTTPException(400)
    today = date.today().isoformat()
    if body.status == "dalla_sarta":
        db.execute("UPDATE tailor_jobs SET status = ?, brought_on = ? WHERE id = ?", (body.status, today, tid))
        db.execute("UPDATE garments SET status = 'sarta' WHERE id = ?", (job["garment_id"],))
    elif body.status == "fatto":
        db.execute("UPDATE tailor_jobs SET status = ?, picked_up_on = ?, cost_eur = ? WHERE id = ?",
                   (body.status, today, body.cost_eur, tid))
        still = db.execute("SELECT 1 FROM tailor_jobs WHERE garment_id = ? AND status = 'dalla_sarta'",
                           (job["garment_id"],)).fetchone()
        if not still:
            db.execute("UPDATE garments SET status = 'pulito' WHERE id = ? AND status = 'sarta'", (job["garment_id"],))
    else:
        db.execute("UPDATE tailor_jobs SET status = ? WHERE id = ?", (body.status, tid))
    return {"ok": True}
