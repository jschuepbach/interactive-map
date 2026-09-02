#!/usr/bin/env python3
"""Ask OpenStreetMap which street address each pin actually sits on.

  python3 scripts/reverse-addresses.py report.json

The scraper took the address from the subtitle of a Google Maps list card,
which is often the neighbouring card's text — that is where "Domino's" and a
pharmacy came from. The coordinates in the same card came from its href and
are sound, so reverse geocoding the pin gives an address that at least belongs
to the building we point at.

Writes a report; applying it is a separate step, because a pin that is a few
metres off yields the neighbour's house number.
One request per second, which is what Nominatim asks for.
"""
import json, pathlib, sys, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = "InteractiveMap/1.0 (personal map project)"

def reverse(lat, lng):
    url = "https://nominatim.openstreetmap.org/reverse?" + urllib.parse.urlencode({
        "lat": lat, "lon": lng, "format": "json", "addressdetails": 1, "zoom": 18})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def main(argv):
    out_path = pathlib.Path(argv[0]) if argv else ROOT / "reverse-report.json"
    places = json.loads((ROOT / "data.json").read_text())
    rows = []
    for i, p in enumerate(places, 1):
        try:
            hit = reverse(p["lat"], p["lng"])
        except Exception as e:
            hit = {}
            print("  ! %s: %s" % (p["name"], e), file=sys.stderr)
        a = hit.get("address", {})
        road = a.get("road") or a.get("pedestrian") or a.get("footway") or ""
        nr, pc = a.get("house_number") or "", a.get("postcode") or ""
        city = a.get("city") or a.get("town") or a.get("village") or ""
        parts = [p["name"], road] + ([nr] if nr else []) + ([pc] if pc else []) + [city or "Barcelona"]
        rows.append({
            "name": p["name"], "stored_address": p.get("note", ""),
            "road": road, "house_number": nr, "postcode": pc, "city": city,
            "proposed": ", ".join(x for x in parts if x) if road else "",
            "suburb": a.get("suburb") or a.get("neighbourhood") or "",
        })
        print("%3d/%d %s -> %s" % (i, len(places), p["name"][:34], rows[-1]["proposed"][:70]),
              file=sys.stderr)
        time.sleep(1.1)
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    hits = sum(1 for r in rows if r["proposed"])
    print("\n%d von %d mit Strasse, Report: %s" % (hits, len(rows), out_path), file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
