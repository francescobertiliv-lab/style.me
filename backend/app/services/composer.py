"""Immagine dell'outfit composta dai ritagli, come un flat lay."""
import uuid
from pathlib import Path

from PIL import Image

from .. import config

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
    """items: dict con slot e cutout. Ritorna il percorso relativo dell'immagine."""
    canvas = Image.new("RGB", (W, H), (250, 249, 246))
    placed = 0
    for it in items:
        box = LAYOUT.get(it.get("slot"))
        path = config.PHOTOS_DIR / it["cutout"] if it.get("cutout") else None
        if not box or not path or not path.exists():
            continue
        x, y, bw, bh = box
        im = Image.open(path).convert("RGBA")
        im.thumbnail((bw, bh))
        canvas.paste(im, (x + (bw - im.width) // 2, y + (bh - im.height) // 2), im)
        placed += 1
    if not placed:
        return None
    rel = Path("outfits") / f"outfit-{uuid.uuid4().hex[:12]}.jpg"
    canvas.save(config.PHOTOS_DIR / rel, "JPEG", quality=85)
    return str(rel)
