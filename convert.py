"""
Google Maps → data.json converter
Reads gmaps-list.json (output of extract_gmaps.js) and writes data.json,
filtered to the Barcelona metro area and geocoded where coordinates are missing.

Usage:
  python3 convert.py                   # reads gmaps-list.json in this folder
  python3 convert.py path/to/file.json # or point to another file
"""

import json, sys, time, urllib.request, urllib.parse, os

# ── Config ────────────────────────────────────────────────────────────────────
BBOX = dict(minLat=41.30, maxLat=41.50, minLng=2.00, maxLng=2.35)
INPUT  = sys.argv[1] if len(sys.argv) > 1 else "gmaps-list.json"
OUTPUT = "data.json"

def in_bbox(lat, lng):
    return (lat is not None and lng is not None
            and BBOX["minLat"] <= lat <= BBOX["maxLat"]
            and BBOX["minLng"] <= lng <= BBOX["maxLng"])

def geocode_nominatim(name, address=""):
    """Free geocoding via Nominatim — rate-limited to 1 req/s."""
    query = f"{name}, Barcelona, Spain" if "barcelona" not in (name+address).lower() else f"{name}, {address}"
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        "q": query, "format": "json", "limit": 1,
        "viewbox": "2.00,41.30,2.35,41.50", "bounded": 1
    })
    req = urllib.request.Request(url, headers={"User-Agent": "bcn-map-converter/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.load(r)
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print(f"  ⚠ Geocode failed for "{name}": {e}")
    return None, None

# ── Load input ────────────────────────────────────────────────────────────────
if not os.path.exists(INPUT):
    print(f"❌  File not found: {INPUT}")
    print("   Run extract_gmaps.js in your browser first, then drop gmaps-list.json here.")
    sys.exit(1)

with open(INPUT, encoding="utf-8") as f:
    raw = json.load(f)

print(f"✓  Loaded {len(raw)} places from {INPUT}")

# ── Filter & geocode ──────────────────────────────────────────────────────────
bcn   = []   # already in Barcelona
other = []   # no coords or outside bbox

for p in raw:
    lat = p.get("lat")
    lng = p.get("lng")
    if in_bbox(lat, lng):
        bcn.append(p)
    else:
        other.append(p)

print(f"   {len(bcn)} already in Barcelona bbox")
print(f"   {len(other)} outside or missing coords → will attempt geocoding\n")

geocoded = []
for i, p in enumerate(other, 1):
    print(f"  [{i}/{len(other)}] Geocoding: {p['name']}")
    lat, lng = geocode_nominatim(p["name"], p.get("note", ""))
    time.sleep(1.1)  # Nominatim rate limit: 1 req/s
    if in_bbox(lat, lng):
        p["lat"] = lat
        p["lng"] = lng
        geocoded.append(p)
        print(f"         ✓ ({lat:.5f}, {lng:.5f})")
    else:
        print(f"         ✗ not in Barcelona, skipped")

all_bcn = bcn + geocoded
print(f"\n✓  {len(all_bcn)} Barcelona places total")

# ── Preview & confirm ─────────────────────────────────────────────────────────
print("\n── Preview (first 30) ───────────────────────────────────────────────────")
for i, p in enumerate(all_bcn[:30], 1):
    print(f"  {i:3}. {p['name'][:50]:<50}  ({p['lat']:.4f}, {p['lng']:.4f})")
if len(all_bcn) > 30:
    print(f"       … and {len(all_bcn) - 30} more")

print()
answer = input(f"Write {len(all_bcn)} places to {OUTPUT}? [Y/n] ").strip().lower()
if answer in ("", "y", "yes"):
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(all_bcn, f, ensure_ascii=False, indent=2)
    print(f"✓  {OUTPUT} written — refresh the map at http://localhost:8000")
else:
    print("Aborted.")
