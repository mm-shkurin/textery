// The scanned set, shared by check-nginx-503.mjs (which forbids these) and its self-test (which
// pins that each one is still forbidden AND that each one's boundary holds). Shared rather than
// duplicated so a directive cannot be dropped from the scan while the self-test keeps reporting the
// same number of green cases — the self-test iterates this list, so an entry with no case is not
// expressible.
//
// Every entry is a way nginx can answer 503 to a request it has already forwarded, or answer it on
// the origin's behalf. But two of them can ALSO appear in a form that provably cannot: `error_page
// 404 /index.html;` maps a client error, and a bare `upstream` block is just a named server group.
// Firing on those is not a harmless false positive — it is the incident. The person adding
// `error_page 404` is told their commit endangers autosaves, sees that it plainly does not, and
// concludes the guard is wrong; a guard that is wrong on first contact gets deleted, not refined,
// and nothing else guards this premise. So each entry carries its own `fires` predicate, and the
// self-test pins both sides of every boundary.
//
// `sample` is a line that MUST fire; `nearMiss`, where present, is the neighbouring line that must
// NOT. Both are realistic declarations rather than bare tokens, so each case fails the way a real
// commit would.
export const DIRECTIVES_THAT_CAN_EMIT_503 = [
  {
    // The canonical maintenance one-liner, and the most direct of them. Any uncommented mention of
    // the status code is either an answer or a comment that should have been one.
    directive: '503',
    sample: 'location = /maint { return 503; }',
    fires: (line) => line.includes('503'),
  },
  {
    // Rejects with 503 by default; `limit_req_status` can change that, but its presence is the
    // signal either way.
    directive: 'limit_req',
    sample: 'limit_req zone=api burst=5;',
    fires: (line) => line.includes('limit_req'),
  },
  {
    directive: 'limit_conn',
    sample: 'limit_conn perip 10;',
    fires: (line) => line.includes('limit_conn'),
  },
  {
    // Fires only when a 5xx is among the codes being mapped. `error_page 404 /index.html;` is the
    // SPA fallback every frontend has and cannot produce a 503; `error_page 502 503 /maint.html;`
    // is nginx answering for an origin that may well have taken the write.
    directive: 'error_page',
    // Deliberately a 502 and not a 503: a line mentioning 503 is caught by the entry above, so a
    // 503 sample would pass this case without the error_page rule existing at all.
    sample: 'error_page 502 /maintenance.html;',
    nearMiss: 'error_page 404 /index.html;',
    fires: (line) => line.includes('error_page') && /\b5\d\d\b/.test(line),
  },
  {
    // Hands the origin's own 5xx to those pages, which is what turns an error_page mapping into an
    // answer nginx composes. `off` is the default and changes nothing.
    directive: 'proxy_intercept_errors',
    sample: 'proxy_intercept_errors on;',
    nearMiss: 'proxy_intercept_errors off;',
    fires: (line) => line.includes('proxy_intercept_errors') && !/\boff\b/.test(line),
  },
  {
    // With proxy_next_upstream, exhausting the group makes nginx answer 503 itself, without the
    // origin ever replying.
    directive: 'max_fails',
    sample: 'server backend:8000 max_fails=3 fail_timeout=30s;',
    nearMiss: 'server backend:8000 max_fails=0;',
    fires: (line) => line.includes('max_fails') && !/max_fails\s*=\s*0\b/.test(line),
  },
  {
    directive: 'proxy_next_upstream',
    sample: 'proxy_next_upstream error timeout;',
    nearMiss: 'proxy_next_upstream off;',
    fires: (line) => line.includes('proxy_next_upstream') && !/\boff\b/.test(line),
  },
  {
    // A named server group answers nothing on its own — it is the block the two above REQUIRE, so it
    // is worth seeing, but only once one of them is actually present somewhere in the same conf.
    // Adding an upstream for DNS re-resolution or keepalive is routine and must not fail the build.
    directive: 'upstream',
    sample: 'upstream backend { server backend:8000 max_fails=2; }',
    nearMiss: 'upstream backend { server backend:8000; }',
    fires: (line, conf) =>
      line.includes('upstream') &&
      !line.includes('proxy_next_upstream') &&
      /max_fails|proxy_next_upstream/.test(conf),
  },
]

export const DIRECTIVES = DIRECTIVES_THAT_CAN_EMIT_503.map((entry) => entry.directive)

// The one place a line is judged. `conf` is the whole (comment-stripped) file, because two entries
// are only dangerous in the presence of another directive elsewhere in it.
export function firstFiring(line, conf) {
  return DIRECTIVES_THAT_CAN_EMIT_503.find((entry) => entry.fires(line, conf))?.directive
}
