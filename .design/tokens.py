# -*- coding: utf-8 -*-
"""Offline: derive design tokens from the pruned frame subtrees."""
import json, glob, io
from collections import Counter

colors, texts, radii, shadows, gaps, pads = Counter(), Counter(), Counter(), Counter(), Counter(), Counter()

def hexof(c, a=1.0):
    r, g, b = (int(round(c[k] * 255)) for k in ("r", "g", "b"))
    al = c.get("a", 1) * a
    return "#%02X%02X%02X" % (r, g, b) + ("" if al >= 0.999 else "%02X" % int(round(al * 255)))

def walk(n):
    for f in n.get("fills", []) + n.get("strokes", []):
        if f.get("visible", True) and f.get("type") == "SOLID":
            colors[hexof(f["color"], f.get("opacity", 1))] += 1
    s = n.get("style")
    if s:
        texts["%s %s/%s w%s ls%s" % (s.get("fontFamily"), s.get("fontSize"),
              round(s.get("lineHeightPx", 0), 1), s.get("fontWeight"),
              round(s.get("letterSpacing", 0), 2))] += 1
    if n.get("cornerRadius") is not None:
        radii[n["cornerRadius"]] += 1
    for e in n.get("effects", []):
        if e.get("visible", True) and e.get("type", "").endswith("SHADOW"):
            o = e.get("offset", {})
            shadows["%s %s %s %s %s" % (e["type"], o.get("x"), o.get("y"),
                    e.get("radius"), hexof(e["color"], 1))] += 1
    if n.get("itemSpacing"):
        gaps[n["itemSpacing"]] += 1
    for k in ("paddingLeft", "paddingRight", "paddingTop", "paddingBottom"):
        if n.get(k):
            pads[n[k]] += 1
    for c in n.get("children", []):
        walk(c)

for p in glob.glob(".design/cache/nodes/*.json"):
    walk(json.load(open(p, encoding="utf-8")))

def top(c, n=40):
    return [{"value": str(k), "uses": v} for k, v in c.most_common(n)]

out = {"colors": top(colors, 60), "typography": top(texts, 40), "radii": top(radii),
       "shadows": top(shadows, 20), "gaps": top(gaps, 30), "paddings": top(pads, 30)}
with io.open(".design/cache/tokens.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
for k, v in out.items():
    print(k, len(v), [x["value"] for x in v[:8]])
