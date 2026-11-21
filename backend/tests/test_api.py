"""Giro completo delle API su SQLite: login, capi, domani, viaggio, kit, stile, cron."""
import io
import os
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app import auth, config, main
from app.services import jobs, weather


PG_URL = os.environ.get("TEST_PG_URL")


@pytest.fixture(params=["sqlite"] + (["postgres"] if PG_URL else []))
def client(request, tmp_path, monkeypatch):
    if request.param == "sqlite":
        monkeypatch.setattr(config, "DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    else:
        import psycopg
        monkeypatch.setattr(config, "DATABASE_URL", PG_URL)
        monkeypatch.setattr(config, "DB_SCHEMA", "test_api")
        with psycopg.connect(PG_URL, autocommit=True) as raw:
            raw.execute('DROP SCHEMA IF EXISTS "test_api" CASCADE')
    monkeypatch.setattr(config, "PHOTOS_DIR", tmp_path / "photos")
    monkeypatch.setattr(config, "PASSWORD_HASH", auth.hash_password("segreta"))
    monkeypatch.setattr(config, "CRON_SECRET", "cron")
    monkeypatch.setattr(main, "_ready", False)
    # niente rete nei test: meteo finto
    monkeypatch.setattr(weather, "forecast", lambda conn, lat, lon, day, timeout=10: {
        "ok": True, "tmax": 14, "tmin": 6, "rain_mm": 0, "rain_prob": 20, "wind": 10, "code": 3, "summary": "nuvoloso"})
    c = TestClient(main.app)
    assert c.get("/api/day/tomorrow").status_code == 401
    me = c.get("/api/auth/me").json()
    assert me == {"logged_in": False, "needs_setup": False, "onboarded": False}
    assert c.post("/api/auth/login", json={"password": "no"}).status_code == 401
    assert c.post("/api/auth/login", json={"password": "segreta"}).status_code == 200
    return c


def photo(color, size=(400, 600)):
    im = Image.new("RGB", size, "white")
    ImageDraw.Draw(im).rectangle([60, 60, size[0] - 60, size[1] - 60], fill=color)
    buf = io.BytesIO()
    im.save(buf, "JPEG")
    return buf.getvalue()


def add(c, name, category, color, formality, set_key=None, **kw):
    up = c.post("/api/garments/photo", files={"photo": ("p.jpg", photo(color), "image/jpeg")}).json()
    cats = {x["name"]: x["id"] for x in c.get("/api/categories").json()}
    p = up["proposal"]
    body = {"name": name, "category_id": cats[category], "color_hex": p["color_hex"],
            "color_family": kw.pop("family", p["color_family"]), "formality": formality, "weight": 2,
            "set_key": set_key, "city_id": 1, "photo": up["photo"], "cutout": up["cutout"], **kw}
    r = c.post("/api/garments", json=body)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def wardrobe(c):
    add(c, "Giacca navy", "giacca completo", (30, 40, 64), 5, "navy")
    add(c, "Pantalone navy", "pantalone completo", (30, 40, 64), 5, "navy")
    add(c, "Camicia bianca", "camicia", (244, 244, 240), 4)
    add(c, "Camicia azzurra", "camicia", (175, 200, 230), 4)
    add(c, "Cravatta bordeaux", "cravatta", (106, 27, 43), 5)
    add(c, "Oxford marroni", "scarpe formali", (91, 58, 36), 5)
    add(c, "Chino beige", "chino", (214, 195, 163), 3)
    add(c, "Jeans scuri", "jeans", (44, 59, 87), 2)
    add(c, "Polo bianca", "polo", (244, 244, 240), 2)
    add(c, "T-shirt navy", "t-shirt", (30, 40, 64), 1)
    add(c, "Sneakers bianche", "sneakers", (244, 244, 240), 1)
    add(c, "Mocassini", "mocassini", (91, 58, 36), 3, material="scamosciato")
    add(c, "Cappotto cammello", "cappotto", (190, 148, 102), 4)


def test_full_flow(client):
    c = client
    wardrobe(c)
    assert c.get("/api/garments").json()[0]["category"]

    plan = c.get("/api/day/tomorrow").json()
    assert plan["outfits"], plan
    first = plan["outfits"][0]
    assert first["image"] and c.get(f"/api/media/{first['image']}").status_code == 200
    assert any(i["slot"] == "capospalla" for i in first["items"])  # 14 gradi: serve il cappotto

    c.put(f"/api/day/{plan['date']}/override", json={"dress_code": "informale"})
    plan2 = c.get("/api/day/tomorrow?refresh=1").json()
    assert plan2["dress_code"] == "informale" and plan2["overridden"]
    assert not any(i["slot"] == "cravatta" for o in plan2["outfits"] for i in o["items"])

    # cambio un pezzo: le alternative rispettano le regole e l'outfit diventa la mia scelta
    o0 = plan2["outfits"][0]
    top = next(i for i in o0["items"] if i["slot"] == "top")
    opts = c.get(f"/api/outfits/{o0['id']}/options?slot=top").json()
    assert opts["current"][0]["id"] == top["id"]
    assert all(o[0]["id"] != top["id"] for o in opts["options"])
    if opts["options"]:
        new = opts["options"][0][0]["id"]
        assert c.post(f"/api/outfits/{o0['id']}/swap", json={"remove_ids": [top["id"]], "add_ids": [new]}).status_code == 200
        plan3 = c.get("/api/day/tomorrow").json()
        assert len(plan3["outfits"]) == 1 and new in {i["id"] for i in plan3["outfits"][0]["items"]}
        assert plan3["chosen"] and plan3["outfits"][0]["source"] == "manuale"
        # ci ripenso: tornano le altre proposte
        c.post(f"/api/outfits/{o0['id']}/unchoose")
        plan4 = c.get("/api/day/tomorrow").json()
        assert not plan4["chosen"] and len(plan4["outfits"]) == len(plan2["outfits"])
        # Ricalcola butta anche la scelta a mano non indossata e rifà le proposte
        plan5 = c.get("/api/day/tomorrow?refresh=1").json()
        assert all(o["source"] == "motore" for o in plan5["outfits"]) and not plan5["chosen"]
        plan2 = plan5

    oid = plan2["outfits"][0]["id"]
    assert c.post(f"/api/outfits/{oid}/worn").status_code == 200
    assert c.post(f"/api/outfits/{oid}/rate", json={"rating": 1}).status_code == 200

    # viaggio fuori UE di 3 notti
    start = date.today() + timedelta(days=5)
    t = c.post("/api/trips", json={"template_id": 3, "destination": "Londra", "lat": 51.5, "lon": -0.12,
                                   "country": "GB", "start_date": start.isoformat(),
                                   "end_date": (start + timedelta(days=3)).isoformat()}).json()
    trip = c.get(f"/api/trips/{t['id']}").json()
    labels = [p["label"] for p in trip["packing"]]
    assert "Passaporto" in labels and "Adattatore per le prese" in labels
    socks = next(p for p in trip["packing"] if p["label"] == "calze")
    assert socks["qty"] == 4
    assert len(trip["days"]) == 4
    # gli oggetti "sempre" bloccano la chiusura della valigia
    assert c.post(f"/api/trips/{t['id']}/packed").status_code == 409
    for p in trip["packing"]:
        c.patch(f"/api/packing/{p['id']}", json={"checked": True})
    assert c.post(f"/api/trips/{t['id']}/packed").status_code == 200
    packed = [p["garment_id"] for p in trip["packing"] if p["garment_id"]]
    if packed:
        assert c.get(f"/api/garments/{packed[0]}").json()["status"] == "valigia"
        c.post(f"/api/trips/{t['id']}/return", json={"choices": {str(packed[0]): "da_lavare"}})
        assert c.get(f"/api/garments/{packed[0]}").json()["status"] == "da_lavare"

    # kit e lista della spesa
    shop = c.get("/api/shopping-list").json()
    assert any(s["name"] == "pettine" for s in shop)
    items = {i["name"]: i for i in c.get("/api/items").json()}
    p = items["pastiglie"]
    p.update(running_low=1, refill_from="la mamma")
    body = {k: p[k] for k in ("name", "owned_qty", "consumable", "running_low", "refill_from", "per_night", "notes")}
    c.put(f"/api/items/{p['id']}", json=body)
    assert any("la mamma" in r["title"] for r in c.get("/api/reminders").json())

    # sarta: il capo esce dagli outfit
    chino = next(g for g in c.get("/api/garments").json() if g["name"] == "Chino beige")
    job = c.post("/api/tailor", json={"garment_id": chino["id"], "kind": "orlo", "note": "tocca appena la scarpa"}).json()
    c.patch(f"/api/tailor/{job['id']}", json={"status": "dalla_sarta"})
    assert c.get(f"/api/garments/{chino['id']}").json()["status"] == "sarta"
    c.patch(f"/api/tailor/{job['id']}", json={"status": "fatto"})
    assert c.get(f"/api/garments/{chino['id']}").json()["status"] == "pulito"

    # stile
    an = c.get("/api/analysis").json()
    assert an["chart"] and an["missing"]
    sug = c.get("/api/suggestions").json()["items"]
    for s in sug:
        assert len(s["outfits"]) >= 3 and "http" not in s["description"]
    tr = c.post("/api/try-on", data={"category": "overshirt", "color_family": "ruggine"}).json()
    assert "outfits" in tr

    # cron: senza segreto no, con il segreto la sera manda (qui senza mail configurata: nessun errore)
    assert c.get("/api/cron/tick").status_code == 401  # con CRON_SECRET impostato
    r = c.get("/api/cron/tick", headers={"Authorization": "Bearer cron"})
    assert r.status_code == 200 and "calendar" in r.json()


def test_evening_once(client, monkeypatch):
    wardrobe(client)
    from app import db
    with db.session() as conn:
        evening = datetime.combine(date.today(), datetime.min.time()).replace(hour=20, minute=35)
        first = jobs.tick(conn, evening)
        second = jobs.tick(conn, evening + timedelta(minutes=10))
        assert "evening" in first and "evening" not in second
        log = conn.execute("SELECT body FROM notification_log WHERE kind = 'sera'").fetchone()
        assert "Outfit:" in log["body"]


def test_first_run_setup(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATABASE_URL", f"sqlite:///{tmp_path / 'first.db'}")
    monkeypatch.setattr(config, "PHOTOS_DIR", tmp_path / "photos")
    monkeypatch.setattr(config, "PASSWORD_HASH", "")
    monkeypatch.setattr(main, "_ready", False)
    c = TestClient(main.app)
    assert c.get("/api/auth/me").json()["needs_setup"] is True
    assert c.post("/api/auth/setup", json={"password": "corta"}).status_code == 400
    assert c.post("/api/auth/setup", json={"password": "lunga-abbastanza"}).status_code == 200
    assert c.post("/api/auth/setup", json={"password": "un-altra-ancora"}).status_code == 409
    assert c.get("/api/settings").status_code == 200  # già dentro dopo il setup
    c.put("/api/settings", json={"mail_to": "me@example.com", "onboarded": True})
    c.put("/api/settings/resend-key", json={"key": "re_x"})
    assert "re_x" not in c.get("/api/settings").text
    st = c.get("/api/status").json()
    assert st["mail_to"] == "me@example.com" and st["mail"] is False  # manca il mittente
    c2 = TestClient(main.app)
    assert c2.post("/api/auth/login", json={"password": "lunga-abbastanza"}).status_code == 200
