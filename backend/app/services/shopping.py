"""Analisi dei colori, suggerimenti di acquisto e prova prima di comprare.
Mai prodotti, prezzi o link inventati: i suggerimenti descrivono il capo (tipo, colore, tessuto)."""
import itertools

from ..db import get_setting, row, rows
from . import engine

# Tessuto consigliato per categoria: solo descrizione, nessun prodotto.
FABRIC = {
    "overshirt": "lana o cotone pesante", "chore jacket": "tela di cotone o moleskin", "polo": "maglia di cotone",
    "t-shirt": "cotone pesante a righe o tinta unita", "maglione": "lana merino o shetland", "cardigan": "lana",
    "chino": "cotone twill", "pantalone": "lana o flanella", "camicia": "oxford o flanella", "cravatta": "seta o lana",
    "giacca spezzata": "lana o tweed", "sciarpa": "lana o cashmere",
}
INFORMAL_CATS = ["overshirt", "chore jacket", "polo", "t-shirt", "maglione", "chino", "camicia"]


def _owned(conn) -> list[dict]:
    gs = engine.load_garments(conn, [r["id"] for r in conn.execute("SELECT id FROM cities")])
    return [g for g in gs if g["status"] != "sarta"]


def analysis(conn) -> dict:
    """Colori dei capi informali contro la palette attiva."""
    owned = [g for g in _owned(conn) if not g["set_key"] and g["slot"] not in ("cravatta", "accessorio")]
    palette = rows(conn.execute(
        "SELECT pc.family, pc.role, f.hex FROM palette_colors pc JOIN palettes p ON p.id = pc.palette_id "
        "JOIN color_families f ON f.name = pc.family WHERE p.active = 1"))
    counts: dict[str, int] = {}
    by_slot: dict[str, dict[str, int]] = {}
    for g in owned:
        counts[g["color_family"]] = counts.get(g["color_family"], 0) + 1
        by_slot.setdefault(g["slot"], {})
        by_slot[g["slot"]][g["color_family"]] = by_slot[g["slot"]].get(g["color_family"], 0) + 1
    fam_hex = {r["name"]: r["hex"] for r in conn.execute("SELECT name, hex FROM color_families")}
    roles = {p["family"]: p["role"] for p in palette}
    chart = [{"family": f, "hex": fam_hex[f], "count": n, "role": roles.get(f, "fuori")}
             for f, n in sorted(counts.items(), key=lambda x: -x[1])]
    missing = [{"family": p["family"], "hex": p["hex"], "role": p["role"],
                "missing_in": [s for s in ("top", "strato", "giacca", "sotto") if not by_slot.get(s, {}).get(p["family"])]}
               for p in palette if p["role"] in ("base", "da_aggiungere") and not counts.get(p["family"])]
    dark = sum(n for f, n in counts.items() if conn.execute(
        "SELECT depth FROM color_families WHERE name = ?", (f,)).fetchone()["depth"] == "scuro")
    total = sum(counts.values()) or 1
    return {"chart": chart, "missing": missing, "palette": palette, "total": total,
            "dark_share": round(dark / total, 2)}


def virtual_piece(conn, category: str, family: str) -> dict:
    cat = row(conn.execute("SELECT * FROM categories WHERE name = ?", (category,)))
    fam = row(conn.execute("SELECT * FROM color_families WHERE name = ?", (family,)))
    role = conn.execute(
        "SELECT pc.role FROM palette_colors pc JOIN palettes p ON p.id = pc.palette_id "
        "WHERE p.active = 1 AND pc.family = ?", (family,)).fetchone()
    return {"id": -1, "name": f"{category} {family}", "category": category, "slot": cat["slot"],
            "color_hex": fam["hex"], "color_family": family, "pattern": "tinta unita",
            "formality": cat["default_formality"], "weight": cat["default_weight"], "set_key": None,
            "tone": fam["tone"], "depth": fam["depth"], "palette_role": role["role"] if role else "fuori",
            "cutout": None, "photo": None, "rain_ok": 1, "rain_gear": 0}


def outfits_with(conn, piece: dict, owned: list[dict] | None = None, limit: int = 3) -> list[list[dict]]:
    """Outfit informali validi che contengono il capo nuovo e solo capi che ho già."""
    owned = owned if owned is not None else _owned(conn)
    rules = engine.load_rules(conn)
    pool = {s: [g for g in owned if g["slot"] == s and not g["set_key"]] for s in ("top", "sotto", "scarpe", "giacca", "strato")}
    pool[piece["slot"]] = [piece]
    tops, bottoms, shoes = pool["top"], pool["sotto"], pool["scarpe"]
    layers = [None] + pool["giacca"] + pool["strato"] if piece["slot"] not in ("giacca", "strato") else [piece]
    if piece["slot"] in ("giacca", "strato"):
        tops = [g for g in owned if g["slot"] == "top"]
    found = []
    for t, b, s, extra in itertools.product(tops, bottoms, shoes, layers):
        combo = [t, b, s] + ([extra] if extra else [])
        if not any(g["id"] == -1 for g in combo):
            continue
        ok, pts, _ = engine.check(combo, rules)
        if ok:
            found.append((pts, combo))
    found.sort(key=lambda x: -x[0])
    out, seen = [], set()
    for _, combo in found:
        key = tuple(sorted(g["id"] for g in combo if g["id"] != -1))
        if key in seen:
            continue
        seen.add(key)
        out.append([engine._public(g) for g in combo])
        if len(out) == limit:
            break
    return out


def suggestions(conn, max_items: int = 6) -> list[dict]:
    """Capi da comprare: colori che mancano, che fanno almeno 3 outfit con quello che ho."""
    owned = _owned(conn)
    prof = row(conn.execute("SELECT * FROM profile WHERE id = 1")) or {}
    an = analysis(conn)
    missing_fams = [m["family"] for m in an["missing"]]
    add_fams = [p["family"] for p in an["palette"] if p["role"] == "da_aggiungere"]
    # prima i toni caldi da aggiungere, poi i colori base che mancano
    families = list(dict.fromkeys(add_fams + missing_fams))
    have = {(g["category"], g["color_family"]) for g in owned}
    out, used_cats = [], {}
    for fam in families:
        # ruoto le categorie: meno ripetizioni di "overshirt" per ogni colore
        for cat in sorted(INFORMAL_CATS, key=lambda c: used_cats.get(c, 0)):
            if (cat, fam) in have:
                continue
            piece = virtual_piece(conn, cat, fam)
            combos = outfits_with(conn, piece, owned, limit=3)
            if len(combos) >= 3:
                out.append({
                    "category": cat, "family": fam, "hex": piece["color_hex"],
                    "description": f"{cat.capitalize()} {fam}, in {FABRIC.get(cat, 'tessuto di qualità')}",
                    "why": "tono da aggiungere" if fam in add_fams else "colore base che ti manca",
                    "budget": f"{prof.get('budget_min', 100)}–{prof.get('budget_max', 200)} €",
                    "outfits": combos,
                })
                used_cats[cat] = used_cats.get(cat, 0) + 1
                break  # una proposta per colore
        if len(out) >= max_items:
            break
    return out
