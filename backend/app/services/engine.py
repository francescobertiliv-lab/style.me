"""Motore degli abbinamenti a regole. Nessun LLM.

Passi:
1. prende i capi puliti nella città giusta, non usati di recente (repeat_days della categoria);
2. filtra per dress code, peso adatto alla temperatura e pioggia;
3. prova tutte le combinazioni dei pezzi principali e scarta quelle che violano le regole di stile;
4. dà un punteggio (palette, feedback, rotazione) e restituisce le migliori;
5. se non c'è niente di valido, spiega cosa manca.
"""
import hashlib
import itertools
import json
from datetime import date

from ..db import get_setting, rows
from . import weather as wx

STATUS_LABEL = {
    "da_lavare": "da lavare", "tintoria": "in tintoria", "valigia": "in valigia", "sarta": "dalla sarta",
}
SLOT_LABEL = {
    "capospalla": "cappotto o impermeabile", "giacca": "giacca", "strato": "maglione",
    "top": "camicia o maglia", "sotto": "pantalone", "scarpe": "paio di scarpe", "cravatta": "cravatta",
}
DEPTH = {"chiaro": 0, "medio": 1, "scuro": 2}


# ---------- dati ----------

def load_garments(conn, city_ids, extra_ids=()) -> list[dict]:
    """Tutti i capi attivi nelle città indicate (più eventuali capi extra), con i dati di colore e palette."""
    q = f"""
      SELECT g.*, c.name AS category, c.slot, c.repeat_days,
             f.tone, f.depth, COALESCE(pc.role, 'fuori') AS palette_role
      FROM garments g
      JOIN categories c ON c.id = g.category_id
      JOIN color_families f ON f.name = g.color_family
      LEFT JOIN palettes p ON p.active = 1
      LEFT JOIN palette_colors pc ON pc.palette_id = p.id AND pc.family = g.color_family
      WHERE g.archived = 0 AND (g.city_id IN ({",".join("?" * len(city_ids))})
            OR g.id IN ({",".join("?" * len(extra_ids)) or "NULL"}))
    """
    return rows(conn.execute(q, (*city_ids, *extra_ids)))


def last_worn(conn, before: date) -> dict[int, date]:
    out = {}
    for r in conn.execute(
        "SELECT oi.garment_id, MAX(o.date) AS d FROM outfits o "
        "JOIN outfit_items oi ON oi.outfit_id = o.id "
        "WHERE o.status = 'indossato' AND o.date < ? GROUP BY oi.garment_id",
        (before.isoformat(),),
    ):
        out[r["garment_id"]] = date.fromisoformat(r["d"])
    return out


def pair_feedback(conn) -> dict[tuple[int, int], float]:
    """Pollici su/giù degli outfit indossati, sommati per coppia di capi."""
    fb: dict[tuple[int, int], float] = {}
    outfits = conn.execute("SELECT id, rating FROM outfits WHERE rating IS NOT NULL").fetchall()
    for o in outfits:
        ids = sorted(r["garment_id"] for r in conn.execute(
            "SELECT garment_id FROM outfit_items WHERE outfit_id = ?", (o["id"],)))
        for a, b in itertools.combinations(ids, 2):
            fb[(a, b)] = fb.get((a, b), 0) + o["rating"]
    return fb


def load_rules(conn) -> list[dict]:
    rs = rows(conn.execute("SELECT * FROM style_rules WHERE active = 1"))
    for r in rs:
        r["params"] = json.loads(r["params"] or "{}")
    return rs


# ---------- regole ----------

def target_weight(conn, w: dict) -> int | None:
    if not w.get("ok"):
        return None
    c = get_setting(conn, "climate", {"light_from": 22, "heavy_below": 12})
    if w["tmax"] >= c["light_from"]:
        return 1
    if w["tmax"] < c["heavy_below"]:
        return 3
    return 2


def _matches(cond: dict, g: dict) -> bool:
    if "slot" in cond and g["slot"] != cond["slot"]:
        return False
    if "family" in cond and g["color_family"] not in cond["family"]:
        return False
    if "category" in cond and g["category"] not in cond["category"]:
        return False
    return True


def is_accent(g: dict) -> bool:
    return g["tone"] != "neutro" and g["palette_role"] != "base"


def check(combo: list[dict], rules: list[dict]) -> tuple[bool, float, list[str]]:
    """Ritorna (valido, punti, regole violate)."""
    score, broken = 0.0, []
    by_slot = {g["slot"]: g for g in combo}
    for r in rules:
        p, kind = r["params"], r["kind"]
        if kind == "vieta_coppia":
            for x, y in itertools.permutations(combo, 2):
                if _matches(p["a"], x) and _matches(p["b"], y):
                    broken.append(r["description"])
                    break
        elif kind == "max_accenti":
            if len({g["color_family"] for g in combo if is_accent(g)}) > p.get("max", 2):
                broken.append(r["description"])
        elif kind == "max_fantasie":
            if sum(1 for g in combo if g["pattern"] != "tinta unita") > p.get("max", 2):
                broken.append(r["description"])
        elif kind == "evita_palette":
            score -= 3 * sum(1 for g in combo if g["palette_role"] == "evita")
        elif kind == "sotto_scarpe_vicini":
            s, sh = by_slot.get("sotto"), by_slot.get("scarpe")
            if s and sh and abs(DEPTH[s["depth"]] - DEPTH[sh["depth"]]) > p.get("max_gap", 1):
                score -= 2
        elif kind == "colore_sopra":
            upper = [by_slot[k] for k in ("top", "strato", "giacca") if k in by_slot]
            s = by_slot.get("sotto")
            if s and upper:
                if any(is_accent(g) for g in upper) and not is_accent(s):
                    score += p.get("bonus", 1)
                elif is_accent(s) and not any(is_accent(g) for g in upper):
                    score -= p.get("bonus", 1)
    return (not broken), score, broken


# ---------- motore ----------

def available(conn, day: date, city_ids, weather: dict, *, extra_ids=(), reserved=frozenset(),
              allowed_status=("pulito",)) -> dict:
    """Capi utilizzabili quel giorno, divisi per slot, con i motivi degli esclusi."""
    every = load_garments(conn, city_ids, extra_ids)
    worn = last_worn(conn, day)
    rain = wx.is_rainy(conn, weather)
    tw = target_weight(conn, weather)
    reasons: dict[str, dict[str, int]] = {}

    def usable(g) -> bool:
        why = None
        if g["status"] not in allowed_status and g["id"] not in extra_ids:
            why = STATUS_LABEL.get(g["status"], g["status"])
        elif g["repeat_days"] and g["id"] in worn and (day - worn[g["id"]]).days < g["repeat_days"]:
            why = f"messi negli ultimi {g['repeat_days']} giorni"
        elif g["repeat_days"] and g["id"] in reserved:
            why = "già usati nei giorni vicini"
        elif rain and not g["rain_ok"]:
            why = "non adatti alla pioggia"
        elif tw and g["slot"] in ("sotto", "giacca", "strato", "capospalla") and abs(g["weight"] - tw) > 1:
            why = "troppo pesanti o leggeri per il meteo"
        if why:
            reasons.setdefault(g["slot"], {})
            reasons[g["slot"]][why] = reasons[g["slot"]].get(why, 0) + 1
            return False
        return True

    pool = [g for g in every if usable(g)]
    by = {s: [g for g in pool if g["slot"] == s] for s in SLOT_LABEL}
    return {"every": every, "pool": pool, "by": by, "reasons": reasons, "rain": rain, "tw": tw, "worn": worn}


def candidates(by: dict, dress_code: str) -> dict:
    """Capi ammessi per ogni posto dell'outfit, secondo il dress code."""
    if dress_code == "completo":
        jackets = [g for g in by["giacca"] if g["set_key"] and g["formality"] >= 4]
        return {
            "completo": [(j, s) for j in jackets for s in by["sotto"] if s["set_key"] == j["set_key"]],
            "top": [g for g in by["top"] if g["formality"] >= 4],
            "cravatta": by["cravatta"],
            "scarpe": [g for g in by["scarpe"] if g["formality"] >= 4],
            "strato": by["strato"],
            "capospalla": [g for g in by["capospalla"] if g["formality"] >= 3] or by["capospalla"],
        }
    return {
        "top": [g for g in by["top"] if g["formality"] <= 4],
        "sotto": [g for g in by["sotto"] if not g["set_key"]],
        "scarpe": [g for g in by["scarpe"] if g["formality"] <= 4],
        "giacca": [g for g in by["giacca"] if not g["set_key"]],
        "strato": by["strato"],
        "capospalla": by["capospalla"],
    }


OPTIONAL = {"completo": ("strato", "capospalla"), "informale": ("giacca", "strato", "capospalla"),
            "libero": ("giacca", "strato", "capospalla")}


def swap_options(conn, outfit: dict, items: list[dict], slot: str, limit: int = 8) -> dict:
    """Alternative per un posto dell'outfit, compatibili con il resto. Per il completo si cambia la coppia."""
    day = date.fromisoformat(outfit["date"])
    weather = json.loads(outfit["weather"] or "{}") or {"ok": False}
    city_id = outfit["city_id"] or get_setting(conn, "home_city_id", 1)
    av = available(conn, day, [city_id], weather, extra_ids=tuple(i["id"] for i in items))
    cands = candidates(av["by"], outfit["dress_code"])
    rules = load_rules(conn)
    full = {g["id"]: g for g in load_garments(conn, [city_id], tuple(i["id"] for i in items))}
    current = [full[i["id"]] for i in items if i["id"] in full]
    formal_pair = outfit["dress_code"] == "completo" and slot in ("giacca", "sotto")
    if formal_pair:
        rest = [g for g in current if g["slot"] not in ("giacca", "sotto")]
        options = [list(pair) for pair in cands["completo"]]
        now = [g for g in current if g["slot"] in ("giacca", "sotto")]
    else:
        rest = [g for g in current if g["slot"] != slot]
        options = [[g] for g in cands.get(slot, [])]
        now = [g for g in current if g["slot"] == slot]
    now_ids = {g["id"] for g in now}
    scored = []
    for opt in options:
        if {g["id"] for g in opt} == now_ids:
            continue
        ok, pts, broken = check(rest + opt, rules)
        if ok:
            scored.append((pts, opt))
    scored.sort(key=lambda x: -x[0])
    return {
        "slot": slot,
        "current": [_public(g) for g in now],
        "removable": slot in OPTIONAL.get(outfit["dress_code"], ()) and bool(now),
        "options": [[_public(g) for g in opt] for _, opt in scored[:limit]],
    }


def _jitter(day: date, ids) -> float:
    h = hashlib.md5(f"{day}-{sorted(ids)}".encode()).hexdigest()
    return int(h[:4], 16) / 0xFFFF * 0.2


def suggest(conn, day: date, city_id: int, dress_code: str, weather: dict, *,
            extra_city_ids=(), extra_ids=(), reserved=frozenset(), prefer=frozenset(),
            allowed_status=("pulito",), n: int = 3) -> dict:
    """Propone fino a n outfit. reserved = capi già usati in giorni vicini (viaggi);
    prefer = capi già in valigia da riusare."""
    city_ids = [city_id, *extra_city_ids]
    city_name = conn.execute("SELECT name FROM cities WHERE id = ?", (city_id,)).fetchone()
    city_name = city_name["name"] if city_name else "qui"
    av = available(conn, day, city_ids, weather, extra_ids=extra_ids, reserved=reserved, allowed_status=allowed_status)
    every, reasons, rain, tw, worn = av["every"], av["reasons"], av["rain"], av["tw"], av["worn"]
    climate = get_setting(conn, "climate", {"coat_below": 15, "layer_below": 12})
    by = av["by"]

    formal = dress_code == "completo"
    c = candidates(by, dress_code)
    if formal:
        suits, tops, ties, shoes = c["completo"], c["top"], c["cravatta"], c["scarpe"]
        required = {"completo": suits, "top": tops, "cravatta": ties, "scarpe": shoes}
    else:
        tops, bottoms, shoes = c["top"], c["sotto"], c["scarpe"]
        jackets = [None] + c["giacca"]
        required = {"top": tops, "sotto": bottoms, "scarpe": shoes}

    missing = []
    for slot, cands in required.items():
        if not cands:
            missing.append(_explain_missing(slot, every, reasons, city_name, formal))
    if missing:
        return {"outfits": [], "missing": missing, "rain": rain, "target_weight": tw}

    rules = load_rules(conn)
    fb = pair_feedback(conn)

    def score_extra(combo):
        s = 0.0
        ids = sorted(g["id"] for g in combo)
        if any(g["palette_role"] == "da_aggiungere" for g in combo):
            s += 0.5
        for a, b in itertools.combinations(ids, 2):
            s += 0.5 * max(-2, min(2, fb.get((a, b), 0)))
        days = [min((day - worn[g["id"]]).days, 30) if g["id"] in worn else 30 for g in combo]
        s += sum(days) / len(days) / 30
        s += 0.7 * sum(1 for g in combo if g["id"] in prefer)
        if tw:
            s += 0.3 * sum(1 for g in combo if g["slot"] in ("sotto", "giacca") and g["weight"] == tw)
        if dress_code == "libero":
            s -= 0.3 * sum(max(0, g["formality"] - 2) for g in combo)
        return s + _jitter(day, ids)

    scored, broken_count = [], {}
    if formal:
        combos = ([j, s, t, c, sh] for (j, s) in suits for t in tops for c in ties for sh in shoes)
    else:
        combos = ([t, b, sh] + ([j] if j else []) for t in tops for b in bottoms for sh in shoes for j in jackets)
    for combo in combos:
        ok, pts, broken = check(combo, rules)
        if not ok:
            for b in broken:
                broken_count[b] = broken_count.get(b, 0) + 1
            continue
        scored.append((pts + score_extra(combo), combo))

    if not scored:
        top_rules = sorted(broken_count, key=broken_count.get, reverse=True)[:2]
        return {
            "outfits": [],
            "missing": ["Ho i capi, ma nessuna combinazione rispetta le regole: "
                        + "; ".join(top_rules) + "."],
            "rain": rain, "target_weight": tw,
        }

    scored.sort(key=lambda x: x[0], reverse=True)
    chosen = []
    for pts, combo in scored:
        ids = {g["id"] for g in combo}
        if all(len(ids & c["ids"]) / len(ids | c["ids"]) < 0.6 for c in chosen):
            chosen.append({"ids": ids, "score": pts, "combo": combo})
        if len(chosen) == n:
            break

    notes = []
    need_coat = weather.get("ok") and (weather["tmax"] < climate["coat_below"] or rain)
    need_layer = (not formal) and weather.get("ok") and weather["tmax"] < climate["layer_below"]
    result = []
    for c in chosen:
        combo = list(c["combo"])
        if need_layer:
            layer = _best_addition(combo, by["strato"], rules, prefer)
            if layer:
                combo.append(layer)
        if need_coat:
            coats = by["capospalla"]
            if rain:
                coats = sorted(coats, key=lambda g: -g["rain_gear"])
            if formal:
                coats = [g for g in coats if g["formality"] >= 3] or coats
            coat = _best_addition(combo, coats, rules, prefer, prefer_rain=rain)
            if coat:
                combo.append(coat)
            elif not notes:
                notes.append(_explain_missing("capospalla", every, reasons, city_name, formal))
        result.append({"score": round(c["score"], 2), "items": [_public(g) for g in combo]})
    return {"outfits": result, "missing": notes, "rain": rain, "target_weight": tw}


def _best_addition(combo, cands, rules, prefer, prefer_rain=False):
    best, best_pts = None, None
    for g in cands:
        ok, pts, _ = check(combo + [g], rules)
        if not ok:
            continue
        pts += 0.7 if g["id"] in prefer else 0
        pts += 2 if (prefer_rain and g["rain_gear"]) else 0
        if best_pts is None or pts > best_pts:
            best, best_pts = g, pts
    return best


NONE_LABEL = {
    "capospalla": "Nessun cappotto o impermeabile", "giacca": "Nessuna giacca", "strato": "Nessun maglione",
    "top": "Nessuna camicia o maglia", "sotto": "Nessun pantalone", "scarpe": "Nessun paio di scarpe",
    "cravatta": "Nessuna cravatta", "completo": "Nessun completo (giacca e pantalone)",
    "top_formal": "Nessuna camicia da completo", "scarpe_formal": "Nessun paio di scarpe eleganti",
}


def _explain_missing(slot, every, reasons, city_name, formal) -> str:
    key = f"{slot}_formal" if formal and slot in ("top", "scarpe") else slot
    label = NONE_LABEL.get(key, slot)
    why = reasons.get("giacca" if slot == "completo" else slot, {})
    if why:
        detail = ", ".join(f"{w} ({n})" for w, n in why.items())
        return f"{label} disponibile a {city_name}: {detail}."
    return f"{label} a {city_name}: nel guardaroba non ne ho trovati."


def _public(g: dict) -> dict:
    keys = ("id", "name", "category", "slot", "color_hex", "color_family", "pattern", "cutout", "photo", "formality")
    return {k: g[k] for k in keys}
