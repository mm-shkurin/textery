#!/usr/bin/env bash
# Publish this monorepo's frontend/ subtree to gitverse.ru/studentlabs/slide_frontend main.
#
# Run from the monorepo root, in Git Bash, on a clean working tree.
# The backend twin of this ran on 2026-08-28 and published 377dcabd..1fdb5bca.
#
#   bash _project_audit/publish-frontend.sh            # build + verify, DOES NOT push
#   bash _project_audit/publish-frontend.sh --push     # build + verify + push
#
# Why this is not just `git subtree split && git push`:
# a plain split produces commit ids that do NOT match what is already on the remote
# (the earlier publish was made from a different merge structure), so the push is
# refused as non-fast-forward. Forcing would rewrite published history. Instead this
# script finds the split commit whose TREE equals the published tip's tree — the point
# where the two histories agree on content — and replays only the commits after it onto
# the published tip. Result: a plain fast-forward push with per-commit granularity kept.

set -euo pipefail

REMOTE=gitverse-frontend
PREFIX=frontend
SOURCE_BRANCH=dev
MIRROR=frontend-mirror
PUBLISH=frontend-publish

say() { printf '\n=== %s ===\n' "$1"; }

say "preflight"
git rev-parse --is-inside-work-tree >/dev/null
if [ -n "$(git status --porcelain)" ]; then
  echo "working tree is dirty — commit or stash first" >&2
  exit 1
fi
git fetch "$REMOTE"
PUBLISHED=$(git rev-parse "$REMOTE/main")
echo "published tip:  $PUBLISHED"
echo "source:         $SOURCE_BRANCH $(git rev-parse --short $SOURCE_BRANCH)"

say "subtree split (walks all $(git rev-list --count $SOURCE_BRANCH) commits — expect 10-15 min)"
git branch -D "$MIRROR" 2>/dev/null || true
git subtree split --prefix="$PREFIX" "$SOURCE_BRANCH" -b "$MIRROR"

say "finding the agreement point"
# The published tip's tree, and the split commit that produced the identical tree.
PUBLISHED_TREE=$(git rev-parse "$REMOTE/main^{tree}")
TWIN=$(git log --format="%H %T" "$MIRROR" | awk -v t="$PUBLISHED_TREE" '$2==t {print $1; exit}')
if [ -z "$TWIN" ]; then
  echo "no split commit reproduces the published tree." >&2
  echo "do NOT force push. Investigate before going further." >&2
  exit 1
fi
echo "published tree: $PUBLISHED_TREE"
echo "twin in split:  $TWIN  ($(git log -1 --format=%s "$TWIN"))"

COUNT=$(git rev-list --count "$TWIN..$MIRROR")
MERGES=$(git rev-list --merges "$TWIN..$MIRROR" | wc -l)
echo "commits to replay: $COUNT (merges: $MERGES)"
[ "$COUNT" -gt 0 ] || { echo "nothing new to publish"; exit 0; }

say "replaying onto the published tip"
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
NEW=$PUBLISHED
for c in $(git rev-list --reverse "$TWIN..$MIRROR"); do
  git log -1 --format=%B "$c" > "$TMP"
  NEW=$(
    GIT_AUTHOR_NAME="$(git log -1 --format=%an "$c")" \
    GIT_AUTHOR_EMAIL="$(git log -1 --format=%ae "$c")" \
    GIT_AUTHOR_DATE="$(git log -1 --format=%aD "$c")" \
    GIT_COMMITTER_NAME="$(git log -1 --format=%cn "$c")" \
    GIT_COMMITTER_EMAIL="$(git log -1 --format=%ce "$c")" \
    GIT_COMMITTER_DATE="$(git log -1 --format=%cD "$c")" \
    git commit-tree "$(git rev-parse "$c^{tree}")" -p "$NEW" -F "$TMP"
  )
  printf '%s -> %s  %s\n' "${c:0:8}" "${NEW:0:8}" "$(git log -1 --format=%s "$c")"
done
git branch -f "$PUBLISH" "$NEW"

say "verification — all three must pass"
FAIL=0
git merge-base --is-ancestor "$REMOTE/main" "$PUBLISH" \
  && echo "  [ok] fast-forward: no --force needed" \
  || { echo "  [FAIL] not a fast-forward"; FAIL=1; }
[ "$(git rev-parse "$PUBLISH^{tree}")" = "$(git rev-parse "$SOURCE_BRANCH:$PREFIX")" ] \
  && echo "  [ok] tree identical to $SOURCE_BRANCH:$PREFIX" \
  || { echo "  [FAIL] tree differs from $SOURCE_BRANCH:$PREFIX"; FAIL=1; }
LEAK=$(git ls-tree -r --name-only "$PUBLISH" | grep -E "^(backend|ProductSpecification|infra|_project_audit|\.claude)/" || true)
[ -z "$LEAK" ] \
  && echo "  [ok] no monorepo-only paths leaked" \
  || { echo "  [FAIL] leaked paths:"; echo "$LEAK"; FAIL=1; }
[ "$FAIL" -eq 0 ] || { echo "verification failed — nothing pushed" >&2; exit 1; }

say "what would be published"
git log --oneline "$REMOTE/main..$PUBLISH"
echo
echo "deletions:"
git diff "$REMOTE/main" "$PUBLISH" --diff-filter=D --stat || true
echo
echo "root of the published repo:"
git ls-tree --name-only "$PUBLISH"

if [ "${1:-}" != "--push" ]; then
  say "dry run — nothing pushed"
  echo "to publish:  git push $REMOTE $PUBLISH:main"
  echo "if that fails with a TLS handshake error, retry; if it asks for credentials,"
  echo "the GitVerse token is in the file the owner keeps on their Desktop —"
  echo "pass it inline as https://<token>@gitverse.ru/... and do NOT write it into"
  echo ".git/config."
  exit 0
fi

say "pushing"
git push "$REMOTE" "$PUBLISH:main"

say "confirming from the remote"
git fetch "$REMOTE"
git log --oneline -1 "$REMOTE/main"
[ "$(git rev-parse "$REMOTE/main^{tree}")" = "$(git rev-parse "$SOURCE_BRANCH:$PREFIX")" ] \
  && echo "published content is identical to $SOURCE_BRANCH:$PREFIX — gate item 3 closed for this layer" \
  || echo "MISMATCH after push — investigate"
