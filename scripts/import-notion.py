#!/usr/bin/env python3
"""Write the Notion table back into data.json, notes.md, links.json and overrides.json.

  python3 scripts/import-notion.py ~/Downloads/places.csv          # show the plan
  python3 scripts/import-notion.py ~/Downloads/places.csv --apply  # write it

Export the database in Notion first: ··· -> Export -> Markdown & CSV, and pick
the CSV. A JSON file with the same column names works too.

What each column does:

  Status "löschen"  drops the place from data.json and its section from notes.md
  Notiz             becomes the personal note in notes.md, an empty cell clears it
  Adresse           becomes the address in data.json, which also decides the barrio
  Maps              the lat,lng in the link moves the pin
  Website/Instagram go to links.json
  Tags              go to overrides.json, but only when the keyword rules in
                    index.html would derive something else on their own

Rows are matched by name. A renamed row still matches through its coordinates,
so renaming in Notion renames the place here. A row that matches nothing and
carries coordinates is added as a new place. Places missing from the file are
reported and kept: only "löschen" deletes.

Nothing is written without --apply.
"""
import csv, json, pathlib, re, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, NOTES = ROOT / "data.json", ROOT / "notes.md"
LINKS, OVERRIDES = ROOT / "links.json", ROOT / "overrides.json"
SRC = (ROOT / "index.html").read_text()

SPECIAL = str.maketrans({"ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "ß": "ss",
                         "ł": "l", "Ł": "l", "đ": "d", "'": "", "’": ""})
def fold(s):
    s = unicodedata.normalize("NFD", (s or "").translate(SPECIAL))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

# --- the app's own category rules, so a Tags cell that agrees with them needs
#     no override entry and overrides.json stays as small as it can be ---
def parse_rules():
    block = re.search(r"const CATEGORY_RULES = \[(.*?)\n    \];", SRC, re.S).group(1)
    return [(key, re.findall(r"'([^']*)'", kws))
            for key, kws in re.findall(r"\{ key: '([^']+)',\s*keywords: \[(.*?)\] \}", block, re.S)]
RULES = parse_rules()
VALID_TAGS = ["Coffee", "Brunch", "Sushi", "Asian", "Tapas", "Vegan",
              "Bakery", "Pizza", "Burger", "Bar", "Wine", "Restaurant"]

def word(hay, kw):
    return re.search(r"(?<![0-9a-zà-ÿ])" + re.escape(kw) + r"s?(?![0-9a-zà-ÿ])", hay) is not None

def derived_tags(place):
    base = place.get("group") or place.get("category") or "Restaurant"
    if base != "Restaurant":
        return [base]
    hay = ((place.get("name") or "") + " " + (place.get("note") or "")).lower()
    return [k for k, kws in RULES if any(word(hay, kw) for kw in kws)] or ["Restaurant"]

def as_url(value):
    """A cell typed as "joncake.com" has to become a real link, not a relative one."""
    v = (value or "").strip()
    return v if not v or re.match(r"^https?://", v, re.I) else "https://" + v

def coords_of(maps_url):
    m = re.search(r"[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)", maps_url or "")
    return (float(m.group(1)), float(m.group(2))) if m else None

def read_rows(path):
    text = pathlib.Path(path).read_text()
    if path.lower().endswith(".json"):
        raw = json.loads(text)
        raw = raw if isinstance(raw, list) else raw.get("results", [])
    else:
        raw = list(csv.DictReader(text.splitlines()))
    rows = []
    for r in raw:
        get = lambda *names: next((str(r[n]).strip() for n in names
                                   if r.get(n) not in (None, "")), "")
        tags = get("Tags")
        rows.append({
            "name": get("Name"),
            "tags": [t.strip() for t in tags.split(",") if t.strip()] if isinstance(tags, str) else tags,
            "address": get("Adresse", "Address"),
            "note": get("Notiz", "Note"),
            "status": get("Status").lower(),
            "maps": get("Maps"),
            "website": get("Website"),
            "instagram": get("Instagram"),
        })
    return [r for r in rows if r["name"]]

def sections(text):
    out, marks = [], list(re.finditer(r"^##\s+(.+?)\s*$", text, re.M))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((m.group(1).strip(), m.start(), end))
    return out

def main(argv):
    if not argv:
        sys.exit(__doc__)
    apply = "--apply" in argv
    path = next(a for a in argv if not a.startswith("--"))

    rows = read_rows(path)
    places = json.loads(DATA.read_text())
    by_name = {fold(p["name"]): p for p in places}
    by_coord = {(round(p["lat"], 5), round(p["lng"], 5)): p for p in places}

    OVR_BEFORE = {k: v for k, v in (json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}).items()
                  if not k.startswith("_") and isinstance(v, list)}

    plan = {"delete": [], "rename": [], "move": [], "address": [], "note": [],
            "links": [], "tags": [], "new": [], "skipped": []}
    seen, deletes = set(), set()
    notes_new, links_new, tags_new = {}, {}, {}

    for r in rows:
        place = by_name.get(fold(r["name"]))
        coords = coords_of(r["maps"])
        if not place and coords:
            place = by_coord.get((round(coords[0], 5), round(coords[1], 5)))
            if place:
                plan["rename"].append("%s -> %s" % (place["name"], r["name"]))
                place["name"] = r["name"]
        if not place:
            if not coords:
                plan["skipped"].append("%s (new, but no lat,lng in Maps)" % r["name"])
                continue
            place = {"name": r["name"], "lat": coords[0], "lng": coords[1],
                     "category": (r["tags"] or ["Restaurant"])[0],
                     "group": (r["tags"] or ["Restaurant"])[0],
                     "note": r["address"], "url": ""}
            places.append(place)
            plan["new"].append(r["name"])
        seen.add(id(place))

        if r["status"].startswith("l"):          # "löschen"
            deletes.add(id(place))
            plan["delete"].append(place["name"])
            continue

        if coords and (round(place["lat"], 5), round(place["lng"], 5)) != (round(coords[0], 5), round(coords[1], 5)):
            plan["move"].append("%s -> %s,%s" % (place["name"], coords[0], coords[1]))
            place["lat"], place["lng"] = coords

        if r["address"] and r["address"] != (place.get("note") or ""):
            plan["address"].append("%s -> %s" % (place["name"], r["address"][:50]))
            place["note"] = r["address"]

        notes_new[place["name"]] = r["note"]
        if r["note"]:
            plan["note"].append(place["name"])

        own = {}
        website = as_url(r["website"])
        if website and website != (place.get("url") or ""):
            own["url"] = website
        if r["instagram"]:
            own["instagram"] = r["instagram"]
        if own:
            links_new[place["name"]] = own
            plan["links"].append(place["name"])

        wanted = [t for t in r["tags"] if t in VALID_TAGS]
        had = OVR_BEFORE.get(place["name"])
        if wanted and (wanted != derived_tags(place) or had):
            tags_new[place["name"]] = wanted
            if wanted != had:
                plan["tags"].append("%s -> %s" % (place["name"], ", ".join(wanted)))

    missing = [p["name"] for p in places if id(p) not in seen]
    places = [p for p in places if id(p) not in deletes]

    for key in ("delete", "rename", "move", "address", "tags", "new", "skipped"):
        for line in plan[key]:
            print("%-8s %s" % (key, line))
    print("\n%d rows: %d notes, %d link entries, %d tag overrides, %d deleted, %d new"
          % (len(rows), sum(1 for v in notes_new.values() if v), len(links_new),
             len(tags_new), len(plan["delete"]), len(plan["new"])), file=sys.stderr)
    if missing:
        print("not in the file, kept unchanged: %s" % ", ".join(missing[:8])
              + (" ..." if len(missing) > 8 else ""), file=sys.stderr)
    if not apply:
        print("\ndry run — nothing written. Add --apply.", file=sys.stderr)
        return 0

    DATA.write_text(json.dumps(places, ensure_ascii=False, indent=2) + "\n")

    # notes.md: keep the file's own order and its scaffold comments, replace
    # only the text under each heading
    live = {p["name"] for p in places}
    text = NOTES.read_text()
    for name, start, end in reversed(sections(text)):
        block = text[start:end]
        head, rest = block.split("\n", 1) if "\n" in block else (block, "")
        if name not in live:                              # Status "löschen"
            text = text[:start] + text[end:]
            continue
        comment = "\n".join(re.findall(r"^<!--.*?-->$", rest, re.M))
        comment = "\n".join(c for c in comment.split("\n") if c and "<!-- skip -->" not in c)
        body = notes_new.get(name, re.sub(r"<!--[\s\S]*?-->", "", rest).strip())
        text = text[:start] + head + "\n" + (comment + "\n" if comment else "") + \
            (body + "\n" if body else "\n") + "\n" + text[end:]

    # places added in Notion have no heading yet
    have = {n for n, _, _ in sections(text)}
    for p in places:
        if p["name"] in have:
            continue
        text = text.rstrip("\n") + "\n\n## %s\n<!-- %s | %s -->\n%s\n" % (
            p["name"], p.get("group") or "Restaurant", (p.get("note") or "")[:70],
            notes_new.get(p["name"], ""))
    NOTES.write_text(text.rstrip("\n") + "\n\n")   # the file ends on a blank line

    current = json.loads(LINKS.read_text()) if LINKS.exists() else {}
    keep = {k: v for k, v in current.items() if k.startswith("_")}
    keep.update(links_new)
    LINKS.write_text(json.dumps(
        {k: keep[k] for k in sorted(keep, key=lambda k: (not k.startswith("_"), fold(k)))},
        ensure_ascii=False, indent=2) + "\n")

    current = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}
    keep = {k: v for k, v in current.items() if k.startswith("_")}
    keep.update(tags_new)
    OVERRIDES.write_text(json.dumps(
        {k: keep[k] for k in sorted(keep, key=lambda k: (not k.startswith("_"), fold(k)))},
        ensure_ascii=False, indent=2) + "\n")

    print("\nwritten. Run scripts/build-review.py to refresh docs/places-review.html.",
          file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
