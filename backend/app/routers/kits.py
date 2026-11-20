"""Kit, inventario, lista della spesa e promemoria delle ricariche."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..auth import require_user
from ..db import get_db, row, rows

router = APIRouter(prefix="/api", dependencies=[Depends(require_user)])


@router.get("/kits")
def kits(db=Depends(get_db)):
    out = rows(db.execute("SELECT * FROM kits ORDER BY id"))
    for k in out:
        k["items"] = rows(db.execute(
            "SELECT i.*, ki.qty FROM kit_items ki JOIN items i ON i.id = ki.item_id WHERE ki.kit_id = ? ORDER BY i.name",
            (k["id"],)))
    return out


class KitIn(BaseModel):
    name: str
    place: str | None = None
    notes: str | None = None


@router.post("/kits")
def add_kit(body: KitIn, db=Depends(get_db)):
    return {"id": db.insert("INSERT INTO kits(name, place, notes) VALUES (?,?,?)", (body.name, body.place, body.notes))}


@router.put("/kits/{kid}")
def edit_kit(kid: int, body: KitIn, db=Depends(get_db)):
    db.execute("UPDATE kits SET name=?, place=?, notes=? WHERE id=?", (body.name, body.place, body.notes, kid))
    return {"ok": True}


@router.delete("/kits/{kid}")
def del_kit(kid: int, db=Depends(get_db)):
    db.execute("DELETE FROM kits WHERE id = ?", (kid,))
    return {"ok": True}


class KitItem(BaseModel):
    item_id: int
    qty: int = 1


@router.put("/kits/{kid}/items")
def set_kit_item(kid: int, body: KitItem, db=Depends(get_db)):
    db.execute("INSERT INTO kit_items(kit_id, item_id, qty) VALUES (?,?,?) "
               "ON CONFLICT(kit_id, item_id) DO UPDATE SET qty = excluded.qty", (kid, body.item_id, body.qty))
    return {"ok": True}


@router.delete("/kits/{kid}/items/{iid}")
def del_kit_item(kid: int, iid: int, db=Depends(get_db)):
    db.execute("DELETE FROM kit_items WHERE kit_id = ? AND item_id = ?", (kid, iid))
    return {"ok": True}


@router.get("/items")
def items(db=Depends(get_db)):
    out = rows(db.execute("SELECT * FROM items ORDER BY name"))
    for i in out:
        i["kits"] = [r["name"] for r in db.execute(
            "SELECT k.name FROM kit_items ki JOIN kits k ON k.id = ki.kit_id WHERE ki.item_id = ?", (i["id"],))]
    return out


class ItemIn(BaseModel):
    name: str
    owned_qty: int = 0
    consumable: int = 0
    running_low: int = 0
    refill_from: str | None = None
    per_night: int = 0
    notes: str | None = None


@router.post("/items")
def add_item(body: ItemIn, db=Depends(get_db)):
    return {"id": db.insert(
        "INSERT INTO items(name, owned_qty, consumable, running_low, refill_from, per_night, notes) VALUES (?,?,?,?,?,?,?)",
        tuple(body.model_dump().values()))}


@router.put("/items/{iid}")
def edit_item(iid: int, body: ItemIn, db=Depends(get_db)):
    before = row(db.execute("SELECT running_low FROM items WHERE id = ?", (iid,)))
    db.execute("UPDATE items SET name=?, owned_qty=?, consumable=?, running_low=?, refill_from=?, per_night=?, notes=? "
               "WHERE id=?", (*body.model_dump().values(), iid))
    # appena segno "quasi finito" un prodotto che dipende da qualcuno, creo il promemoria per domattina
    if body.running_low and before and not before["running_low"] and body.refill_from:
        due = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0).isoformat(timespec="minutes")
        db.execute("INSERT INTO reminders(title, due_at, kind, item_id, link) VALUES (?,?, 'ricarica', ?, '/kit/spesa')",
                   (f"Chiedi {body.name} a {body.refill_from}", due, iid))
    if not body.running_low:
        db.execute("UPDATE reminders SET done = 1 WHERE item_id = ? AND kind = 'ricarica'", (iid,))
    return {"ok": True}


@router.delete("/items/{iid}")
def del_item(iid: int, db=Depends(get_db)):
    db.execute("DELETE FROM kit_items WHERE item_id = ?", (iid,))
    db.execute("DELETE FROM items WHERE id = ?", (iid,))
    return {"ok": True}


@router.get("/shopping-list")
def shopping(db=Depends(get_db)):
    return rows(db.execute("SELECT * FROM shopping_list"))


@router.get("/reminders")
def reminders(db=Depends(get_db)):
    return rows(db.execute("SELECT * FROM reminders WHERE done = 0 ORDER BY due_at"))


class ReminderIn(BaseModel):
    title: str
    due_at: str
    link: str | None = None


@router.post("/reminders")
def add_reminder(body: ReminderIn, db=Depends(get_db)):
    return {"id": db.insert("INSERT INTO reminders(title, due_at, kind, link) VALUES (?,?, 'libero', ?)",
                            (body.title, body.due_at, body.link))}


@router.post("/reminders/{rid}/done")
def done(rid: int, db=Depends(get_db)):
    db.execute("UPDATE reminders SET done = 1 WHERE id = ?", (rid,))
    return {"ok": True}
