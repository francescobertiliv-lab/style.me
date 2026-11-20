"""Immagine dell'outfit composta dai ritagli, come un flat lay."""
import io
import uuid

from PIL import Image

from . import storage

W, H = 900, 1100
# Posizione (x, y, larghezza, altezza) di ogni slot nella tavola
LAYOUT = {
    "capospalla": (20, 20, 300, 420),
    "giacca": (300, 40, 320, 400),
    "strato": (20, 440, 260, 260),
    "top": (590, 40, 290, 360),
    "cravatta": (620, 400, 120, 330),
    "sotto": (300, 440, 300, 480),
    "scarpe": (620, 760, 260, 220),
    "accessorio": (40, 760, 220, 220),
}


def compose(items: list[dict]) -> str | None:
    """items: dict con slot e cutout. Ritorna il percorso dell'immagine salvata."""
    canvas = Image.new("RGB", (W, H), (250, 249, 246))
    placed = 0
    for it in items:
        box = LAYOUT.get(it.get("slot"))
        data = storage.get(it["cutout"]) if it.get("cutout") and box else None
        if not data:
            continue
        x, y, bw, bh = box
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        im.thumbnail((bw, bh))
        canvas.paste(im, (x + (bw - im.width) // 2, y + (bh - im.height) // 2), im)
        placed += 1
    if not placed:
        return None
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=85)
    return storage.put(f"outfits/outfit-{uuid.uuid4().hex[:12]}.jpg", buf.getvalue(), "image/jpeg")
