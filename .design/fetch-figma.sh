#!/usr/bin/env bash
# Session 0 ONLY. Single-shot Figma cache builder.
# Usage: FIGMA_TOKEN=... FIGMA_FILE_KEY=... bash .design/fetch-figma.sh
set -euo pipefail

: "${FIGMA_TOKEN:?set FIGMA_TOKEN}"
: "${FIGMA_FILE_KEY:?set FIGMA_FILE_KEY}"

CACHE=".design/cache"
mkdir -p "$CACHE/nodes" "$CACHE/assets"

api() { # api <path> <outfile>
  local out="$2" code
  code=$(curl -sS -w '%{http_code}' -o "$out.tmp" \
    -H "X-Figma-Token: $FIGMA_TOKEN" "https://api.figma.com$1")
  if [ "$code" = "429" ]; then
    echo "429 RATE LIMITED — STOP. Do not retry. Wait before any further call." >&2
    rm -f "$out.tmp"; exit 42
  fi
  [ "$code" = "200" ] || { echo "HTTP $code for $1" >&2; cat "$out.tmp" >&2; exit 1; }
  mv "$out.tmp" "$out"
}

# 1/3 — whole document, one call. Everything else is derived from this file offline.
if [ ! -s "$CACHE/file.json" ]; then
  api "/v1/files/$FIGMA_FILE_KEY" "$CACHE/file.json"
else
  echo "file.json cached — skipping fetch"
fi

# 2/3 — image fills (raster assets placed inside frames), one call.
if [ ! -s "$CACHE/imagefills.json" ]; then
  api "/v1/files/$FIGMA_FILE_KEY/images" "$CACHE/imagefills.json"
fi

# 3/3 — vector/raster exports for explicitly listed node ids, batched.
# Fill .design/export-ids.txt with one "<nodeid> <slug> <format>" per line first.
IDS_FILE=".design/export-ids.txt"
if [ -s "$IDS_FILE" ]; then
  for fmt in svg png; do
    ids=$(awk -v f="$fmt" '$3==f {printf "%s,", $1}' "$IDS_FILE" | sed 's/,$//')
    [ -n "$ids" ] || continue
    api "/v1/images/$FIGMA_FILE_KEY?ids=$ids&format=$fmt&scale=2" "$CACHE/urls-$fmt.json"
    # URLs below are S3, not the Figma API — not rate limited by the token.
    python - "$CACHE/urls-$fmt.json" "$IDS_FILE" "$fmt" <<'PY'
import json,sys,urllib.request,os
urls=json.load(open(sys.argv[1]))["images"]
slug={l.split()[0]:l.split()[1] for l in open(sys.argv[2]) if l.strip() and l.split()[2]==sys.argv[3]}
for nid,u in urls.items():
    if not u: print("no url for",nid); continue
    p=os.path.join(".design/cache/assets", slug.get(nid,nid.replace(":","-"))+"."+sys.argv[3])
    urllib.request.urlretrieve(u,p); print("saved",p)
PY
  done
else
  echo "export-ids.txt empty — no asset export performed"
fi
echo "cache ready in $CACHE"
