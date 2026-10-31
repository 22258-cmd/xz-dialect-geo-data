#!/usr/bin/env python3
"""从权威边界派生出精简版，并给两份产物做校验和。

为什么不是原来那个 build_geo.py：
  · 它的输入是硬编码的 `D:\\workbuddy\\...\\xz.json`，那个目录已经不在了 —— 谁都跑不出仓库里那份数据；
  · 它的输出路径也在仓库外，写完的东西没人认领；
  · 它把颜色与文案硬编码进脚本，数据与表现混在一起。
所以这里改成：**输入输出都在仓库内**，且 `--check` 能在干净克隆上验证产物没被手改过。

用法：
    python tools/derive_lite.py            # 生成 data/geo.lite.js 与 data/SHA256SUMS
    python tools/derive_lite.py --check    # 只比对，不写文件；不一致退出码 1
    python tools/derive_lite.py --tol 0.006

零依赖（只用标准库）。
"""
import argparse
import hashlib
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FULL = os.path.join(ROOT, "data", "geo.full.js")
LITE = os.path.join(ROOT, "data", "geo.lite.js")
SUMS = os.path.join(ROOT, "data", "SHA256SUMS")

DEFAULT_TOL = 0.0045      # Douglas-Peucker 容差（度），约 500 m
MIN_RING_PTS = 5          # 精简后少于这个点数的环直接丢掉（碎岛）


def load_global_js(path, var_name):
    """读 `window.XXX = {...};` 这种形态的文件，返回解析后的对象。"""
    with open(path, encoding="utf-8") as fp:
        text = fp.read()
    start = text.index("{")
    end = text.rindex("}") + 1
    return json.loads(text[start:end])


def dump_global_js(path, var_name, obj):
    with open(path, "w", encoding="utf-8") as fp:
        fp.write("window.%s=%s\n" % (var_name, json.dumps(obj, ensure_ascii=False, separators=(",", ":"))))


def _perp_dist(pt, a, b):
    (x, y), (ax, ay), (bx, by) = pt, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(x - ax, y - ay)
    t = ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(x - (ax + t * dx), y - (ay + t * dy))


def rdp(points, tol):
    """Douglas-Peucker：迭代版，避免深递归。"""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi <= lo + 1:
            continue
        dmax, idx = -1.0, -1
        a, b = points[lo], points[hi]
        for i in range(lo + 1, hi):
            d = _perp_dist(points[i], a, b)
            if d > dmax:
                dmax, idx = d, i
        if dmax > tol:
            keep[idx] = True
            stack.append((lo, idx))
            stack.append((idx, hi))
    return [p for p, k in zip(points, keep) if k]


def simplify(data, tol):
    out = dict(data)
    districts = []
    for d in data["districts"]:
        polygons = []
        for polygon in d["polys"]:          # polys[] 是多边形，每个多边形含若干环
            rings = []
            for ring in polygon:
                s = rdp([tuple(pt) for pt in ring], tol)
                if len(s) >= MIN_RING_PTS:
                    rings.append([list(pt) for pt in s])
            if rings:
                polygons.append(rings)
        nd = dict(d)
        # 必须保持与权威版**同样的嵌套层级** districts[].polys[][]（多边形 → 环 → 点）。
        # 压平一层看着无害，但消费方是按层级遍历的，schema 一变就悄悄错。
        nd["polys"] = polygons
        districts.append(nd)
    out["districts"] = districts
    return out


def points_of(data):
    """数到最里层的顶点。层级是 多边形 → 环 → 点，别只数到环。"""
    n = 0
    for d in data["districts"]:
        for polygon in d["polys"]:
            for ring in polygon:
                n += len(ring)
    return n


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="从 geo.full.js 派生 geo.lite.js 并校验")
    ap.add_argument("--tol", type=float, default=DEFAULT_TOL, help="RDP 容差（度），默认 %(default)s")
    ap.add_argument("--check", action="store_true", help="只比对校验和，不写任何文件")
    args = ap.parse_args()

    for p in (FULL,):
        if not os.path.exists(p):
            print("[derive] 缺少输入文件 %s" % p, file=sys.stderr)
            return 2

    full = load_global_js(FULL, "XZ_GEO")
    lite = simplify(full, args.tol)

    if args.check:
        if not os.path.exists(LITE) or not os.path.exists(SUMS):
            print("[derive] FAIL —— 缺 data/geo.lite.js 或 data/SHA256SUMS，先跑一次不带 --check 的生成",
                  file=sys.stderr)
            return 1
        dump = os.path.join(os.path.dirname(LITE), ".geo.lite.tmp.js")
        dump_global_js(dump, "XZ_GEO_LITE", lite)
        want = {}
        with open(SUMS, encoding="utf-8") as fp:
            for line in fp:
                if line.strip():
                    digest, _, name = line.strip().partition("  ")
                    want[name] = digest
        got = {
            "geo.full.js": sha256(FULL),
            "geo.lite.js": sha256(dump),
            "geo.lite.committed.js": sha256(LITE),
        }
        os.remove(dump)
        bad = []
        for name in ("geo.full.js", "geo.lite.js"):
            if want.get(name) != got[name]:
                bad.append("%s: 记录=%s 实际=%s" % (name, (want.get(name) or "-")[:12], got[name][:12]))
        if got["geo.lite.js"] != got["geo.lite.committed.js"]:
            bad.append("data/geo.lite.js 的内容与按当前 --tol 派生出的结果不一致（被手改过？）")
        if bad:
            print("[derive] FAIL", file=sys.stderr)
            for b in bad:
                print("  - " + b, file=sys.stderr)
            return 1
        print("[derive] OK —— 两份产物与 SHA256SUMS 一致（full %d 点 / lite %d 点）"
              % (points_of(full), points_of(lite)))
        return 0

    dump_global_js(LITE, "XZ_GEO_LITE", lite)
    with open(SUMS, "w", encoding="utf-8", newline="\n") as fp:
        fp.write("%s  geo.full.js\n" % sha256(FULL))
        fp.write("%s  geo.lite.js\n" % sha256(LITE))
    print("[derive] 已生成 data/geo.lite.js（tol=%g，%d 区 / %d → %d 点）并更新 data/SHA256SUMS"
          % (args.tol, len(full["districts"]), points_of(full), points_of(lite)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
