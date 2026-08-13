"""Generic code-smell, security, and test-hygiene detectors.

Nothing here names a file of this project: each rule is a class of defect the
grader looks for in any repository. Judgment-heavy smells (God Object, SRP,
cyclomatic complexity, duplication) are intentionally absent — they belong to
the review-agent lane described in SKILL.md.
"""

TESTS_ONLY = r"(?!.*(/tests?/|__tests__|\.test\.|\.spec\.|test_))"

RULES: list[dict] = [
    {
        "id": "SMELL-URL", "category": "smell", "applies": "*", "kind": "forbid",
        "regression": True,
        "title": "no hardcoded external endpoints (config, not source)",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"[\"']https?://",
        "unless": r"(?i)localhost|127\.0\.0\.1|example\.|schemas?\.|xmlns|w3\.org|\.svg",
    },
    {
        "id": "SMELL-FS-PATH", "layer_kind": "service", "category": "smell", "applies": "*", "kind": "forbid",
        "regression": True,
        "title": "certificate/asset paths are configurable, not package-relative",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"[\"'][^\"']*\.(pem|crt|p12|keystore)[\"']",
    },
    {
        "id": "SMELL-MAGIC", "category": "smell", "applies": "*", "kind": "forbid",
        "regression": True,
        "title": "timing/limit constants come from configuration",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"^\s*(const|let|_?[A-Z][A-Z_0-9]{2,})\s*[A-Z_0-9]*\s*=\s*\d{3,}\s*;?\s*$",
        "unless": r"env|config|settings|getenv",
    },
    {
        "id": "SMELL-POLICY-IN-CODE", "category": "smell", "applies": "*",
        "kind": "forbid", "regression": True,
        "title": "allow/deny policy lists are data, not inline literals",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"(?i)(ALLOWED|BLOCKED|WHITELIST|BLACKLIST|PERMITTED)_[A-Z_]*\s*[:=]\s*[\[{(]",
    },
    {
        "id": "SMELL-ENDPOINT-LITERAL", "category": "smell", "applies": "*",
        "kind": "forbid", "regression": True,
        "title": "API paths come from one route map, not literals at call sites",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"['\"]/(api|v\d)/",
        "unless": r"endpoints|routes|paths\.",
    },
    {
        "id": "SMELL-POLLING", "layer_kind": "ui", "category": "smell", "applies": "*", "kind": "forbid",
        "regression": True,
        "title": "progress is pushed (SSE/WS) or backed off, not naively polled",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"setInterval\s*\(",
    },
    {
        "id": "SMELL-REFETCH-TOKEN", "layer_kind": "ui", "category": "smell", "applies": "*",
        "kind": "forbid", "regression": True,
        "title": "mutations update the cache locally, not via a refetch counter",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"reloadToken|refreshKey|refetchCounter|forceReload",
    },
    {
        "id": "SMELL-NO-ABORT", "layer_kind": "ui", "category": "smell", "applies": "*", "kind": "require",
        "regression": True,
        "title": "in-flight requests are cancellable on unmount/navigation",
        "roots": "{code}", "globs": "{src}",
        "regex": r"AbortController|CancelToken|signal\s*[:,]",
    },
    {
        "id": "SMELL-TYPE-ESCAPE", "category": "smell", "applies": "*", "kind": "forbid",
        "regression": True,
        "title": "no type-system escape hatches",
        "roots": "{code}", "globs": "{src}",
        "regex": r"as\s+unknown\s+as|@ts-ignore|#\s*type:\s*ignore|\bAny\b\s*=|cast\(Any",
    },
    {
        "id": "SMELL-DEAD-CODE", "category": "smell", "applies": "*", "kind": "forbid",
        "title": "no commented-out code or stale TODO/FIXME piles",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}", "code_only": False,
        "regex": r"^\s*(#|//)\s*(TODO|FIXME|HACK|XXX)\b",
    },
    {
        "id": "SMELL-LONG-FUNC", "category": "smell", "applies": "*",
        "kind": "max_function_lines",
        "title": "no long method carrying a whole flow",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}", "limit": 30,
    },
    {
        "id": "SMELL-DUPLICATION", "category": "smell", "applies": "*",
        "kind": "duplicate_blocks",
        "title": "no block duplicated across files (DRY)",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}", "window": 6,
    },
    {
        "id": "STYLE-NAMING", "category": "style", "applies": "*",
        "kind": "naming_consistency",
        "title": "one file-naming convention per directory",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
    },
    {
        "id": "STYLE-INDENT", "category": "style", "applies": "*",
        "kind": "indentation_consistency",
        "title": "no mixed tab/space indentation inside a file",
        "roots": "{code}", "globs": "{src}",
    },
    {
        "id": "SEC-INJECTION", "category": "security", "applies": "*", "kind": "forbid",
        "title": "SECURITY: queries and commands are parameterized, never concatenated",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"(?i)(execute|query|raw|text)\s*\(\s*[f\"'].*(select|insert|update|delete)"
                 r".*(\+|\{|%s?\s*%|\$\{)|subprocess\.\w+\([^)]*\+",
    },
    {
        "id": "SEC-SECRET", "category": "security", "applies": "*", "kind": "forbid",
        "title": "SECURITY: no credentials or tokens in tracked source",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"(?i)(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*[\"'][^\"'{$<]{8,}",
    },
    {
        "id": "SEC-WEB-STORAGE", "layer_kind": "ui", "category": "security", "applies": "*",
        "kind": "forbid", "regression": True,
        "title": "SECURITY: credentials never in web storage (XSS-readable)",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"(session|local)Storage\.[gs]etItem\(\s*['\"][^'\"]*(token|jwt|auth|session)",
    },
    {
        "id": "SEC-RAW-HTML", "layer_kind": "ui", "category": "security", "applies": "*", "kind": "forbid",
        "regression": True,
        "title": "SECURITY: no unsanitized HTML sink",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"dangerouslySetInnerHTML|innerHTML\s*=|rehype-raw|v-html|\|\s*safe\b",
    },
    {
        "id": "SEC-EVAL", "layer_kind": "service", "category": "security", "applies": "*", "kind": "forbid",
        "title": "SECURITY: no dynamic evaluation or shell interpolation",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"\beval\(|new Function\(|shell\s*=\s*True|os\.system\(|pickle\.loads\(",
    },
    {
        "id": "SEC-TLS-OFF", "layer_kind": "service", "category": "security", "applies": "*", "kind": "forbid",
        "title": "SECURITY: TLS verification and CORS are not disabled wholesale",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"verify\s*=\s*False|rejectUnauthorized:\s*false|allow_origins\s*=\s*\[\s*[\"']\*",
    },
    {
        "id": "SEC-FETCHER", "layer_kind": "service", "category": "security", "applies": "*", "kind": "require",
        "regression": True,
        "title": "SECURITY: renderers/parsers deny remote resource fetching (SSRF)",
        "roots": "{code}", "globs": "{src}",
        "regex": r"url_fetcher|resolve_entities\s*=\s*False|no_network|block_remote",
    },
    {
        "id": "TEST-PRESENT", "category": "tests", "applies": "*", "kind": "require",
        "title": "the layer has tests",
        "roots": "{code}", "globs": "{src}",
        "regex": r"^\s*(def test_|it\(|test\(|describe\()",
    },
    {
        "id": "TEST-SKIPS", "category": "tests", "applies": "*", "kind": "forbid",
        "regression": True,
        "title": "no silently skipped tests on a fresh checkout",
        "roots": "{code}", "globs": "{src}",
        "regex": r"skipif|\.skip\(|@pytest\.mark\.skip|xfail|it\.todo",
    },
    {
        "id": "TEST-TIMEOUT", "layer_kind": "service", "category": "tests", "applies": "*", "kind": "require",
        "regression": True,
        "title": "lock/concurrency tests are bounded by a timeout",
        "roots": "{code}", "globs": ["*concurren*", "*lock*", "*race*"],
        "regex": r"timeout",
    },
]
