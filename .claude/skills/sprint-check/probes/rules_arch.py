"""Generic architecture / consistency detectors.

Layer-boundary rules are not written here — they are generated from
`config.json:layers.<layer>.forbidden_imports`, so the same catalogue serves a
Clean-Architecture backend and an FSD frontend without edits.
"""

RULES: list[dict] = [
    {
        "id": "ARCH-SIZE", "category": "arch", "applies": "*", "kind": "max_lines",
        "regression": True,
        "title": "no oversized source files",
        "roots": "{code}", "globs": "{src}", "limit": "{file_line_limit}",
        "exclude": "{tests}",
    },
    {
        "id": "ARCH-SIZE-STYLE", "layer_kind": "ui", "category": "arch", "applies": "*", "kind": "max_lines",
        "title": "no oversized stylesheets",
        "roots": "{code}", "globs": "{styles}", "limit": "{file_line_limit}",
    },
    {
        "id": "ARCH-PATH-HACK", "category": "arch", "applies": "*", "kind": "forbid",
        "regression": True,
        "title": "no runtime import-path patching (packaging worked around)",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"sys\.path|require\.cache|module-alias|process\.env\.NODE_PATH",
    },
    {
        "id": "ARCH-GLOBAL-STATE", "category": "arch", "applies": "*", "kind": "forbid",
        "title": "no cross-request state in module globals (multi-instance safe)",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"^(_?[A-Z][A-Z_0-9]*)\s*(:\s*[^=]+)?=\s*(\{\}|\[\]|dict\(\)|new Map\(|new Set\()",
    },
    {
        "id": "ARCH-ENTRY-CONFIG", "category": "arch", "applies": "*", "kind": "require",
        "title": "a linter/formatter config is committed for the layer",
        "roots": "{config}", "code_only": False,
        "regex": r"(?i)ruff|flake8|black|mypy|eslint|prettier|biome|stylelint",
    },
    {
        "id": "ARCH-TEST-DOUBLE-STANDARD", "category": "arch", "applies": "*",
        "kind": "forbid", "regression": True,
        "title": "lint/type rules are not relaxed for test code",
        "roots": "{config}", "code_only": False,
        "regex": r"(?i)(per-file-ignores.*test|\"?tests?/\*+\"?\s*=|overrides.*\btests?\b)",
    },
    {
        "id": "ARCH-EXPORT-STYLE", "layer_kind": "ui", "category": "arch", "applies": "*", "kind": "forbid",
        "regression": True,
        "title": "one export convention across the layer",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"^export\s+default\b",
        "unless": r"config|vite|next|storybook",
    },
    {
        "id": "ARCH-STATE-LIB", "layer_kind": "ui", "category": "arch", "applies": "*", "kind": "require",
        "regression": True,
        "title": "a deliberate shared-state/data-cache solution is declared",
        "roots": "{config}", "code_only": False, "regex": "{state_libraries}",
    },
    {
        "id": "ARCH-STATE-SPREAD", "layer_kind": "ui", "category": "arch", "applies": "*",
        "kind": "max_per_file", "regression": True,
        "title": "related state is grouped, not scattered across many state slots",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"\buseState\s*[(<]|\bcreateSignal\s*\(", "limit": 3,
    },
    {
        "id": "ARCH-SCOPED-STYLES", "layer_kind": "ui", "category": "arch", "applies": "*", "kind": "forbid",
        "regression": True,
        "title": "component styles are scoped, not global imports",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"import\s+['\"][^'\"]+\.(css|scss)['\"]",
        "unless": r"\.module\.|index\.css|/app/|main\.|tailwind",
    },
    {
        "id": "ARCH-DESIGN-TOKENS", "layer_kind": "ui", "category": "arch", "applies": "*", "kind": "forbid",
        "regression": True,
        "title": "visual constants come from tokens, not literals",
        "roots": "{code}", "globs": "{styles}",
        "exclude": "{style_token_files}|{tests}",
        "regex": r"#[0-9a-fA-F]{3,8}\b|rgba?\(", "unless": r"var\(--",
    },
    {
        "id": "ARCH-ENV-ACCESS", "layer_kind": "ui", "category": "arch", "applies": "*", "kind": "forbid",
        "regression": True,
        "title": "platform globals reached through a guarded helper",
        "roots": "{code}", "globs": "{src}", "exclude": "{tests}",
        "regex": r"\b(window|document|localStorage|navigator)\.",
        "unless": r"typeof window|shared/lib|/browser|isBrowser",
    },
]
