"""Foto dei capi: salvataggio, ritaglio, colori e proposta degli attributi.

Lo scontorno vero lo fa il browser quando scatti la foto (gira sul telefono, gratis).
Se il ritaglio non arriva, qui togliamo solo lo sfondo bianco.
"""
import io
import uuid

from PIL import Image, ImageChops, ImageOps

from . import colors, storage

MAX_SIDE = 1600


def _remove_white(img: Image.Image, threshold: int = 235) -> Image.Image:
    rgb = img.convert("RGB")
    masks = [ch.point(lambda v: 255 if v > threshold else 0) for ch in rgb.split()]
    white = ImageChops.multiply(ImageChops.multiply(masks[0], masks[1]), masks[2])
    out = rgb.convert("RGBA")
    out.putalpha(ImageOps.invert(white))
    return out


def save_upload(data: bytes, cutout: bytes | None = None, kind: str = "garment") -> dict:
    """Salva foto originale e ritaglio. Ritorna i percorsi e l'immagine ritagliata."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    name = f"{kind}-{uuid.uuid4().hex[:12]}"

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    photo = storage.put(f"originals/{name}.jpg", buf.getvalue(), "image/jpeg")

    cut = Image.open(io.BytesIO(cutout)).convert("RGBA") if cutout else _remove_white(img)
    bbox = cut.getchannel("A").getbbox()
    if bbox:
        cut = cut.crop(bbox)
    cut.thumbnail((800, 800))
    buf = io.BytesIO()
    cut.save(buf, "PNG", optimize=True)
    cut_path = storage.put(f"cutouts/{name}.png", buf.getvalue(), "image/png")
    return {"photo": photo, "cutout": cut_path, "image": cut}


def propose_attributes(conn, cut: Image.Image) -> dict:
    """Proposta da confermare: colori, famiglia, fantasia, categoria probabile."""
    dom = colors.dominant_colors(cut)
    main = dom[0]["hex"] if dom else "#808080"
    w, h = cut.size
    ratio = h / w if w else 1
    # Indizio grezzo dalla forma: molto alta e stretta = cravatta, larga e bassa = scarpe.
    guess = "cravatta" if ratio > 3 else "sneakers" if ratio < 0.7 else None
    cat = None
    if guess:
        cat = conn.execute(
            "SELECT id, default_formality, default_weight FROM categories WHERE name = ?", (guess,)
        ).fetchone()
    return {
        "color_hex": main,
        "color_family": colors.nearest_family(conn, main),
        "colors": dom,
        "pattern": colors.guess_pattern(dom),
        "category_id": cat["id"] if cat else None,
        "formality": cat["default_formality"] if cat else 3,
        "weight": cat["default_weight"] if cat else 2,
    }
