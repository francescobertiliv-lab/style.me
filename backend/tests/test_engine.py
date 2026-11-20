from datetime import date

import pytest

from app import db
from app.services import calendar, engine


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "t.db"
    db.init_db(path)
    c = db.connect(path)
    yield c
    c.close()


def cat(conn, name):
    return conn.execute("SELECT id FROM categories WHERE name=?", (name,)).fetchone()[0]


def add(conn, name, category, family, formality, weight=2, set_key=None, status="pulito",
        city=1, rain_ok=1, rain_gear=0, pattern="tinta unita"):
    hexc = conn.execute("SELECT hex FROM color_families WHERE name=?", (family,)).fetchone()[0]
    cur = conn.execute(
        "INSERT INTO garments(name, category_id, set_key, color_hex, color_family, pattern, formality, weight,"
        " rain_ok, rain_gear, status, city_id, photo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'x.jpg')",
        (name, cat(conn, category), set_key, hexc, family, pattern, formality, weight, rain_ok, rain_gear, status, city),
    )
    return cur.lastrowid


SUNNY = {"ok": True, "tmax": 18, "tmin": 10, "rain_mm": 0, "rain_prob": 10, "code": 1, "summary": "sereno"}
RAINY = {"ok": True, "tmax": 9, "tmin": 4, "rain_mm": 6, "rain_prob": 90, "code": 63, "summary": "pioggia"}


def wardrobe(conn):
    add(conn, "Giacca navy", "giacca completo", "navy", 5, set_key="navy1")
    add(conn, "Pantalone navy", "pantalone completo", "navy", 5, set_key="navy1")
    add(conn, "Camicia bianca", "camicia", "bianco", 4)
    add(conn, "Camicia azzurra", "camicia", "azzurro", 4)
    add(conn, "Cravatta bordeaux", "cravatta", "bordeaux", 5, pattern="regimental")
    add(conn, "Oxford marroni", "scarpe formali", "marrone", 5)
    add(conn, "Chino beige", "chino", "beige", 3)
    add(conn, "Polo ruggine", "polo", "ruggine", 2)
    add(conn, "Mocassini scamosciati", "mocassini", "marrone", 3, rain_ok=0)
    add(conn, "Sneakers bianche", "sneakers", "bianco", 1)
    add(conn, "Scarpe nere", "scarpe formali", "nero", 5)
    add(conn, "Impermeabile", "impermeabile", "beige", 3, rain_gear=1)


def test_dress_code_rules(conn):
    # 2026-11-23 è settimana di plenaria, lunedì → completo
    assert calendar.day_info(conn, date(2026, 11, 23))["dress_code"] == "completo"
    # venerdì di settimana di gruppo → informale
    assert calendar.day_info(conn, date(2026, 11, 20))["dress_code"] == "informale"
    # settimana verde → informale anche il lunedì
    assert calendar.day_info(conn, date(2026, 10, 26))["dress_code"] == "informale"
    # festivo
    assert calendar.day_info(conn, date(2026, 11, 11))["dress_code"] == "libero"
    conn.execute("INSERT INTO day_overrides VALUES ('2026-11-24','informale','non vado in ufficio')")
    assert calendar.day_info(conn, date(2026, 11, 24))["dress_code"] == "informale"


def test_formal_outfit(conn):
    wardrobe(conn)
    res = engine.suggest(conn, date(2026, 11, 23), 1, "completo", SUNNY)
    assert res["outfits"], res
    names = {i["name"] for i in res["outfits"][0]["items"]}
    assert {"Giacca navy", "Pantalone navy", "Cravatta bordeaux"} <= names
    assert "Chino beige" not in names


def test_rain_no_suede_and_coat(conn):
    wardrobe(conn)
    res = engine.suggest(conn, date(2026, 11, 20), 1, "informale", RAINY)
    for o in res["outfits"]:
        names = {i["name"] for i in o["items"]}
        assert "Mocassini scamosciati" not in names
        assert "Impermeabile" in names


def test_black_shoes_never_with_beige(conn):
    wardrobe(conn)
    res = engine.suggest(conn, date(2026, 11, 20), 1, "informale", SUNNY)
    for o in res["outfits"]:
        names = {i["name"] for i in o["items"]}
        assert not ({"Scarpe nere", "Chino beige"} <= names)


def test_missing_explained(conn):
    add(conn, "Giacca navy", "giacca completo", "navy", 5, set_key="n")
    add(conn, "Pantalone navy", "pantalone completo", "navy", 5, set_key="n")
    add(conn, "Camicia bianca", "camicia", "bianco", 4, status="da_lavare")
    add(conn, "Cravatta", "cravatta", "bordeaux", 5)
    add(conn, "Oxford", "scarpe formali", "marrone", 5)
    res = engine.suggest(conn, date(2026, 11, 23), 1, "completo", SUNNY)
    assert not res["outfits"]
    assert "camicia" in res["missing"][0] and "da lavare" in res["missing"][0]


def test_repeat_days(conn):
    wardrobe(conn)
    shirt = conn.execute("SELECT id FROM garments WHERE name='Camicia bianca'").fetchone()[0]
    cur = conn.execute("INSERT INTO outfits(date, dress_code, source, status) VALUES ('2026-11-18','completo','manuale','indossato')")
    conn.execute("INSERT INTO outfit_items VALUES (?,?)", (cur.lastrowid, shirt))
    res = engine.suggest(conn, date(2026, 11, 23), 1, "completo", SUNNY)
    for o in res["outfits"]:
        assert shirt not in {i["id"] for i in o["items"]}


def test_other_city_ignored(conn):
    wardrobe(conn)
    add(conn, "Camicia a Livorno", "camicia", "bianco", 4, city=3)
    res = engine.suggest(conn, date(2026, 11, 23), 1, "completo", SUNNY)
    for o in res["outfits"]:
        assert "Camicia a Livorno" not in {i["name"] for i in o["items"]}


def test_no_weather_still_works(conn):
    wardrobe(conn)
    res = engine.suggest(conn, date(2026, 11, 23), 1, "completo", {"ok": False, "message": "x"})
    assert res["outfits"]
