"""Colori: da HEX alla famiglia più vicina, colori dominanti di una foto."""
from PIL import Image


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*[int(c) for c in rgb[:3]])


def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb) -> tuple[float, float, float]:
    r, g, b = (_lin(c) for c in rgb[:3])
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def distance(hex_a: str, hex_b: str) -> float:
    a, b = rgb_to_lab(hex_to_rgb(hex_a)), rgb_to_lab(hex_to_rgb(hex_b))
    return sum((p - q) ** 2 for p, q in zip(a, b)) ** 0.5


def nearest_family(conn, hex_color: str) -> str:
    fams = conn.execute("SELECT name, hex FROM color_families").fetchall()
    return min(fams, key=lambda f: distance(hex_color, f["hex"]))["name"]


def dominant_colors(img: Image.Image, k: int = 4) -> list[dict]:
    """Colori dominanti dei pixel non trasparenti: [{hex, share}] dal più presente."""
    im = img.convert("RGBA")
    im.thumbnail((200, 200))
    pixels = [p[:3] for p in im.getdata() if p[3] > 128]
    if not pixels:
        return []
    flat = Image.new("RGB", (len(pixels), 1))
    flat.putdata(pixels)
    q = flat.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    palette = q.getpalette()
    counts = sorted(q.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)
    out = []
    for count, idx in counts:
        rgb = palette[idx * 3: idx * 3 + 3]
        out.append({"hex": rgb_to_hex(rgb), "share": round(count / total, 3)})
    return out


def guess_pattern(colors: list[dict], conn=None) -> str:
    """Stima semplice: se il secondo colore è consistente e lontano dal primo, c'è una fantasia."""
    if len(colors) < 2:
        return "tinta unita"
    main, second = colors[0], colors[1]
    if second["share"] >= 0.18 and distance(main["hex"], second["hex"]) > 25:
        return "fantasia"
    return "tinta unita"
