# How this ships

## One file, on purpose

The whole app is `index.html`: inline CSS, one IIFE, `data.json` fetched at
runtime. No build step, no `node_modules`, no framework. A push is a deploy.

This was reconsidered on 2026-09-17 and kept. The triggers that would change the
answer, none of which apply yet:

- **Per-place pages** with their own link previews and OG images. Today a place
  is shareable as `?q=<name>`, which has no preview card in a messenger.
- **Photos per place.** The moment images arrive, an image pipeline earns its
  keep.
- **Size.** Around 2200 lines today. Past roughly twice that, splitting is worth
  the tooling.

If one of those lands, Astro is the closer fit than Next: static pages per
place, no React required, and the MapLibre code moves across almost unchanged.
The smaller step is a few ES modules plus esbuild, still no framework.

## Vercel

- Project `interactive-map` (`prj_M1l40jPDIaVHlB4mUBHNg018JYjj`).
- Public URL: <https://interactive-map-wine.vercel.app>
- `interactive-map-jandimitrischuepbach-7658s-projects.vercel.app` is **not**
  public: SSO protection is on for everything except custom domains, so that
  host redirects strangers to a Vercel login. Send people the `-wine` address,
  or add a custom domain, where the protection does not apply.
- Production branch is `master`. This repo has no `main`, and Vercel proposes
  `main` by default when connecting.

### The gap of 2026-09-17

The Git connection was missing for a while, so pushes stopped deploying and the
live site sat on a commit from August while master moved on. It was reconnected
on 2026-09-17. If the live site ever looks older than master again, check
Project Settings → Git first: an unconnected project shows "Connect Git
Repository" on its dashboard card instead of a commit line, and Deploy Hooks
refuse to be created.

A deployment can also be triggered without the CLI through the Vercel API, which
is what filled the gap:

    POST /v13/deployments
    { "name": "interactive-map",
      "project": "<project id>",
      "target": "production",
      "gitSource": { "type": "github", "org": "jschuepbach",
                     "repo": "interactive-map", "ref": "master" } }
