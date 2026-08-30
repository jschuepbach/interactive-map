#!/usr/bin/env python3
"""Write one note into notes.md.

  python3 scripts/add-note.py "nomad lab" "Winzig, kein Laptop. Filter nehmen."
  python3 scripts/add-note.py --list gracia        # what is still unwritten there

Name matching is fuzzy: case and accents are ignored, and a partial name is
enough as long as it is unambiguous. Ambiguous input prints the candidates and
changes nothing. An existing note is replaced, the scaffold comment is kept.
"""
import json, pathlib, re, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTES = ROOT / "notes.md"

SPECIAL = str.maketrans({"ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "ß": "ss",
                         "ł": "l", "Ł": "l", "đ": "d", "'": "", "\u2019": ""})
def fold(s):
    s = unicodedata.normalize("NFD", (s or "").translate(SPECIAL))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()

def sections(text):
    """[(heading, start_index_of_heading_line, end_index)] over the raw text."""
    out, marks = [], [m for m in re.finditer(r"^##\s+(.+?)\s*$", text, re.M)]
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((m.group(1), m.start(), end))
    return out

def body_of(block):
    return re.sub(r"<!--[\s\S]*?-->", "", block.split("\n", 1)[1] if "\n" in block else "").strip()

def main(argv):
    if not NOTES.exists():
        sys.exit("notes.md not found — run scripts/build-notes-scaffold.py first")
    text = NOTES.read_text()
    secs = sections(text)

    if argv and argv[0] == "--list":
        needle = fold(argv[1]) if len(argv) > 1 else ""
        places = json.loads((ROOT / "data.json").read_text())
        hood = {p.get("name", ""): (p.get("note") or "") for p in places}
        n = 0
        for name, s, e in secs:
            if body_of(text[s:e]):
                continue
            if needle and needle not in fold(name) and needle not in fold(hood.get(name, "")):
                continue
            print(name)
            n += 1
        print("\n%d without a note" % n, file=sys.stderr)
        return 0

    if len(argv) < 2:
        sys.exit(__doc__)
    query, note = fold(argv[0]), " ".join(argv[1:]).strip()

    exact = [s for s in secs if fold(s[0]) == query]
    hits = exact or [s for s in secs if query in fold(s[0])]
    if not hits:
        sys.exit('no place matches "%s"' % argv[0])
    if len(hits) > 1:
        print("ambiguous, matches:", file=sys.stderr)
        for name, _, _ in hits:
            print("  " + name, file=sys.stderr)
        sys.exit(2)

    name, start, end = hits[0]
    block = text[start:end]
    head, rest = block.split("\n", 1) if "\n" in block else (block, "")
    comment = "\n".join(re.findall(r"^<!--.*?-->$", rest, re.M))
    rebuilt = head + "\n" + (comment + "\n" if comment else "") + note + "\n\n"
    NOTES.write_text(text[:start] + rebuilt + text[end:])
    print('%s <- "%s"' % (name, note[:60] + ("..." if len(note) > 60 else "")))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
