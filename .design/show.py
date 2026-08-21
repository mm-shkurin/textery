# -*- coding: utf-8 -*-
"""Offline: print a readable layout outline of a cached frame."""
import json, sys, io

def hexof(c):
    return "#%02X%02X%02X" % tuple(int(round(c[k]*255)) for k in ("r","g","b"))

def fill(n):
    for f in n.get("fills", []):
        if f.get("visible", True) and f.get("type") == "SOLID":
            return hexof(f["color"])
        if f.get("visible", True) and f.get("type","").startswith("GRADIENT"):
            return "grad"
    return ""

def line(n, d):
    b = n.get("absoluteBoundingBox") or {}
    s = n.get("style") or {}
    bits = []
    if b: bits.append("%dx%d @%d,%d" % (b.get("width",0), b.get("height",0), b.get("x",0), b.get("y",0)))
    if n.get("layoutMode"): bits.append("%s gap%s" % (n["layoutMode"][:3], n.get("itemSpacing",0)))
    pad = [n.get(k,0) for k in ("paddingTop","paddingRight","paddingBottom","paddingLeft")]
    if any(pad): bits.append("pad %s" % "/".join(str(int(p)) for p in pad))
    if n.get("cornerRadius"): bits.append("r%s" % round(n["cornerRadius"],1))
    f = fill(n)
    if f: bits.append(f)
    if s: bits.append("%s/%s w%s" % (s.get("fontSize"), round(s.get("lineHeightPx",0)), s.get("fontWeight")))
    txt = n.get("characters")
    if txt: bits.append("«%s»" % txt.replace("\n", " | ")[:70])
    return "%s%s [%s] %s" % ("  "*d, n.get("name"), n.get("type","")[:4], "  ".join(bits))

def walk(n, d, maxd, out):
    out.write(line(n, d) + "\n")
    if d < maxd:
        for c in n.get("children", []):
            walk(c, d+1, maxd, out)

slug = sys.argv[1]; maxd = int(sys.argv[2]) if len(sys.argv) > 2 else 4
root = json.load(open(f".design/cache/nodes/{slug}.json", encoding="utf-8"))
if len(sys.argv) > 3:
    def find(n, nid):
        if n["id"] == nid: return n
        for c in n.get("children", []):
            r = find(c, nid)
            if r: return r
    root = find(root, sys.argv[3]) or root
buf = io.StringIO(); walk(root, 0, maxd, buf)
io.open(".design/cache/_view.txt", "w", encoding="utf-8").write(buf.getvalue())
print(buf.getvalue())
