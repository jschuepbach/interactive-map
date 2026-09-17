# Where the content comes from

The **Notion table is the list**, not this repo:
<https://app.notion.com/p/5606b2adaedb4fe18d1101c3fe5f0b60?v=e5796b340ac146db9194a306dfe156e1>

Columns that matter:

| Notion column      | Lands in                                   |
|--------------------|--------------------------------------------|
| `Name`             | `data.json` `name`, heading in `notes.md`  |
| `Cuisine`          | `data.json` `groups`, first tag is `group` |
| `Why it's good`    | the note body in `notes.md`                |
| `My suggestion`    | `data.json` `tip`                          |
| `Adresse`, `Maps`  | `data.json` `note` (scraped address), `lat`/`lng` |

`Why it's good` still reading **"Still on my bucket list"** means Jan has not been
there. Those places get no note and `"bucket": true` instead, which is what keeps
the two filters honest: *Only the ones I have written about* and *Still on my
bucket list* are the two halves of the same question.

## The path

1. Pull the table through the Notion MCP and write `notion-snapshot.json`
   (one entry per place: `cuisine`, `why`, `tip`, `bucket`).
2. `python3 scripts/apply-notion.py` shows the plan, `--apply` writes
   `data.json`, `notes.md` and `links.json`.
3. Places missing from the snapshot are dropped. Places in the snapshot with no
   match here are reported: they need coordinates before they can be added.

Names are matched loosely (accents, case, punctuation) and the snapshot's
spelling wins, so renaming a row in Notion renames the place here.

## Two things worth knowing

- **Notion's read index keeps trash rows.** A row count can be higher than what
  the table really holds (248 vs 227 in September 2026). The write path refuses
  them with "This page is in the trash". Believe the write path, not the count.
- **The note and the address are separate fields in the app.** `data.json` ships
  the scraped Google Maps address in `note`; at load time the app moves it to
  `address` and puts the text from `notes.md` into `note`. The postcode in the
  address is what assigns a neighbourhood, so overwriting it would cost every
  written-up place its barrio.

## Other scripts

- `scripts/notes-todo.py` lists the places with no note yet
- `scripts/ingest-notes.py` takes dictated `Name: text` blocks
- `scripts/export-notion.py` dumps the current state back out as JSON rows
