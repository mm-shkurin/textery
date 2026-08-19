# Design alignment — Figma protocol

Branch: `design/figma-alignment`. Worktree per session.

## Rate limits (READ FIRST)

Figma REST API returns **429** on burst usage; repeated 429 can lock the token
for up to **36 hours**. Therefore:

1. **Exactly one session (session 0) talks to Figma.** It runs `.design/fetch-figma.sh`
   once, writes `.design/cache/`, and downloads every asset. It commits the cache.
2. **All other sessions are offline.** They read `.design/cache/` only.
   They must never run `curl` against `api.figma.com`, never re-fetch a node,
   never re-export an image. If something is missing from the cache, they stop
   and report the missing node id — session 0 batches it into a single follow-up call.
3. **No polling, no retry loops.** A 429 is not retried automatically. On 429 stop
   immediately and wait — retrying is what turns a soft limit into a 36h ban.
4. Budget for session 0: **1** `GET /v1/files/:key` call, **1** `GET /v1/files/:key/images`
   call, and **at most 3** `GET /v1/images/:key?ids=...` calls (ids batched, comma-separated,
   up to ~50 ids per call). That is the whole budget. Nothing else.

## Token

Token lives in `infra/.env` as `FIGMA_TOKEN` (gitignored). Never commit it,
never paste it into a prompt file, never send it anywhere but `api.figma.com`.

## Cache layout

```
.design/cache/file.json          full document (one fetch)
.design/cache/nodes/<slug>.json  one pruned subtree per target frame
.design/cache/tokens.json        colors / type ramp / spacing extracted from the frames
.design/cache/assets/<name>.svg|png
.design/cache/MANIFEST.md        frame name -> node id -> slug -> assets
```
