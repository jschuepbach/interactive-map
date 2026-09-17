#!/usr/bin/env python3
"""Write notion-snapshot.json into data.json and notes.md.

  python3 scripts/apply-notion.py          # show the plan
  python3 scripts/apply-notion.py --apply  # write it

The snapshot is the Notion table, one entry per place:

  cuisine   the Cuisine column, in Notion's order. First tag colours the pin.
  why       the "Why it's good" column. Becomes the note in notes.md.
  tip       the "My suggestion" column. Becomes "tip" in data.json.
  bucket    true when "Why it's good" still reads "Still on my bucket list".
            Those places get no note, so the written-about filter keeps meaning
            "Jan has been there".

Places missing from the snapshot are dropped, as agreed: Notion is the list.
Names are matched loosely (accents, case, punctuation), and the snapshot's
spelling wins, so a rename in Notion renames the place here.
"""
import json, pathlib, re, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, NOTES = ROOT / "data.json", ROOT / "notes.md"
LINKS, SNAP = ROOT / "links.json", ROOT / "notion-snapshot.json"

HEADER = """<!-- Deine Notizen. Eine Ueberschrift pro Ort, darunter freier Text.
     Gepflegt wird der Text in Notion, Spalte "Why it's good".
     Diese Datei schreibt scripts/apply-notion.py aus notion-snapshot.json.
     Die App liest sie direkt, kein Build-Schritt: speichern, neu laden.
     Orte ohne Text darunter stehen noch auf der Bucket-Liste. -->
"""

SPECIAL = str.maketrans({"ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "ß": "ss",
                         "ł": "l", "Ł": "l", "đ": "d", "'": "", "’": ""})
def fold(s):
    s = unicodedata.normalize("NFD", (s or "").translate(SPECIAL))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def main(argv):
    apply = "--apply" in argv
    snap = json.loads(SNAP.read_text())
    places = json.loads(DATA.read_text())
    links = json.loads(LINKS.read_text())

    by_fold = {fold(name): (name, row) for name, row in snap.items()}
    kept, dropped, renamed = [], [], []

    for p in places:
        hit = by_fold.pop(fold(p["name"]), None)
        if not hit:
            dropped.append(p["name"])
            continue
        name, row = hit
        if name != p["name"]:
            renamed.append((p["name"], name))
            for key in list(links):
                if fold(key) == fold(p["name"]) and key != name:
                    links[name] = links.pop(key)
            p["name"] = name
        p["groups"] = row["cuisine"]
        p["group"] = row["cuisine"][0]
        if row["tip"]:
            p["tip"] = row["tip"]
        else:
            p.pop("tip", None)
        if row["bucket"]:
            p["bucket"] = True
        else:
            p.pop("bucket", None)
        kept.append(p)

    missing = sorted(by_fold.values())

    body = [HEADER]
    for p in kept:
        row = snap[p["name"]]
        body.append("\n## %s\n<!-- %s -->\n" % (p["name"], ", ".join(row["cuisine"])))
        if row["why"]:
            body.append(row["why"] + "\n")

    print("%d places kept, %d dropped, %d renamed" % (len(kept), len(dropped), len(renamed)))
    for old, new in renamed:
        print("  renamed  %s -> %s" % (old, new))
    for name in dropped:
        print("  dropped  %s" % name)
    for name, _ in missing:
        print("  in Notion but not here, needs coordinates: %s" % name)
    print("%d notes written, %d still on the bucket list, %d tips"
          % (sum(1 for p in kept if snap[p["name"]]["why"]),
             sum(1 for p in kept if snap[p["name"]]["bucket"]),
             sum(1 for p in kept if snap[p["name"]]["tip"])))

    if not apply:
        print("\nnothing written, pass --apply")
        return 0

    DATA.write_text(json.dumps(kept, ensure_ascii=False, indent=2) + "\n")
    NOTES.write_text("".join(body))
    LINKS.write_text(json.dumps(links, ensure_ascii=False, indent=2) + "\n")
    print("\nwritten: data.json, notes.md, links.json")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
