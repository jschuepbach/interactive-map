/**
 * Google Maps List Extractor
 * Paste this into the browser DevTools console while viewing a Google Maps shared list.
 * It auto-scrolls to load all items, then downloads a JSON file.
 *
 * Steps:
 *   1. Open your Google Maps list link in Chrome (you must be logged in)
 *   2. Open DevTools → Console (Cmd+Option+J on Mac)
 *   3. Paste this entire script and press Enter
 *   4. Wait for "Done! X places extracted" in the console
 *   5. A file named gmaps-list.json will download automatically
 */
(async function extractList() {
  console.log('[extractor] Starting…');

  // ── 1. Find the scrollable panel ──────────────────────────────────────────
  // Google Maps keeps the list in a scrollable div. The selector varies by
  // page version; we try several known class patterns.
  function getScrollContainer() {
    const candidates = [
      document.querySelector('div.m6QErb[tabindex]'),
      document.querySelector('div[role="feed"]'),
      document.querySelector('[data-section-id="oloc"]'),
      document.querySelector('div.m6QErb'),
    ];
    return candidates.find(Boolean) || document.documentElement;
  }

  // ── 2. Auto-scroll until no new content loads ─────────────────────────────
  async function scrollToBottom() {
    const container = getScrollContainer();
    let prev = -1;
    let stall = 0;
    while (stall < 3) {
      container.scrollTop += 1200;
      await new Promise(r => setTimeout(r, 1200));
      const now = container.scrollTop + container.clientHeight;
      if (now === prev) stall++;
      else { stall = 0; prev = now; }
      const count = document.querySelectorAll('a[href*="/maps/place/"]').length;
      console.log(`[extractor] Scrolling… ${count} places visible`);
    }
    console.log('[extractor] Scroll complete.');
  }

  await scrollToBottom();

  // ── 3. Extract data from place links ─────────────────────────────────────
  // Each list card contains an <a href="/maps/place/…/@lat,lng,…"> element.
  // Coordinates live in the @lat,lng part of that href.
  const places = [];
  const seen = new Set();

  const links = [...document.querySelectorAll('a[href*="/maps/place/"]')];
  console.log(`[extractor] Processing ${links.length} links…`);

  for (const link of links) {
    try {
      const href = link.href || '';

      // Extract coordinates from the URL  (/@lat,lng,zoom pattern)
      const coordMatch = href.match(/@(-?\d+\.\d+),(-?\d+\.\d+)/);
      const lat = coordMatch ? parseFloat(coordMatch[1]) : null;
      const lng = coordMatch ? parseFloat(coordMatch[2]) : null;

      // Place name: try several DOM locations
      const nameEl =
        link.querySelector('.fontHeadlineSmall') ||
        link.querySelector('h3') ||
        link.querySelector('[jsan*="name"]') ||
        link.querySelector('div[style*="font-weight"]');
      const nameFromEl = nameEl?.textContent?.trim();

      // Fallback: decode from URL path (/maps/place/Name+Here/@…)
      const urlName = (() => {
        try {
          const m = href.match(/\/maps\/place\/([^/@]+)/);
          return m ? decodeURIComponent(m[1].replace(/\+/g, ' ')) : null;
        } catch { return null; }
      })();

      const name = nameFromEl || urlName || link.getAttribute('aria-label') || '';
      if (!name) continue;

      // Address / subtitle
      const subtitleEl =
        link.querySelector('.fontBodyMedium') ||
        link.querySelector('[jsan*="address"]') ||
        link.querySelectorAll('div')[1];
      const address = subtitleEl?.textContent?.trim() || '';

      // Category – often in a small text node after the address
      const spans = [...link.querySelectorAll('span')];
      const category = spans.map(s => s.textContent.trim()).filter(t => t && t.length < 60)[0] || '';

      // Deduplicate by name + rough coords
      const key = name + (lat?.toFixed(3) ?? '') + (lng?.toFixed(3) ?? '');
      if (seen.has(key)) continue;
      seen.add(key);

      places.push({
        name,
        lat,
        lng,
        category,
        note: address,
        url: href.split('?')[0], // strip tracking params
      });
    } catch (e) {
      console.warn('[extractor] Error on link:', e);
    }
  }

  console.log(`[extractor] Done! ${places.length} places extracted.`);

  // ── 4. Download ───────────────────────────────────────────────────────────
  const blob = new Blob([JSON.stringify(places, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'gmaps-list.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  return `Extracted ${places.length} places → gmaps-list.json`;
})();
