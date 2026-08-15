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
    // Several forms, because ONE sample cannot pin a rule stated as broadly as "any mention of the
    // code": narrowing this to `return 503` would keep a single-sample case green while going blind
    // to every other way the status reaches a client.
    samples: [
      'location = /maint { return 503; }',
      'error_page 404 =503 /maint.html;',
      'limit_req_status 503;',
    ],
    fires: (line) => line.includes('503'),
  },
  {
    // Rejects with 503 by default; `limit_req_status` can change that, but its presence is the
    // signal either way.
    directive: 'limit_req',
    samples: [
      'limit_req zone=api burst=5;',
      'limit_req_zone $binary_remote_addr zone=api:10m rate=5r/s;',
    ],
    fires: (line) => line.includes('limit_req'),
  },
  {
    directive: 'limit_conn',
    samples: ['limit_conn perip 10;', 'limit_conn_zone $binary_remote_addr zone=perip:10m;'],
    fires: (line) => line.includes('limit_conn'),
  },
  {
    // Fires only when a 5xx is among the codes being mapped. `error_page 404 /index.html;` is the
    // SPA fallback every frontend has and cannot produce a 503; `error_page 502 503 /maint.html;`
    // is nginx answering for an origin that may well have taken the write.
    directive: 'error_page',
    // Deliberately a 502 and not a 503: a line mentioning 503 is caught by the entry above, so a
    // 503 sample would pass this case without the error_page rule existing at all.
    samples: ['error_page 502 /maintenance.html;', 'error_page 500 502 504 /maint.html;'],
    nearMisses: ['error_page 404 /index.html;', 'error_page 404 /index.html; # not a 5xx'],
    fires: (line) => line.includes('error_page') && /\b5\d\d\b/.test(line),
  },
  {
    // Hands the origin's own 5xx to those pages, which is what turns an error_page mapping into an
    // answer nginx composes. `off` is the default and changes nothing.
    directive: 'proxy_intercept_errors',
    samples: ['proxy_intercept_errors on;'],
    nearMisses: ['proxy_intercept_errors off;'],
    fires: (line) => line.includes('proxy_intercept_errors') && !/\boff\b/.test(line),
  },
  {
    // With proxy_next_upstream, exhausting the group makes nginx answer 503 itself, without the
    // origin ever replying.
    directive: 'max_fails',
    samples: ['server backend:8000 max_fails=3 fail_timeout=30s;'],
    nearMisses: ['server backend:8000 max_fails=0;'],
    fires: (line) => line.includes('max_fails') && !/max_fails\s*=\s*0\b/.test(line),
  },
  {
    directive: 'proxy_next_upstream',
    samples: ['proxy_next_upstream error timeout;'],
    nearMisses: ['proxy_next_upstream off;'],
    fires: (line) => line.includes('proxy_next_upstream') && !/\boff\b/.test(line),
  },
  {
    // A named server group answers nothing on its own — it is the block the two above REQUIRE, so it
    // is worth seeing, but only once one of them is actually ENABLED somewhere in the same conf.
    // Adding an upstream for DNS re-resolution or keepalive is routine and must not fail the build,
    // and neither must one carrying `max_fails=0` — the disabled form this file pins as benign three
    // entries up. A raw substring test for the companion names re-armed on exactly those, firing the
    // false positive the whole boundary exists to prevent.
    directive: 'upstream',
    // The sample carries NO companion on its own line: with one, `max_fails` fires first and the
    // offender is attributed to that entry, leaving this predicate provable only in the passing
    // direction — it could be blinded outright with every case still green. Two servers is the form
    // only this entry claims.
    samples: ['upstream backend { server a:8000; server b:8000; }'],
    nearMisses: [
      'upstream backend { server backend:8000; }',
      'upstream backend { server backend:8000 max_fails=0; }',
    ],
    fires: (line, conf) =>
      line.includes('upstream') &&
      !line.includes('proxy_next_upstream') &&
      hasEnabledCompanion(conf),
  },
]

// Whether anything in the conf makes an upstream group able to answer 503.
//
// Two ways. Explicitly: a `max_fails`/`proxy_next_upstream` line — asked by running THOSE entries'
// own predicates, so the disabled forms they already treat as benign (`max_fails=0`,
// `proxy_next_upstream off`) stay benign here too. A raw substring test for the names re-armed on
// exactly those, firing the false positive this whole boundary exists to prevent.
//
// And by default: nginx ships `max_fails=1` and `proxy_next_upstream error timeout`, so a group
// with TWO OR MORE servers has failover on with neither word written anywhere, and exhausting it
// answers 503 with the origin never replying. A single-server group has nothing to fail over to.
// That is the line between the benign `upstream` block someone adds for DNS re-resolution or
// keepalive and one that can answer for the origin.
function hasEnabledCompanion(conf) {
  const companions = DIRECTIVES_THAT_CAN_EMIT_503.filter(({ directive }) =>
    ['max_fails', 'proxy_next_upstream'].includes(directive),
  )
  const lines = conf.split('\n')
  const explicit = lines.some((line) => companions.some((entry) => entry.fires(line, conf)))
  // `server backend:8000;` — an upstream member. Deliberately NOT matching the `server {` block
  // opener, which is not a member and would make every ordinary vhost look like a failover target.
  const serverCount = (conf.match(/\bserver\s+[A-Za-z0-9_.:/-]+/g) ?? []).length

  return explicit || serverCount > 1
}

export const DIRECTIVES = DIRECTIVES_THAT_CAN_EMIT_503.map((entry) => entry.directive)

// The one place a line is judged. `conf` is the whole (comment-stripped) file, because two entries
// are only dangerous in the presence of another directive elsewhere in it.
// Inline comments are cut before judging. Whole-line comments are already dropped by the caller,
// but the predicates negate on substrings — `off`, `max_fails=0`, a non-5xx code — so a trailing
// `# nginx defaults this off` could talk a real emitter out of firing. That surface did not exist
// while every rule was a bare `includes`; the tightening created it.
export const stripComment = (line) => line.split('#')[0].trim()

export function firstFiring(rawLine, rawConf) {
  const line = stripComment(rawLine)
  const conf = rawConf.split('\n').map(stripComment).join('\n')
  return DIRECTIVES_THAT_CAN_EMIT_503.find((entry) => entry.fires(line, conf))?.directive
}
