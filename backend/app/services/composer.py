"""Immagine dell'outfit composta dai ritagli, come un flat lay."""
import io
import uuid

from PIL import Image

from . import storage

BG = (238, 236, 231)
LEFT = ("capospalla", "giacca", "strato")          # strati esterni, colonna di sinistra
RIGHT = ("top", "sotto", "scarpe")                  # dal busto ai piedi, colonna di destra
SIZE = {"capospalla": 420, "giacca": 400, "strato": 300, "top": 340, "sotto": 440, "scarpe": 200, "accessorio": 180}


def _load(it):
    data = storage.get(it["cutout"]) if it.get("cutout") else None
    return Image.open(io.BytesIO(data)).convert("RGBA") if data else None


def compose(items: list[dict]) -> str | None:
    """items: dict con slot e cutout. Ritorna il percorso dell'immagine salvata.
    Due colonne come un flat lay: strati esterni a sinistra, busto-gambe-scarpe a destra.
    Se non ci sono strati esterni, una colonna sola al centro."""
    imgs = {}
    for it in items:
        im = _load(it)
        if im is not None:
            im.thumbnail((380, SIZE.get(it.get("slot"), 300)))
            imgs.setdefault(it.get("slot"), im)
    if not imgs:
        return None
    left = [imgs[s] for s in LEFT if s in imgs]
    right = [imgs[s] for s in RIGHT if s in imgs]
    gap, pad = 24, 40
    col_h = lambda col: sum(i.height for i in col) + gap * max(len(col) - 1, 0)
    W = 900 if left else 520
    H = max(col_h(left), col_h(right)) + 2 * pad
    canvas = Image.new("RGB", (W, max(H, 600)), BG)
    columns = [(left, W // 4), (right, 3 * W // 4)] if left else [(right, W // 2)]
    for col, cx in columns:
        y = pad
        for im in col:
            canvas.paste(im, (cx - im.width // 2, y), im)
            y += im.height + gap
    tie = imgs.get("cravatta")
    if tie is not None and "top" in imgs:  # la cravatta sopra la camicia
        top = imgs["top"]
        tie.thumbnail((90, int(top.height * 0.9)))
        cx = (3 * W // 4) if left else W // 2
        canvas.paste(tie, (cx - tie.width // 2, pad + top.height // 6), tie)
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=85)
    return storage.put(f"outfits/outfit-{uuid.uuid4().hex[:12]}.jpg", buf.getvalue(), "image/jpeg")
