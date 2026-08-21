# -*- coding: utf-8 -*-
"""Offline: cut pruned per-frame subtrees out of the cached file.json."""
import json, io, os

TARGETS = {
    "landing-desktop":        "90:880",
    "navbar-variant5":        "1086:4929",
    "create-project":         "788:5094",
    "create-project-mobile":  "1227:9974",
    "cards-images":           "788:6243",
    "projects-grid":          "484:1104",
    "projects-grid-mobile":   "674:2534",
    "profile-personal":       "1127:10768",
    "profile-mobile":         "1311:7203",
    "profile-edit-name":      "1202:6364",
    "profile-edit-name-mobile": "1311:11006",
    "profile-save":           "1227:9790",
    "profile-save-mobile":    "1311:11272",
    "profile-delete":         "1202:6227",
    "profile-delete-mobile":  "1311:11406",
}

KEEP = ("name","type","absoluteBoundingBox","layoutMode","itemSpacing","counterAxisSpacing",
        "paddingLeft","paddingRight","paddingTop","paddingBottom","primaryAxisAlignItems",
        "counterAxisAlignItems","primaryAxisSizingMode","counterAxisSizingMode","layoutWrap",
        "layoutSizingHorizontal","layoutSizingVertical","layoutGrow","constraints","fills",
        "strokes","strokeWeight","strokeAlign","cornerRadius","rectangleCornerRadii","effects",
        "style","characters","opacity","clipsContent","visible","componentId")

def prune(n):
    o = {"id": n["id"]}
    for k in KEEP:
        if k in n and n[k] not in (None, [], {}):
            o[k] = n[k]
    kids = [prune(c) for c in n.get("children", []) if c.get("visible", True)]
    if kids:
        o["children"] = kids
    return o

def index(node, acc):
    acc[node["id"]] = node
    for c in node.get("children", []):
        index(c, acc)

doc = json.load(open(".design/cache/file.json", encoding="utf-8"))
by_id = {}
index(doc["document"], by_id)
os.makedirs(".design/cache/nodes", exist_ok=True)
for slug, nid in TARGETS.items():
    n = by_id.get(nid)
    if n is None:
        print("MISSING", slug, nid); continue
    p = f".design/cache/nodes/{slug}.json"
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(prune(n), f, ensure_ascii=False, indent=1)
    print(f"{slug:26} {nid:14} {os.path.getsize(p)//1024} KB")
