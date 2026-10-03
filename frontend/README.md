# Vectron web console

The browser UI for the Vectron software factory. It is written in React 18, TypeScript (strict) and Vite.
The only runtime dependencies are `react`, `react-dom`, `mermaid` (lazy-loaded) and
`highlight.js`. The UI makes no external network requests, so it works air-gapped.

The API contract is in [`src/api/types.ts`](src/api/types.ts). All calls go to the relative base `/api`.

## Develop

```bash
npm install
npm run dev          # http://localhost:5173, proxies /api → http://127.0.0.1:8000
```

Start the backend on port 8000 first. To point the proxy somewhere else, set
`VECTRON_API_URL=http://host:port` (as an environment variable or in `frontend/.env.local`).
The proxy passes job event streams (SSE) through unbuffered. It asks the backend for an
uncompressed stream and sets `Cache-Control: no-transform` and `X-Accel-Buffering: no`.

## Build

```bash
npm run build        # tsc --noEmit && vite build  →  dist/
npm run typecheck    # type-checks src/ and vite.config.ts
npm run preview      # serves dist/ on :4173 with the same /api proxy
```

In production the FastAPI backend serves `dist/` as static files at the site root, next to `/api`.
Routing uses the URL hash (`#/`, `#/builds`, `#/jobs/<id>`), so the backend needs no SPA fallback.
It only has to serve `index.html`, `favicon.svg` and `assets/`.

## Layout

```
src/
  api/        types.ts (contract), client.ts (typed fetch wrappers, URL helpers)
  hooks/      useHashRoute, useJob (snapshot + SSE), useResource, useFileText, …
  lib/        formatting, task/file tree builders, mermaid loader, highlight.js setup
  components/ shared UI, catalog/ (blueprint cards, brief), job/ (task tree, comms log, tabs)
  views/      CatalogView, BuildsView, JobView
  styles/     tokens + base, layout, components, catalog, job, syntax colours
```
