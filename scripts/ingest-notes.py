#!/usr/bin/env python3
"""Write many notes, websites and Instagram handles in one go.

  python3 scripts/ingest-notes.py < block.txt
  pbpaste | python3 scripts/ingest-notes.py --dry     # preview, write nothing

Input is one place per line:

  Nomad Lab: Winzig, kein Laptop. Filter nehmen.
  slowmov | @slowmov slowmov.com Ruhige Ecke in Gracia, bestes Geback.
  hidden coffee: @hiddencoffeeroasters
  - Right Side: skip

A line whose part before ":" or "|" matches a place name starts a new entry.
Every other line is appended to the entry above it, so notes may span lines and
may contain colons themselves. Matching ignores case, accents and is happy with
a partial name; ambiguous or unknown names are reported and nothing is written
for them.

Inside a line, an @handle and any web address are pulled out and go to
links.json (@handle and instagram.com/... as the Instagram profile, everything
else as the website), the remaining words become the note in notes.md. A line
may carry only links, only a note, or both. "skip" or "-" marks a place as
deliberately without a note, so scripts/notes-todo.py stops offering it.
"""
import json, pathlib, re, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTES = ROOT / "notes.md"
LINKS = ROOT / "links.json"

SPECIAL = str.maketrans({"ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "ß": "ss",
                         "ł": "l", "Ł": "l", "đ": "d", "'": "", "’": ""})
def fold(s):
    s = unicodedata.normalize("NFD", (s or "").translate(SPECIAL))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def sections(text):
    out, marks = [], list(re.finditer(r"^##\s+(.+?)\s*$", text, re.M))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((m.group(1), m.start(), end))
    return out

def match(query, secs):
    q = fold(query)
    if not q:
        return []
    exact = [s for s in secs if fold(s[0]) == q]
    if exact:
        return exact
    starts = [s for s in secs if fold(s[0]).startswith(q)]
    return starts or [s for s in secs if q in fold(s[0])]

# A bare domain counts as a website ("slowmov.com"), so dictation does not have
# to spell out the protocol. Numbers and abbreviations do not match: the last
# part has to be letters and nothing may follow it.
DOMAIN = re.compile(r"^(?:https?://)?[\w-]+(?:\.[\w-]+)*\.[a-z]{2,6}(?:/[^\s]*)?$", re.I)

def split_links(text):
    """('note text', {'instagram': ..., 'url': ...}) — links pulled out of a line."""
    links, words = {}, []
    for w in text.split():
        bare = w.strip(",;")
        if bare.startswith("@") and len(bare) > 1:
            links["instagram"] = bare
        elif DOMAIN.match(bare):
            if "instagram.com" in bare.lower():
                links["instagram"] = bare
            else:
                links["url"] = bare if bare.lower().startswith("http") else "https://" + bare
        else:
            words.append(w)
    return " ".join(words).strip(), links

def parse(lines, secs, warn):
    """[(raw_name, note_lines)] — a matching 'name:' line opens a new entry."""
    entries = []
    for line in lines:
        line = line.rstrip()
        if not line.strip():
            continue
        m = re.match(r"^\s*(?:[-*]\s*)?(?:##\s*)?(.+?)\s*[:|]\s*(.*)$", line)
        if m and match(m.group(1), secs):
            entries.append([m.group(1).strip(), [m.group(2).strip()]])
            continue
        if m and len(m.group(1)) <= 40 and entries:
            # looks like a heading but names no place: most likely a typo
            warn.append("looks like a name but matches nothing, kept as text: %s"
                        % m.group(1).strip())
        if entries:
            entries[-1][1].append(line.strip())
        else:
            entries.append([None, [line.strip()]])
    return [(n, " ".join(p for p in parts if p).strip()) for n, parts in entries]

def main(argv):
    dry = "--dry" in argv
    text = NOTES.read_text()
    secs = sections(text)
    problems = []
    entries = parse(sys.stdin.read().splitlines(), secs, problems)

    writes = []          # [(section, note_or_None, links_dict)]
    seen = set()
    for name, value in entries:
        if name is None:
            problems.append("no place name: %r" % value[:50]); continue
        hits = match(name, secs)
        if not hits:
            problems.append("unknown: %s" % name); continue
        if len(hits) > 1:
            problems.append("ambiguous: %s -> %s" % (name, ", ".join(h[0] for h in hits)))
            continue
        note, links = split_links(value)
        if not note and not links:
            problems.append("nothing to write: %s" % name); continue
        real = hits[0][0]
        if real in seen:
            problems.append("twice in input: %s" % real); continue
        seen.add(real)
        writes.append((hits[0], note, links))

    for (real, _, _), note, links in writes:
        bits = []
        if note:
            bits.append(note[:60] + ("..." if len(note) > 60 else ""))
        for key in ("instagram", "url"):
            if links.get(key):
                bits.append("[%s %s]" % (key, links[key]))
        print("%s <- %s" % (real, " ".join(bits)))
    for problem in problems:
        print("  ! " + problem, file=sys.stderr)

    if dry:
        print("\ndry run: %d would be written, %d problems" % (len(writes), len(problems)),
              file=sys.stderr)
        return 1 if problems else 0

    # notes.md, back to front so the offsets taken above stay valid
    for (real, start, end), note, links in sorted(writes, key=lambda w: -w[0][1]):
        if not note:
            continue                                   # links only, nothing to say here
        block = text[start:end]
        head, rest = block.split("\n", 1) if "\n" in block else (block, "")
        comment = "\n".join(re.findall(r"^<!--.*?-->$", rest, re.M))
        comment = "\n".join(c for c in comment.split("\n") if c and "<!-- skip -->" not in c)
        body = "<!-- skip -->" if fold(note) == "skip" or note.strip() == "-" else note
        text = text[:start] + head + "\n" + (comment + "\n" if comment else "") + body + "\n\n" + text[end:]

    NOTES.write_text(text)

    # links.json, merged into what is already there so a second run adds an
    # Instagram handle without dropping the website written earlier
    link_writes = [(w[0][0], w[2]) for w in writes if w[2]]
    if link_writes:
        current = json.loads(LINKS.read_text()) if LINKS.exists() else {}
        for real, links in link_writes:
            entry = current.get(real) if isinstance(current.get(real), dict) else {}
            entry.update(links)
            current[real] = entry
        ordered = {k: current[k] for k in sorted(current, key=lambda k: (not k.startswith("_"), fold(k)))}
        LINKS.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n")

    notes_written = sum(1 for w in writes if w[1])
    print("\n%d notes, %d link entries, %d problems"
          % (notes_written, len(link_writes), len(problems)), file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
