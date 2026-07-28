// The scanned set, shared by check-nginx-503.mjs (which forbids these) and its self-test (which
// pins that each one is still forbidden). Shared rather than duplicated so a directive cannot be
// dropped from the scan while the self-test keeps reporting the same number of green cases — the
// self-test iterates this list, so an entry with no case is not expressible.
//
// Every way nginx can answer 503 to a request it has already forwarded, or answer it on the
// origin's behalf. `return 503`/a bare 503 in a rewrite is the canonical maintenance one-liner and
// the most direct of them; `limit_req`/`limit_conn` reject with 503 by default; `error_page` can map
// anything onto a 503 page; `proxy_intercept_errors` hands the origin's own 5xx to those pages;
// `max_fails` + `proxy_next_upstream` make nginx exhaust an upstream group and answer 503 without
// the origin ever replying. `upstream` is listed because it is the block the last two require — its
// presence is the earliest visible signal. The bare status code is scanned as a string: any
// uncommented line mentioning 503 is either an answer or a comment that should have been one.
//
// `sample` is the line the self-test feeds the guard for that entry — a realistic declaration, not a
// bare token, so the case fails the way a real commit would.
export const DIRECTIVES_THAT_CAN_EMIT_503 = [
  { directive: '503', sample: 'location = /maint { return 503; }' },
  { directive: 'limit_req', sample: 'limit_req zone=api burst=5;' },
  { directive: 'limit_conn', sample: 'limit_conn perip 10;' },
  { directive: 'error_page', sample: 'error_page 502 /maintenance.html;' },
  { directive: 'proxy_intercept_errors', sample: 'proxy_intercept_errors on;' },
  { directive: 'max_fails', sample: 'server backend:8000 max_fails=3 fail_timeout=30s;' },
  { directive: 'proxy_next_upstream', sample: 'proxy_next_upstream error timeout;' },
  { directive: 'upstream', sample: 'upstream backend { server backend:8000; }' },
]

export const DIRECTIVES = DIRECTIVES_THAT_CAN_EMIT_503.map((entry) => entry.directive)
