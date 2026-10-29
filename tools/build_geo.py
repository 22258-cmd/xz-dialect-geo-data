# -*- coding: utf-8 -*-
"""把徐州市区县 GeoJSON 简化为前端可直接使用的数据。"""
import json, math, os

SRC = r"D:\workbuddy\2026-10-16-16-04-30\data\xz.json"
OUT = r"D:\workbuddy\2026-10-16-16-04-30\XZDialectGame\data\geo.js"

TOL = 0.0045          # Douglas-Peucker 容差（度）
MIN_RING_PTS = 5


def perp_dist(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def rdp(pts, tol):
    if len(pts) < 3:
        return pts
    dmax, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = perp_dist(pts[i], pts[0], pts[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        return rdp(pts[:idx + 1], tol)[:-1] + rdp(pts[idx:], tol)
    return [pts[0], pts[-1]]


def ring_area(pts):
    s = 0.0
    for i in range(len(pts) - 1):
        s += pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
    return s / 2.0


def simplify_ring(ring, tol):
    pts = [(round(p[0], 4), round(p[1], 4)) for p in ring]
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        return None
    for factor in (1.0, 0.6, 0.35, 0.2, 0.1):
        simp = rdp(pts + [pts[0]], tol * factor)
        if len(simp) - 1 >= MIN_RING_PTS:
            return simp
    return None


def centroid(ring):
    a = cx = cy = 0.0
    for i in range(len(ring) - 1):
        cross = ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
        a += cross
        cx += (ring[i][0] + ring[i + 1][0]) * cross
        cy += (ring[i][1] + ring[i + 1][1]) * cross
    if abs(a) < 1e-12:
        return ring[0]
    a *= 0.5
    return (cx / (6 * a), cy / (6 * a))


PHOTO = {
    "320302": ("鼓楼区", "#C1503A", "老城中心 · 彭城广场"),
    "320303": ("云龙区", "#CE7546", "云龙山 · 户部山 · 回龙窝"),
    "320305": ("贾汪区", "#C99A52", "潘安湖 · 马庄香包"),
    "320311": ("泉山区", "#B4573B", "云龙湖 · 淮塔"),
    "320312": ("铜山区", "#AE6544", "汉王 · 楚王山汉墓"),
    "320321": ("丰县", "#C9A25C", "刘邦故里 · 丰县琴书"),
    "320322": ("沛县", "#BC8A4B", "沛公故里 · 鼋汁狗肉"),
    "320324": ("睢宁县", "#C5934F", "睢宁儿童画 · 方言保护计划"),
    "320381": ("新沂市", "#BFA061", "窑湾古镇 · 马陵山"),
    "320382": ("邳州市", "#B47E48", "邳州银杏 · 柳琴戏"),
}


def main():
    raw = json.load(open(SRC, encoding="utf-8"))
    feats = []
    total_pts = 0
    for f in raw["features"]:
        props = f["properties"]
        code = str(props["adcode"])
        name, color, sub = PHOTO.get(code, (props["name"], "#B47E48", ""))
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        out_polys = []
        for poly in polys:
            rings = []
            for ri, ring in enumerate(poly):
                simp = simplify_ring(ring, TOL)
                if simp:
                    rings.append(simp)
            if rings:
                out_polys.append(rings)
        if not out_polys:
            continue
        biggest = max(out_polys, key=lambda r: len(r[0]))
        ring = biggest[0]
        cx, cy = centroid(ring)
        npts = sum(len(r) for p in out_polys for r in p)
        total_pts += npts
        feats.append({
            "code": code, "name": name, "sub": sub, "color": color,
            "center": [round(cx, 4), round(cy, 4)],
            "polys": out_polys,
        })
        print(code, name, "polys=%d pts=%d" % (len(out_polys), npts))

    lons = [p[0] for f in feats for poly in f["polys"] for r in poly for p in r]
    lats = [p[1] for f in feats for poly in f["polys"] for r in poly for p in r]
    meta = {"lonMin": min(lons), "lonMax": max(lons),
            "latMin": min(lats), "latMax": max(lats),
            "latRef": (min(lats) + max(lats)) / 2.0}

    js = "window.__GEO__ = " + json.dumps(
        {"meta": meta, "districts": feats}, ensure_ascii=False,
        separators=(",", ":")) + ";\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fp:
        fp.write(js)
    print("total pts", total_pts, "bytes", len(js))
    print("bounds", meta)


main()
