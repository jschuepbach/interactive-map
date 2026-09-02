#!/usr/bin/env python3
"""Show places that still have no note, in workable portions.

  python3 scripts/notes-todo.py                 # next 15, mixed
  python3 scripts/notes-todo.py 30              # next 30
  python3 scripts/notes-todo.py --group Coffee  # only one group
  python3 scripts/notes-todo.py --all           # everything, grouped
  python3 scripts/notes-todo.py --count         # just the numbers

A block marked with <!-- skip --> is treated as done and never shown again.
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTES = ROOT / "notes.md"

def sections(text):
    out, marks = [], list(re.finditer(r"^##\s+(.+?)\s*$", text, re.M))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((m.group(1), text[m.start():end]))
    return out

def body_of(block):
    rest = block.split("\n", 1)[1] if "\n" in block else ""
    return re.sub(r"<!--[\s\S]*?-->", "", rest).strip()

def main(argv):
    limit, group_filter, show_all, count_only = 15, None, False, False
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--group":
            i += 1; group_filter = argv[i].lower()
        elif a == "--all":
            show_all = True
        elif a == "--count":
            count_only = True
        else:
            rest.append(a)
        i += 1
    if rest:
        limit = int(rest[0])

    text = NOTES.read_text()
    places = {p.get("name", ""): p for p in json.loads((ROOT / "data.json").read_text())}

    todo = []
    done = 0
    for name, block in sections(text):
        if body_of(block) or "<!-- skip -->" in block:
            done += 1
            continue
        p = places.get(name, {})
        todo.append((p.get("group") or p.get("category") or "?", name,
                     (p.get("note") or "").strip()))

    if count_only:
        print("%d done, %d open, %d total" % (done, len(todo), done + len(todo)))
        return 0

    if group_filter:
        todo = [t for t in todo if group_filter in t[0].lower()]
    todo.sort(key=lambda t: (t[0], t[1]))
    shown = todo if (show_all or group_filter) else todo[:limit]

    current = None
    for grp, name, addr in shown:
        if grp != current:
            print("\n# %s" % grp)
            current = grp
        addr = re.sub(r",?\s*\d{5},?\s*Barcelona\s*$", "", addr)
        addr = addr[:60]
        print("- %s%s" % (name, ("  (%s)" % addr) if addr else ""))
    print("\n%d shown, %d open of %d" % (len(shown), len(todo), done + len(todo)),
          file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
