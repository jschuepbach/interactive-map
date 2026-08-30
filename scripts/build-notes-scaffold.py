#!/usr/bin/env python3
"""Create or extend notes.md — one heading per place, for Jan's own notes.

Never touches text that is already there: existing sections are kept verbatim,
only missing places are appended. Seeds the ten hand-written notes from
data.json on the first run.

Run: python3 scripts/build-notes-scaffold.py
"""
import json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTES = ROOT / "notes.md"
places = json.loads((ROOT / "data.json").read_text())

HEADER = """<!-- Deine Notizen. Eine Ueberschrift pro Ort, darunter freier Text.
     Die App liest diese Datei direkt, kein Build-Schritt: speichern, neu laden.
     Ueberschrift muss exakt dem Namen aus data.json entsprechen.
     Orte ohne Text darunter zeigen in der App keine Notiz an. -->
"""

def is_address(note):
    n = (note or "").strip()
    if len(n) < 15:
        return True
    return bool(re.search(r"\b08\d{3}\b", n) or re.search(r",\s*(barcelona|spain|espanya)\.?$", n, re.I))

existing_text = NOTES.read_text() if NOTES.exists() else ""
have = set(re.findall(r"^##\s+(.+?)\s*$", existing_text, re.M))

out = []
if not existing_text:
    out.append(HEADER)

added = 0
for p in places:
    name = p.get("name", "").strip()
    if not name or name in have:
        continue
    have.add(name)
    seed = "" if is_address(p.get("note")) else p["note"].strip()
    hint = (p.get("note") or "").strip()
    out.append("\n## %s\n<!-- %s | %s -->\n%s\n" % (name, p.get("group", ""), hint[:70], seed))
    added += 1

if out:
    with NOTES.open("a" if existing_text else "w") as fh:
        fh.write("".join(out))
print("notes.md: %d places added, %d total headings" % (added, len(have)))
