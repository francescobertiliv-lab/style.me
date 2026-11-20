"""Profilo, palette, regole di stile, analisi, suggerimenti, prova, lista desideri."""
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..auth import require_user
from ..db import get_db, row, rows
from ..services import images, shopping

router = APIRouter(prefix="/api", dependencies=[Depends(require_user)])


@router.get("/profile")
def profile(db=Depends(get_db)):
    p = row(db.execute("SELECT * FROM profile WHERE id = 1"))
    p["sizes"] = json.loads(p["sizes"] or "{}")
    return p


class ProfileIn(BaseModel):
    height_cm: int | None = None
    build: str | None = None
    coloring: str | None = None
    sizes: dict = {}
    fit_notes: str | None = None
    budget_min: int | None = None
    budget_max: int | None = None


@router.put("/profile")
def save_profile(body: ProfileIn, db=Depends(get_db)):
    db.execute("UPDATE profile SET height_cm=?, build=?, coloring=?, sizes=?, fit_notes=?, budget_min=?, budget_max=? "
               "WHERE id = 1", (body.height_cm, body.build, body.coloring, json.dumps(body.sizes), body.fit_notes,
                                body.budget_min, body.budget_max))
    return {"ok": True}


@router.get("/palettes")
def palettes(db=Depends(get_db)):
    out = rows(db.execute("SELECT * FROM palettes ORDER BY active DESC, id DESC"))
    for p in out:
        p["colors"] = rows(db.execute(
            "SELECT pc.id, pc.family, pc.role, f.hex FROM palette_colors pc "
            "JOIN color_families f ON f.name = pc.family WHERE pc.palette_id = ? ORDER BY pc.role, pc.family", (p["id"],)))
    return out


class PaletteIn(BaseModel):
    name: str
    source: str = "consulente"
    colors: list[dict]  # [{family, role}]


@router.post("/palettes")
def new_palette(body: PaletteIn, db=Depends(get_db)):
    """La palette della consulente sostituisce quella stimata (la vecchia resta in archivio)."""
    db.execute("UPDATE palettes SET active = 0")
    pid = db.insert("INSERT INTO palettes(name, source, active) VALUES (?,?,1)", (body.name, body.source))
    for c in body.colors:
        db.execute("INSERT INTO palette_colors(palette_id, family, role) VALUES (?,?,?)", (pid, c["family"], c["role"]))
    return {"id": pid}


@router.post("/palettes/{pid}/activate")
def activate(pid: int, db=Depends(get_db)):
    db.execute("UPDATE palettes SET active = 0")
    db.execute("UPDATE palettes SET active = 1 WHERE id = ?", (pid,))
    return {"ok": True}


class PaletteColor(BaseModel):
    family: str
    role: str


@router.put("/palettes/{pid}/colors")
def set_color(pid: int, body: PaletteColor, db=Depends(get_db)):
    db.execute("DELETE FROM palette_colors WHERE palette_id = ? AND family = ?", (pid, body.family))
    if body.role in ("base", "da_aggiungere", "evita"):
        db.execute("INSERT INTO palette_colors(palette_id, family, role) VALUES (?,?,?)", (pid, body.family, body.role))
    return {"ok": True}


@router.get("/style-rules")
def style_rules(db=Depends(get_db)):
    out = rows(db.execute("SELECT * FROM style_rules ORDER BY id"))
    for r in out:
        r["params"] = json.loads(r["params"])
    return out


class RuleIn(BaseModel):
    kind: str
    params: dict
    description: str
    active: int = 1


@router.post("/style-rules")
def add_rule(body: RuleIn, db=Depends(get_db)):
    return {"id": db.insert("INSERT INTO style_rules(kind, params, description, active) VALUES (?,?,?,?)",
                            (body.kind, json.dumps(body.params), body.description, body.active))}


@router.put("/style-rules/{rid}")
def edit_rule(rid: int, body: RuleIn, db=Depends(get_db)):
    db.execute("UPDATE style_rules SET kind=?, params=?, description=?, active=? WHERE id=?",
               (body.kind, json.dumps(body.params), body.description, body.active, rid))
    return {"ok": True}


@router.get("/analysis")
def analysis(db=Depends(get_db)):
    return shopping.analysis(db)


@router.get("/suggestions")
def suggestions(db=Depends(get_db)):
    p = profile(db)
    return {"sizes": p["sizes"], "items": shopping.suggestions(db)}


@router.post("/try-on")
async def try_on(category: str = Form(...), photo: UploadFile | None = File(None),
                 cutout: UploadFile | None = File(None), color_family: str | None = Form(None),
                 url: str | None = Form(None), save: int = Form(0), db=Depends(get_db)):
    """Prova prima di comprare: foto (o colore) del capo del negozio, abbinato ai miei."""
    if not db.execute("SELECT 1 FROM categories WHERE name = ?", (category,)).fetchone():
        raise HTTPException(400, "Categoria sconosciuta")
    saved = None
    if photo:
        saved = images.save_upload(await photo.read(), await cutout.read() if cutout else None, kind="wish")
        color_family = color_family or images.propose_attributes(db, saved["image"])["color_family"]
    if not color_family:
        raise HTTPException(400, "Serve una foto o un colore")
    piece = shopping.virtual_piece(db, category, color_family)
    if saved:
        piece["cutout"] = saved["cutout"]
    combos = shopping.outfits_with(db, piece, limit=6)
    wid = None
    if save:
        cat = db.execute("SELECT id FROM categories WHERE name = ?", (category,)).fetchone()
        wid = db.insert("INSERT INTO wishlist(description, category_id, color_family, url, image, cutout, status) "
                        "VALUES (?,?,?,?,?,?, 'desiderato')",
                        (f"{category} {color_family}", cat["id"], color_family, url,
                         saved["photo"] if saved else None, saved["cutout"] if saved else None))
    return {"piece": shopping.engine._public(piece), "outfits": combos, "wishlist_id": wid,
            "verdict": "Si abbina con almeno 3 capi che hai" if len(combos) >= 3 else
                       f"Fa solo {len(combos)} outfit con quello che hai"}


@router.get("/wishlist")
def wishlist(db=Depends(get_db)):
    return rows(db.execute("SELECT w.*, c.name AS category FROM wishlist w LEFT JOIN categories c ON c.id = w.category_id "
                           "WHERE w.status IN ('idea','desiderato') ORDER BY w.id DESC"))


class WishIn(BaseModel):
    description: str
    category_id: int | None = None
    color_family: str | None = None
    url: str | None = None
    price_eur: float | None = None
    status: str = "idea"


@router.post("/wishlist")
def add_wish(body: WishIn, db=Depends(get_db)):
    return {"id": db.insert("INSERT INTO wishlist(description, category_id, color_family, url, price_eur, status) "
                            "VALUES (?,?,?,?,?,?)", tuple(body.model_dump().values()))}


@router.delete("/wishlist/{wid}")
def drop_wish(wid: int, db=Depends(get_db)):
    db.execute("UPDATE wishlist SET status = 'scartato' WHERE id = ?", (wid,))
    return {"ok": True}
