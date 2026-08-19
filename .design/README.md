# Design alignment — Figma protocol

Branch: `design/figma-alignment`. The work itself was done in one session; the per-session
prompts that used to live in `prompts/` are gone with it. What stays is the rate-limit
protocol below and the offline cache, which is what any future design pass should read.

## Rate limits (READ FIRST)

Figma REST API returns **429** on burst usage; repeated 429 can lock the token
for up to **36 hours**. Therefore:

1. **One fetch, then offline.** `.design/fetch-figma.sh` pulls the whole document once into
   `.design/cache/file.json` (48 MB, gitignored) and exports assets in batches. Everything
   after that — `prune.py`, `tokens.py`, `show.py` — reads the cache and never the network.
2. **Read the cache, not the API.** `.design/cache/nodes/*.json` holds fifteen pruned frames
   and `MANIFEST.md` maps them to node ids. Needing one more frame means adding it to
   `TARGETS` in `prune.py` and re-running that script — no request involved. Only a frame
   the document itself does not contain needs a fetch.
3. **No polling, no retry loops.** A 429 is not retried automatically. On 429 stop
   immediately and wait — retrying is what turns a soft limit into a 36h ban.
4. Budget: **1** `GET /v1/files/:key` call, **1** `GET /v1/files/:key/images` call, and **at
   most 3** `GET /v1/images/:key?ids=...` calls (ids batched, up to ~50 per call). The 2026-08-19
   run spent all of it and still took a 429 on the last export — see MANIFEST for what that
   left missing.

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
