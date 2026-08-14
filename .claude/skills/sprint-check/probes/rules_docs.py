"""Generic documentation / repo-hygiene detectors.

Stack-agnostic: every root, glob, and project-specific pattern comes from
`config.json`. Rules run once per layer listed in `applies` ("*" = every layer).
`regression: True` marks a class the grader has already penalized here.
"""

RULES: list[dict] = [
    {
        "id": "DOC-README", "category": "docs", "applies": "*", "kind": "require",
        "title": "layer has a README",
        "roots": "{docs}", "regex": r"\S", "code_only": False,
    },
    {
        "id": "DOC-RUN", "category": "docs", "applies": "*", "kind": "require",
        "regression": True,
        "title": "README documents how to run the layer",
        "roots": "{docs}", "code_only": False,
        "regex": r"(?i)```|\$ |npm run|make |uvicorn|pytest|docker",
    },
    {
        "id": "DOC-CONTAINER", "category": "docs", "applies": "*", "kind": "require",
        "regression": True,
        "title": "README documents the containerized run (Dockerfile/compose)",
        "roots": "{docs}", "regex": r"(?i)docker|compose|container", "code_only": False,
    },
    {
        "id": "DOC-ARCH", "category": "docs", "applies": "*", "kind": "require",
        "regression": True,
        "title": "README explains the module/layer map, not just commands",
        "roots": "{docs}", "code_only": False,
        "regex": r"(?i)architect|архитект|layer|слой|module|модул|feature-sliced|\bFSD\b",
    },
    {
        "id": "DOC-TESTS", "category": "docs", "applies": "*", "kind": "require",
        "regression": True,
        "title": "README states the prerequisites tests need (DB, services, fixtures)",
        "roots": "{docs}", "code_only": False,
        "regex": r"(?i)createdb|create database|test database|тестов\w* (базу|БД)"
                 r"|docker compose up|npm (ci|install)|pip install|make setup|fixtures?",
    },
    {
        "id": "DOC-ENV", "category": "docs", "applies": "*", "kind": "require",
        "title": "an env template exists next to the code that needs it",
        "roots": "{env_example}", "regex": r"\S", "code_only": False,
    },
    {
        "id": "DOC-ENV-CLEAN", "category": "docs", "applies": "*", "kind": "forbid",
        "regression": True,
        "title": "env template holds placeholders, never real hosts or credentials",
        "roots": "{env_example}", "code_only": False,
        "regex": r"https?://\S+|=[A-Za-z0-9_\-]{20,}",
        "unless": r"(?i)changeme|<|example\.com|placeholder|your[-_]",
    },
    {
        "id": "DOC-CHANGELOG", "category": "docs", "applies": "*", "kind": "require",
        "title": "a changelog exists for the layer",
        "roots": "{changelog}", "regex": r"\S", "code_only": False,
    },
    {
        "id": "DOC-CHANGELOG-FRESH", "category": "docs", "applies": "*",
        "kind": "git_doc_freshness", "regression": True,
        "title": "changelog keeps pace with the commit stream",
        "roots": "{changelog}", "scope": "{root}", "limit": "{changelog_commit_limit}",
    },
    {
        "id": "DOC-CI", "category": "docs", "applies": "*", "kind": "require",
        "title": "CI runs tests and format/lint checks on the release branch",
        "roots": ["{root}/.github/workflows", ".github/workflows", ".gitverse/ci",
                  "{root}/.gitlab-ci.yml"],
        "code_only": False,
        "regex": r"(?i)(pytest|npm (run )?test|vitest|jest|lint|ruff|eslint|format)",
    },
    {
        "id": "DOC-TESTCASES", "category": "docs", "applies": "*", "kind": "require",
        "title": "test cases / test plan are committed artifacts, not local files",
        "roots": "{test_artifacts}", "code_only": False,
        "regex": r"(?i)(тест-?кейс|test case|TC\d|ожидаемый результат|expected result|шаги)",
    },
    {
        "id": "DOC-DECISIONS", "category": "docs", "applies": "*", "kind": "require",
        "title": "non-obvious choices are written down somewhere discoverable",
        "roots": "{docs}", "code_only": False,
        "regex": r"(?i)decision|решени|trade-?off|why|почему|ADR",
    },
]
