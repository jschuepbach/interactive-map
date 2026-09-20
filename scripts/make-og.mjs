// Builds img/og.png, the link preview card for WhatsApp, iMessage, Slack and
// the rest. The pin field behind the type is the real list: every place in
// data.json, projected and coloured by its family, so the card is a picture of
// the thing it links to rather than a stock graphic.
//
//   node scripts/make-og.mjs
//
// Renders through headless Chrome, which is the only renderer on this machine
// that can turn HTML into a PNG. After regenerating, bump the ?v= on the
// og:image URL in index.html: WhatsApp caches a preview per URL for weeks.

import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const W = 1200;
const H = 630;
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

const COLORS = {
  sweet: '#d98f4e', brunch: '#e0b755', local: '#e8705a', asia: '#48b3bd',
  americas: '#6bb069', europe: '#cf6f9b', drinks: '#8f86e0', other: '#c2727f',
  quick: '#5b93d6'
};
// Same families as index.html, same hues.
const FAMILIES = [
  { color: COLORS.sweet,    groups: ['Coffee', 'Pastry', 'Bakery', 'Tea', 'Ice Cream'] },
  { color: COLORS.brunch,   groups: ['Brunch'] },
  { color: COLORS.local,    groups: ['Tapas', 'Catalan'] },
  { color: COLORS.asia,     groups: ['Japanese', 'Pan-Asian', 'Korean', 'Vietnamese', 'Chinese', 'Thai', 'Indian', 'Filipino'] },
  { color: COLORS.americas, groups: ['Peruvian', 'Mexican', 'Brazilian', 'Colombian', 'Ecuatorian'] },
  { color: COLORS.europe,   groups: ['Fine-dining', 'Grill', 'Seafood', 'Italian', 'Mediterranean', 'Fusion'] },
  { color: COLORS.quick,    groups: ['Burger', 'Sandwich', 'Vegan', 'Middle-Eastern'] },
  { color: COLORS.drinks,   groups: ['Wine', 'Cheese'] },
  { color: COLORS.other,    groups: ['Drinks', 'Beer'] }
];
const FAMILY_OF = {};
FAMILIES.forEach((f) => f.groups.forEach((g) => { FAMILY_OF[g] = f; }));

const places = JSON.parse(readFileSync(resolve(root, 'data.json'), 'utf8'))
  .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng));

// Web Mercator is overkill across 8km; a cosine on the longitude is exact
// enough and keeps the city the shape people recognise.
const latMid = places.reduce((s, p) => s + p.lat, 0) / places.length;
const kx = Math.cos((latMid * Math.PI) / 180);
const xs = places.map((p) => p.lng * kx).sort((a, b) => a - b);
const ys = places.map((p) => -p.lat).sort((a, b) => a - b);
// Percentiles, not the bounding box. Half a dozen places out towards Sants and
// Gràcia would otherwise set the frame and leave the Eixample core, where most
// of the list actually is, as a small clump in one corner. The outliers still
// get drawn; they just run off the edge, which is what a city does.
const at = (arr, q) => arr[Math.round((arr.length - 1) * q)];
const spanX = at(xs, 0.94) - at(xs, 0.06);
const spanY = at(ys, 0.94) - at(ys, 0.06);
const scale = Math.min((W * 0.96) / spanX, (H * 0.96) / spanY);
const cx = (at(xs, 0.94) + at(xs, 0.06)) / 2;
const cy = (at(ys, 0.94) + at(ys, 0.06)) / 2;

const dots = places.map((p) => {
  const fam = (p.groups || [p.group]).map((g) => FAMILY_OF[g]).find(Boolean);
  const x = W / 2 + (p.lng * kx - cx) * scale;
  const y = H / 2 + (-p.lat - cy) * scale;
  return `<i style="left:${x.toFixed(1)}px;top:${y.toFixed(1)}px;--c:${fam ? fam.color : '#ff385c'}"></i>`;
}).join('');

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
  * { box-sizing: border-box; margin: 0; }
  html, body { width: ${W}px; height: ${H}px; }
  body { background: #121212; overflow: hidden;
    font-family: -apple-system, system-ui, 'Helvetica Neue', sans-serif;
    -webkit-font-smoothing: antialiased; }
  .field { position: absolute; inset: 0; }
  .field i { position: absolute; width: 11px; height: 11px; margin: -5.5px 0 0 -5.5px;
    border-radius: 50%; background: var(--c);
    box-shadow: 0 0 0 2.5px #121212, 0 0 16px -2px var(--c); }
  /* The type sits in a well punched out of the field, not on top of it. */
  .scrim { position: absolute; inset: 0;
    background:
      radial-gradient(52% 60% at 50% 52%, #121212 26%, rgba(18,18,18,.90) 48%, rgba(18,18,18,0) 84%),
      linear-gradient(to bottom, rgba(18,18,18,.55), rgba(18,18,18,0) 26%, rgba(18,18,18,0) 70%, rgba(18,18,18,.75)); }
  .stack { position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 30px; text-align: center; }
  .brand { display: flex; align-items: center; gap: 13px; color: #ededed; }
  .brand svg { width: 34px; height: 34px; display: block; }
  .brand span { font-size: 27px; font-weight: 600; letter-spacing: -.02em; }
  h1 { font-size: 66px; line-height: 1.12; font-weight: 450; letter-spacing: -.025em;
    color: #c8c8c8; max-width: 860px; }
  h1 b { font-weight: 700; color: #ededed; font-variant-numeric: tabular-nums; }
  .foot { font-size: 21px; color: #9a9a9a; letter-spacing: -.005em; }
</style></head><body>
  <div class="field">${dots}</div>
  <div class="scrim"></div>
  <div class="stack">
    <div class="brand">
      <svg viewBox="0 0 64 64"><polygon points="19,4 45,4 60,19 60,45 45,60 19,60 4,45 4,19"
        fill="none" stroke="currentColor" stroke-width="6" stroke-linejoin="round"/>
        <circle cx="32" cy="32" r="9" fill="#ff385c"/></svg>
      <span>Barcelona</span>
    </div>
    <h1><b>${places.length} places</b><br>I recommend to my friends.</h1>
    <p class="foot">No ratings, no sponsors. Picked by hand.</p>
  </div>
</body></html>`;

mkdirSync(resolve(root, 'img'), { recursive: true });
const tmp = resolve(root, 'img', '.og-card.html');
writeFileSync(tmp, html);

execFileSync(CHROME, [
  '--headless',
  '--disable-gpu',
  '--hide-scrollbars',
  '--force-device-scale-factor=1',
  `--window-size=${W},${H}`,
  `--screenshot=${resolve(root, 'img', 'og.png')}`,
  'file://' + tmp
], { stdio: 'inherit' });

rmSync(tmp, { force: true });
console.log(`og.png written from ${places.length} places`);
