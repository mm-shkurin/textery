# Textery frontend

React + TypeScript + Vite app for Textery — lets a user pick a document type,
describe a topic, and watch an AI-generated document appear as it's produced.

## Structure

- `src/features/landing` — marketing landing page.
- `src/features/generation` — the document-generation flow: type/mode
  selection modals, the chat-style workspace, the polling hook
  (`useGeneration`), and the HTTP client (`generationApi`).
- `src/shared` — components shared across features.

## Setup

```bash
npm install
npm run dev      # start dev server (proxies /api to the backend)
npm run build    # type-check + production build
npm run lint      # oxlint
npm run test      # run tests once
npm run test:watch
```

## Environment

- `VITE_API_BASE_URL` — base URL for the generation API. Defaults to `''`,
  which routes requests through the Vite dev server's `/api` proxy
  (see `vite.config.ts`, target controlled by `VITE_API_PROXY_TARGET`).
- `FRONTEND_PORT` — port the dev server listens on (defaults to `5173`).

## Testing

Tests use Vitest + Testing Library (`src/test/setup.ts`). Run `npm run test`
before committing; `npm run build` also type-checks via `tsc -b`.
