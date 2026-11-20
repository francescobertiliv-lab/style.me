"""Foto dei capi: salvataggio, scontorno, colori e proposta degli attributi."""
import io
import uuid
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

from .. import config
from . import colors

MAX_SIDE = 1600


def _remove_background(img: Image.Image) -> Image.Image:
    """Scontorno con rembg se installato. Se manca o fallisce, toglie solo lo sfondo bianco."""
    try:
        from rembg import remove  # dipendenza pesante, caricata solo qui
        return remove(img)
    except Exception:
        return _remove_white(img)


def _remove_white(img: Image.Image, threshold: int = 235) -> Image.Image:
    rgb = img.convert("RGB")
    masks = [ch.point(lambda v: 255 if v > threshold else 0) for ch in rgb.split()]
    white = ImageChops.multiply(ImageChops.multiply(masks[0], masks[1]), masks[2])
    out = rgb.convert("RGBA")
    out.putalpha(ImageOps.invert(white))
    return out


def save_upload(data: bytes, kind: str = "garment") -> dict:
    """Salva la foto, crea il ritaglio e restituisce i percorsi relativi a PHOTOS_DIR."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    name = f"{kind}-{uuid.uuid4().hex[:12]}"
    original = Path("originals") / f"{name}.jpg"
    img.save(config.PHOTOS_DIR / original, "JPEG", quality=88)

    cut = _remove_background(img)
    bbox = cut.getchannel("A").getbbox()
    if bbox:
        cut = cut.crop(bbox)
    cut.thumbnail((800, 800))
    cutout = Path("cutouts") / f"{name}.png"
    cut.save(config.PHOTOS_DIR / cutout, "PNG", optimize=True)
    return {"photo": str(original), "cutout": str(cutout), "image": cut}


def propose_attributes(conn, cut: Image.Image) -> dict:
    """Proposta da confermare: colori, famiglia, fantasia, categoria probabile."""
    dom = colors.dominant_colors(cut)
    main = dom[0]["hex"] if dom else "#808080"
    w, h = cut.size
    ratio = h / w if w else 1
    # Indizio grezzo dalla forma: molto stretta e alta = cravatta, larga e bassa = scarpe.
    if ratio > 3:
        guess = "cravatta"
    elif ratio < 0.7:
        guess = "sneakers"
    else:
        guess = None
    cat = None
    if guess:
        cat = conn.execute(
            "SELECT id, name, default_formality, default_weight FROM categories WHERE name = ?", (guess,)
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
