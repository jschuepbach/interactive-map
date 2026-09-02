#!/usr/bin/env python3
"""Geocode every place by name and compare it with the coordinates we store.

  python3 scripts/check-addresses.py report.json

The scrape often kept the address of a neighbouring business, so the stored
address cannot be trusted on its own. Searching OpenStreetMap for the place
name inside a box around Barcelona gives an independent second opinion:

  ok       found within 150 m of our pin, the address we show is plausible
  moved    found, but far away — our pin or our address is likely wrong
  unknown  OpenStreetMap does not know the name, needs a human

One request per second, which is what Nominatim asks for.
"""
import json, pathlib, re, sys, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = "InteractiveMap/1.0 (personal map project)"
BOX = "1.95,41.55,2.40,41.28"           # left,top,right,bottom around Barcelona

def clean(name):
    """Drop the noise that keeps a search from matching: category words the
    owner never put on the door, and our own disambiguating suffixes."""
    n = re.sub(r"\s+(Barcelona|BCN)\b", "", name, flags=re.I)
    n = re.sub(r"\s+c/\s*\w+$", "", n)
    return n.strip() or name

def search(query):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        "q": query, "format": "json", "limit": 3, "addressdetails": 1,
        "viewbox": BOX, "bounded": 1})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def metres(a, b):
    import math
    R = 6371000
    dlat, dlng = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
    x = math.sin(dlat / 2) ** 2 + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))

def address_of(hit):
    a = hit.get("address", {})
    parts = [a.get("road"), a.get("house_number")]
    street = " ".join(p for p in parts if p)
    if a.get("house_number") and a.get("road"):
        street = "%s, %s" % (a["road"], a["house_number"])
    bits = [hit.get("name") or "", street, a.get("postcode", ""), "Barcelona"]
    return ", ".join(b for b in bits if b)

def main(argv):
    out_path = pathlib.Path(argv[0]) if argv else ROOT / "address-report.json"
    places = json.loads((ROOT / "data.json").read_text())
    rows, counts = [], {"ok": 0, "moved": 0, "unknown": 0}
    for i, p in enumerate(places, 1):
        name = clean(p["name"])
        try:
            hits = search(name)
        except Exception as e:
            hits = []
            print("  ! %s: %s" % (p["name"], e), file=sys.stderr)
        best, dist = None, None
        for h in hits:
            d = metres((p["lat"], p["lng"]), (float(h["lat"]), float(h["lon"])))
            if dist is None or d < dist:
                best, dist = h, d
        state = "unknown" if best is None else ("ok" if dist <= 150 else "moved")
        counts[state] += 1
        rows.append({
            "name": p["name"], "state": state,
            "distance_m": None if dist is None else round(dist),
            "stored_address": p.get("note", ""),
            "stored": [p["lat"], p["lng"]],
            "found_address": address_of(best) if best else "",
            "found": [float(best["lat"]), float(best["lon"])] if best else None,
            "found_name": (best.get("name") or "") if best else "",
        })
        print("%3d/%d %-8s %s" % (i, len(places), state, p["name"]), file=sys.stderr)
        time.sleep(1.1)
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    print("\n%s -> %s" % (counts, out_path), file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
