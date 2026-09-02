#!/usr/bin/env python3
"""Dump every place as one JSON row, ready to push into a Notion database.

  python3 scripts/export-notion.py > places.json

Category rules, neighbourhood postcodes and the proximity fallback are read out
of index.html, so a row says exactly what the app shows. Personal notes come
from notes.md, websites and Instagram from links.json.
Run: python3 scripts/export-notion.py [outfile]
"""
import json, pathlib, re, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = (ROOT / "index.html").read_text()

def parse_rules():
    block = re.search(r"const CATEGORY_RULES = \[(.*?)\n    \];", SRC, re.S).group(1)
    return [(key, re.findall(r"'([^']*)'", kws))
            for key, kws in re.findall(r"\{ key: '([^']+)',\s*keywords: \[(.*?)\] \}", block, re.S)]

def parse_hoods():
    block = re.search(r"const HOODS = \[(.*?)\n    \];", SRC, re.S).group(1)
    return [(hid, label, set(re.findall(r"'([^']*)'", codes)))
            for hid, label, codes in re.findall(
                r"\{ id: '([^']+)',\s*label: '([^']*)',\s*codes: \[(.*?)\] \}", block, re.S)]

def word(hay, kw):
    return re.search(r"(?<![0-9a-zà-ÿ])" + re.escape(kw) + r"s?(?![0-9a-zà-ÿ])", hay) is not None

def is_address(note):
    n = (note or "").strip()
    if len(n) < 15:
        return True
    return bool(re.search(r"\b08\d{3}\b", n) or re.search(r",\s*(barcelona|spain|espanya)\.?$", n, re.I))

def own_notes():
    text = (ROOT / "notes.md").read_text()
    out, marks = {}, list(re.finditer(r"^##\s+(.+?)\s*$", text, re.M))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = re.sub(r"<!--[\s\S]*?-->", "", text[m.end():end]).strip()
        if body:
            out[m.group(1).strip()] = body
    return out

def maps_url(p):
    return "https://www.google.com/maps/search/?api=1&query=%s,%s" % (p["lat"], p["lng"])

def instagram_url(handle):
    h = (handle or "").strip()
    if not h:
        return ""
    if re.match(r"^https?://", h, re.I):
        return h
    return "https://instagram.com/" + h.lstrip("@").rstrip("/")

RULES, HOODS = parse_rules(), parse_hoods()
places = json.loads((ROOT / "data.json").read_text())
ovr = json.loads((ROOT / "overrides.json").read_text()) if (ROOT / "overrides.json").exists() else {}
OVERRIDES = {k.lower(): v for k, v in ovr.items() if not k.startswith("_") and isinstance(v, list)}
links = json.loads((ROOT / "links.json").read_text()) if (ROOT / "links.json").exists() else {}
LINKS = {k.lower(): v for k, v in links.items() if not k.startswith("_") and isinstance(v, dict)}
NOTES = own_notes()

BY_CODE = {c: (hid, label) for hid, label, codes in HOODS for c in codes}

rows, pending = [], []
for p in places:
    name = p.get("name", "")
    base = p.get("group") or p.get("category") or "Restaurant"
    hay = (name + " " + (p.get("note") or "")).lower()
    manual = OVERRIDES.get(name.lower())
    if manual:
        tags = list(manual)
    elif base == "Restaurant":
        tags = [k for k, kws in RULES if any(word(hay, kw) for kw in kws)] or ["Restaurant"]
    else:
        tags = [base]

    code = re.search(r"\b(08\d{3})\b", p.get("note") or "")
    hood = BY_CODE.get(code.group(1)) if code else None

    own = LINKS.get(name.lower(), {})
    row = {
        "name": name,
        "tags": tags,
        "barrio": hood[1] if hood else "",
        "hood_id": hood[0] if hood else "",
        "hood_source": "postcode" if hood else "",
        "address": "" if not is_address(p.get("note")) else (p.get("note") or ""),
        "note": NOTES.get(name, ""),
        "maps": maps_url(p),
        "website": own.get("url") or p.get("url") or "",
        "instagram": instagram_url(own.get("instagram")),
        "lat": p.get("lat"), "lng": p.get("lng"),
    }
    # a place whose own note replaced the scraped address still needs the address
    if not row["address"] and is_address(p.get("note")):
        row["address"] = p.get("note") or ""
    rows.append(row)
    if not hood:
        pending.append(row)

# same fallback as the app: nearest centroid of the places placed by postcode
sums = {}
for r in rows:
    if not r["hood_id"]:
        continue
    s = sums.setdefault(r["hood_id"], {"lat": 0.0, "lng": 0.0, "n": 0, "label": r["barrio"]})
    s["lat"] += r["lat"]; s["lng"] += r["lng"]; s["n"] += 1
centroids = [(v["label"], v["lat"] / v["n"], v["lng"] / v["n"]) for v in sums.values()]
for r in pending:
    label, _, _ = min(centroids, key=lambda c: (r["lat"] - c[1]) ** 2 + (r["lng"] - c[2]) ** 2)
    r["barrio"], r["hood_source"] = label, "proximity"

out = json.dumps(rows, ensure_ascii=False, indent=2)
if len(sys.argv) > 1:
    pathlib.Path(sys.argv[1]).write_text(out + "\n")
    print("%d rows -> %s" % (len(rows), sys.argv[1]), file=sys.stderr)
else:
    print(out)
