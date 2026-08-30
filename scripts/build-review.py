#!/usr/bin/env python3
"""Build docs/places-review.html — every place with the category the app derives for it.

The category rules and neighbourhood postcodes are parsed straight out of
index.html, so this page can never drift from what the map actually shows.
Run: python3 scripts/build-review.py
"""
import json, re, html, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = (ROOT / "index.html").read_text()

def parse_rules():
    block = re.search(r"const CATEGORY_RULES = \[(.*?)\n    \];", SRC, re.S).group(1)
    rules = []
    for key, kws in re.findall(r"\{ key: '([^']+)',\s*keywords: \[(.*?)\] \}", block, re.S):
        rules.append((key, re.findall(r"'([^']*)'", kws)))
    return rules

def parse_hoods():
    block = re.search(r"const HOODS = \[(.*?)\n    \];", SRC, re.S).group(1)
    hoods = []
    for hid, label, codes in re.findall(
            r"\{ id: '([^']+)',\s*label: '([^']*)',\s*codes: \[(.*?)\] \}", block, re.S):
        hoods.append((hid, label, set(re.findall(r"'([^']*)'", codes))))
    return hoods

def word(hay, kw):
    """Same whole-word rule as matchesWord() in index.html (plural s allowed)."""
    return re.search(r"(?<![0-9a-z\u00e0-\u00ff])" + re.escape(kw) + r"s?(?![0-9a-z\u00e0-\u00ff])", hay) is not None

RULES, HOODS = parse_rules(), parse_hoods()
COLORS = dict(re.findall(r"--c-([a-z]+):\s*(#[0-9a-f]{6})", SRC))

places = json.loads((ROOT / "data.json").read_text())

# --- mirror the app: group, then keyword sub-category for restaurants only ---
rows = []
for p in places:
    base = p.get("group") or p.get("category") or "Restaurant"
    hay = ((p.get("name") or "") + " " + (p.get("note") or "")).lower()
    matches = [(k, kw) for k, kws in RULES for kw in kws if word(hay, kw)]
    group, why = base, "group field"
    if base == "Restaurant":
        for k, kws in RULES:
            hit = next((kw for kw in kws if word(hay, kw)), None)
            if hit:
                group, why = k, 'keyword "%s"' % hit
                break
    # a rule that lost only because another one came first
    losers = sorted({k for k, _ in matches if k != group}) if base == "Restaurant" else []

    m = re.search(r"\b(08\d{3})\b", p.get("note") or "")
    hood = next((label for _, label, codes in HOODS if m and m.group(1) in codes), None)

    rows.append({
        "name": p.get("name", ""), "group": group, "why": why, "losers": losers,
        "cat": p.get("category", ""), "note": p.get("note", ""),
        "hood": hood or "(by proximity)", "url": p.get("url", ""),
        "lat": p.get("lat"), "lng": p.get("lng"),
    })

ORDER = ["Coffee", "Brunch", "Sushi", "Asian", "Tapas", "Vegan", "Bakery",
         "Pizza", "Burger", "Bar", "Wine", "Restaurant"]
rows.sort(key=lambda r: (ORDER.index(r["group"]) if r["group"] in ORDER else 99,
                         r["name"].lower()))
counts = collections.Counter(r["group"] for r in rows)
derived = [r for r in rows if r["why"] != "group field"]
ambiguous = [r for r in rows if r["losers"]]

def color(g):
    return COLORS.get(g.lower(), "#ff7a59")

def esc(s):
    return html.escape(str(s or ""))

trs = []
for r in rows:
    flag = ""
    if r["losers"]:
        flag += '<span class="flag" title="Other rules also matched">auch %s</span>' % esc(", ".join(r["losers"]))
    maps = "https://www.google.com/maps/search/?api=1&query=%s,%s" % (r["lat"], r["lng"])
    trs.append(
        '<tr data-cat="%s" data-text="%s">'
        '<td><span class="dot" style="background:%s"></span><b class="cat">%s</b></td>'
        '<td class="nm">%s%s</td>'
        '<td class="src">%s</td>'
        '<td class="hood">%s</td>'
        '<td class="note">%s</td>'
        '<td class="lnk"><a href="%s" target="_blank" rel="noopener">map</a>%s</td>'
        "</tr>" % (
            esc(r["group"]), esc((r["name"] + " " + r["note"] + " " + r["group"]).lower()),
            color(r["group"]), esc(r["group"]), esc(r["name"]), flag, esc(r["why"]),
            esc(r["hood"]), esc(r["note"]), esc(maps),
            (' · <a href="%s" target="_blank" rel="noopener">site</a>' % esc(r["url"])) if r["url"] else "",
        ))

chips = "".join(
    '<button class="chip" data-f="%s" style="border-color:%s;color:%s">%s (%d)</button>'
    % (esc(g), color(g), color(g), esc(g), counts[g]) for g in ORDER if counts[g])

page = """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Places Review</title>
<style>
:root{--bg:#0a0c10;--panel:#0f1218;--panel-2:#161a22;--text:#e6e8ec;--muted:#8a93a3;--border:#1f2530;--accent:#ff7a59}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 -apple-system,BlinkMacSystemFont,Inter,"Segoe UI",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:40px 22px 80px}
h1{font-size:26px;letter-spacing:-.02em;margin:0 0 8px}
.lede{color:var(--muted);margin:0 0 22px;max-width:75ch}
.bar{position:sticky;top:0;z-index:5;background:var(--bg);padding:14px 0 12px;border-bottom:1px solid var(--border);margin-bottom:6px}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:10px}
.chip{background:var(--panel-2);border:1px solid var(--border);border-radius:999px;padding:6px 13px;
  font:600 12px inherit;font-family:inherit;cursor:pointer}
.chip.on{background:var(--accent);border-color:var(--accent);color:#0a0c10!important}
#q{width:100%;background:var(--panel);border:1px solid var(--border);border-radius:9px;color:var(--text);
  padding:10px 13px;font:14px inherit;font-family:inherit}
#q::placeholder{color:var(--muted)}
.meta{color:var(--muted);font-size:12px;margin:10px 0 0}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);
  padding:12px 10px;border-bottom:1px solid var(--border);position:sticky;top:118px;background:var(--bg)}
td{padding:11px 10px;border-bottom:1px solid var(--border);vertical-align:top}
tr:hover td{background:var(--panel)}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px}
.cat{font-size:11px;letter-spacing:.04em}
.nm{font-weight:600;min-width:190px}
.src,.hood{color:var(--muted);font-size:12px;white-space:nowrap}
.note{color:var(--muted);font-size:12px}
.lnk a{color:var(--accent);text-decoration:none;font-size:12px;font-weight:600}
.lnk a:hover{text-decoration:underline}
.flag{display:inline-block;margin-left:8px;padding:1px 7px;border-radius:999px;background:var(--panel-2);
  border:1px solid var(--border);color:#e8c15a;font-size:10px;font-weight:600;letter-spacing:.02em}
.flag.warn{color:#ff7a59}
.hide{display:none}
@media(max-width:820px){.note,.hood{display:none}th{top:150px}}
</style></head><body><div class="wrap">
<h1>Alle Orte mit Kategorie</h1>
<p class="lede">__TOTAL__ Orte. Kategorie ist die, die die App anzeigt. Spalte "Quelle" sagt, woher sie kommt:
"group field" steht so in <code>data.json</code>, ein Keyword bedeutet, die Regel in <code>index.html</code> hat
sie aus Name und Note geraten. __DERIVED__ Orte sind geraten. __FLAGGED__ davon sind markiert: "auch X" heisst, eine zweite Regel hätte ebenfalls gepasst,
die erste in der Reihenfolge gewinnt. Gematcht wird auf ganze Wörter, ein Plural-s zählt mit.</p>
<div class="bar">
  <div class="chips"><button class="chip on" data-f="">Alle (__TOTAL__)</button>__CHIPS__
    <button class="chip" data-f="__flag__">Nur markierte (__FLAGGED__)</button></div>
  <input id="q" type="search" placeholder="Suchen nach Name, Note, Kategorie">
  <p class="meta" id="meta"></p>
</div>
<table><thead><tr><th>Kategorie</th><th>Name</th><th>Quelle</th><th>Quartier</th><th>Note</th><th>Links</th></tr></thead>
<tbody id="tb">__ROWS__</tbody></table>
</div>
<script>
var rows=[].slice.call(document.querySelectorAll('#tb tr')),f='',q='';
function apply(){var n=0;rows.forEach(function(r){
  var okF = !f || (f==='__flag__' ? !!r.querySelector('.flag') : r.dataset.cat===f);
  var okQ = !q || r.dataset.text.indexOf(q)>-1;
  r.classList.toggle('hide',!(okF&&okQ)); if(okF&&okQ)n++;});
  document.getElementById('meta').textContent=n+' von '+rows.length+' Orten';}
document.querySelectorAll('.chip').forEach(function(c){c.addEventListener('click',function(){
  document.querySelectorAll('.chip').forEach(function(x){x.classList.remove('on')});
  c.classList.add('on');f=c.dataset.f;apply();});});
document.getElementById('q').addEventListener('input',function(e){q=e.target.value.toLowerCase();apply();});
apply();
</script></body></html>"""

page = (page.replace("__ROWS__", "\n".join(trs)).replace("__CHIPS__", chips)
            .replace("__TOTAL__", str(len(rows))).replace("__DERIVED__", str(len(derived)))
            .replace("__FLAGGED__", str(len(ambiguous))))
out = ROOT / "docs" / "places-review.html"
out.write_text(page)
print("wrote", out, "|", len(rows), "places,", len(derived), "derived,",
      len(ambiguous), "ambiguous")
print(dict(counts))
