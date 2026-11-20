"""Domani, storico degli outfit, giorni forzati."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_user
from ..db import get_db, rows
from ..services import composer, day as dayplan, jobs

router = APIRouter(prefix="/api", dependencies=[Depends(require_user)])


@router.get("/day/tomorrow")
def tomorrow(refresh: int = 0, db=Depends(get_db)):
    d = jobs.now_local(db).date() + timedelta(days=1)
    return dayplan.build(db, d, refresh=bool(refresh))


@router.get("/day/{d}")
def one_day(d: date, refresh: int = 0, db=Depends(get_db)):
    return dayplan.build(db, d, refresh=bool(refresh))


class Override(BaseModel):
    dress_code: str | None
    note: str | None = None


@router.put("/day/{d}/override")
def override(d: date, body: Override, db=Depends(get_db)):
    db.execute("DELETE FROM day_overrides WHERE date = ?", (d.isoformat(),))
    if body.dress_code:
        if body.dress_code not in ("completo", "informale", "libero"):
            raise HTTPException(400, "Dress code non valido")
        db.execute("INSERT INTO day_overrides(date, dress_code, note) VALUES (?,?,?)",
                   (d.isoformat(), body.dress_code, body.note))
    return {"ok": True}


class Rating(BaseModel):
    rating: int


@router.post("/outfits/{oid}/rate")
def rate(oid: int, body: Rating, db=Depends(get_db)):
    if body.rating not in (-1, 1):
        raise HTTPException(400)
    db.execute("UPDATE outfits SET rating = ? WHERE id = ?", (body.rating, oid))
    return {"ok": True}


@router.post("/outfits/{oid}/worn")
def worn(oid: int, db=Depends(get_db)):
    """L'ho messo davvero: entra nello storico, le alternative dello stesso giorno escono."""
    o = db.execute("SELECT date FROM outfits WHERE id = ?", (oid,)).fetchone()
    if not o:
        raise HTTPException(404)
    db.execute("UPDATE outfits SET status = 'scartato' WHERE date = ? AND id != ? AND status = 'proposto'",
               (o["date"], oid))
    db.execute("UPDATE outfits SET status = 'indossato' WHERE id = ?", (oid,))
    return {"ok": True}


class Manual(BaseModel):
    date: date
    garment_ids: list[int]
    worn: bool = True


@router.post("/outfits")
def manual(body: Manual, db=Depends(get_db)):
    """Outfit scelto a mano (o cambiato un capo della proposta)."""
    items = rows(db.execute(
        f"SELECT g.id, g.cutout, c.slot FROM garments g JOIN categories c ON c.id = g.category_id "
        f"WHERE g.id IN ({','.join('?' * len(body.garment_ids)) or 'NULL'})", body.garment_ids))
    if not items:
        raise HTTPException(400, "Nessun capo")
    info = dayplan.calendar.day_info(db, body.date)
    if body.worn:
        db.execute("UPDATE outfits SET status = 'scartato' WHERE date = ? AND status = 'proposto'",
                   (body.date.isoformat(),))
    oid = db.insert(
        "INSERT INTO outfits(date, dress_code, day_type, source, status, image) VALUES (?,?,?, 'manuale', ?, ?)",
        (body.date.isoformat(), info["dress_code"], info["week_label"],
         "indossato" if body.worn else "proposto", composer.compose(items)))
    for it in items:
        db.execute("INSERT INTO outfit_items VALUES (?,?)", (oid, it["id"]))
    return {"id": oid}


@router.get("/history")
def history(start: date | None = None, end: date | None = None, db=Depends(get_db)):
    end = end or date.today()
    start = start or end - timedelta(days=60)
    out = rows(db.execute(
        "SELECT id, date, dress_code, day_type, rating, image FROM outfits "
        "WHERE status = 'indossato' AND date BETWEEN ? AND ? ORDER BY date DESC",
        (start.isoformat(), end.isoformat())))
    for o in out:
        o["items"] = rows(db.execute(
            "SELECT g.id, g.name, g.color_hex FROM outfit_items oi JOIN garments g ON g.id = oi.garment_id "
            "WHERE oi.outfit_id = ?", (o["id"],)))
    return out
