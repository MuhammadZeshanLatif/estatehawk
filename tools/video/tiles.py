"""Stand-in map tiles for video recording when server.arcgisonline.com is not reachable (the cloud workspace blocks it).
python3 tools/video/tiles.py PORT
Serves /street/{z}/{y}/{x} and /sat/{z}/{y}/{x}: a clean street-map look and an aerial look (roads, lawns, trees, roofs).
Tiles are drawn from world pixel positions, so roads continue across tiles and every zoom level looks consistent.
record.js uses these only when the real Esri tile cannot be fetched."""
import hashlib, io, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

T = 256


def h(*a):
    return int(hashlib.md5(("|".join(map(str, a))).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def roads(z, x0, y0):
    """road lines crossing this tile, in tile pixels: (orientation, position, width, major)"""
    if z < 11:
        return []
    s = 2 ** (z - 16)  # pixels per "street unit"
    S = max(60, 210 * s)  # spacing between streets in world pixels at this zoom
    out = []
    for o, base in (("v", x0), ("h", y0)):
        k0 = int(base // S) - 1
        for k in range(k0, k0 + int(T // S) + 3):
            pos = k * S + (h(o, k, "j") - 0.5) * S * 0.35 - base
            major = k % 5 == 0
            w = max(2, (14 if major else 8) * s * (1.6 if major else 1))
            if -w < pos < T + w:
                out.append((o, pos, w, major))
    return out


def street(z, x, y):
    x0, y0 = x * T, y * T
    im = Image.new("RGB", (T, T), (242, 239, 233))
    d = ImageDraw.Draw(im)
    if z >= 13:  # parks and blocks
        S = max(60, 210 * 2 ** (z - 16))
        for i in range(int(x0 // S) - 1, int((x0 + T) // S) + 2):
            for j in range(int(y0 // S) - 1, int((y0 + T) // S) + 2):
                if h("park", i, j) < 0.08:
                    d.rectangle([i * S - x0 + 6, j * S - y0 + 6, (i + 1) * S - x0 - 6, (j + 1) * S - y0 - 6], fill=(205, 228, 196))
                elif z >= 16:
                    for b in range(4):
                        bx = i * S - x0 + 14 + h("bx", i, j, b) * (S - 50)
                        by = j * S - y0 + 14 + h("by", i, j, b) * (S - 50)
                        bw = 14 + h("bw", i, j, b) * 22 * 2 ** (z - 16)
                        d.rectangle([bx, by, bx + bw, by + bw * 0.8], fill=(226, 222, 214), outline=(212, 207, 198))
    for o, p, w, major in roads(z, x0, y0):
        case, fill = ((226, 196, 120), (252, 224, 150)) if major else ((214, 209, 200), (255, 255, 255))
        if o == "v":
            d.rectangle([p - w / 2 - 1, 0, p + w / 2 + 1, T], fill=case); d.rectangle([p - w / 2, 0, p + w / 2, T], fill=fill)
        else:
            d.rectangle([0, p - w / 2 - 1, T, p + w / 2 + 1], fill=case); d.rectangle([0, p - w / 2, T, p + w / 2], fill=fill)
    if z < 11:  # region view: soft land with faint lines
        for k in range(0, T, 64):
            d.line([(k, 0), (k, T)], fill=(234, 231, 224)); d.line([(0, k), (T, k)], fill=(234, 231, 224))
    return im


def vnoise(x0, y0, cell, seed):
    """smooth value noise from world pixel positions (no seams between tiles)"""
    xs = (x0 + np.arange(T)) / cell
    ys = (y0 + np.arange(T)) / cell
    gx0, gy0 = int(np.floor(xs[0])), int(np.floor(ys[0]))
    nx, ny = int(np.floor(xs[-1])) - gx0 + 2, int(np.floor(ys[-1])) - gy0 + 2
    g = np.array([[h(seed, gx0 + i, gy0 + j) for i in range(nx)] for j in range(ny)])
    fx, fy = xs - gx0, ys - gy0
    ix, iy = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - ix, fy - iy
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a = g[np.ix_(iy, ix)]; b = g[np.ix_(iy, ix + 1)]; c = g[np.ix_(iy + 1, ix)]; d = g[np.ix_(iy + 1, ix + 1)]
    top = a + (b - a) * tx[None, :]; bot = c + (d - c) * tx[None, :]
    return top + (bot - top) * ty[:, None]


def sat(z, x, y):
    x0, y0 = x * T, y * T
    k = 2 ** (z - 16)
    n = 0.6 * vnoise(x0, y0, 40 * k, "g1") + 0.4 * vnoise(x0, y0, 9 * k, "g2")
    base = np.stack([84 + 40 * n, 104 + 34 * n, 62 + 22 * n], -1)
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    if z >= 13:
        S = 70 * k  # one block is about 120 m
        rw = max(2, 4.5 * k)  # road about 8 m wide
        lot = 9 * k  # house lot about 16 m wide
        for i in range(int(x0 // S) - 1, int((x0 + T) // S) + 2):
            for j in range(int(y0 // S) - 1, int((y0 + T) // S) + 2):
                bx, by = i * S - x0, j * S - y0
                if h("park", i, j) < 0.1:
                    continue
                if z >= 15:  # lots with lawns, houses facing the street, back-yard trees
                    for side in range(2):
                        for m in range(int((S - 2 * rw) // lot)):
                            lx = bx + rw + m * lot
                            ly = by + rw if side == 0 else by + S - rw - lot * 1.6
                            sh = 0.85 + 0.25 * h("l", i, j, side, m)
                            d.rectangle([lx, ly, lx + lot - 1, ly + lot * 1.6], fill=(int(98 * sh), int(122 * sh), int(70 * sh)))
                            if h("e", i, j, side, m) < 0.88:
                                hw, hh = lot * (0.55 + 0.2 * h("w", i, j, side, m)), lot * (0.5 + 0.2 * h("hh", i, j, side, m))
                                hx = lx + (lot - hw) / 2
                                hy = ly + lot * 0.35 if side == 0 else ly + lot * 1.6 - lot * 0.35 - hh
                                roof = [(112, 106, 100), (138, 96, 80), (92, 94, 100), (158, 150, 138), (124, 120, 112)][int(h("c", i, j, side, m) * 5)]
                                d.rectangle([hx + k, hy + k, hx + hw + k, hy + hh + k], fill=(46, 54, 38))
                                d.rectangle([hx, hy, hx + hw, hy + hh], fill=roof)
                                d.line([(hx, hy + hh / 2), (hx + hw, hy + hh / 2)], fill=tuple(max(0, c - 22) for c in roof), width=max(1, int(k)))
                            if h("t", i, j, side, m) < 0.5:
                                tx = lx + lot * h("tx", i, j, side, m)
                                ty = (ly + lot * 1.45) if side == 0 else (ly + lot * 0.15)
                                r = (3 + 3 * h("tr", i, j, side, m)) * k
                                d.ellipse([tx - r, ty - r, tx + r, ty + r], fill=(48, 70, 40))
        for i in range(int(x0 // S) - 1, int((x0 + T) // S) + 2):
            d.rectangle([i * S - x0 - rw, 0, i * S - x0 + rw, T], fill=(126, 125, 120))
        for j in range(int(y0 // S) - 1, int((y0 + T) // S) + 2):
            d.rectangle([0, j * S - y0 - rw, T, j * S - y0 + rw], fill=(126, 125, 120))
    return im


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            kind, z, y, x = self.path.strip("/").split("/")[:4]
            im = (sat if kind == "sat" else street)(int(z), int(x), int(y))
            buf = io.BytesIO(); im.save(buf, "JPEG", quality=86)
            self.send_response(200); self.send_header("Content-Type", "image/jpeg"); self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers(); self.wfile.write(buf.getvalue())
        except Exception as e:
            self.send_response(404); self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8197), H).serve_forever()
