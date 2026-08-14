"""Generic git-practice detectors, scoped per layer via `{root}` pathspec."""

RULES: list[dict] = [
    {
        "id": "GIT-ARTIFACTS", "category": "git", "applies": "*",
        "kind": "git_tracked_artifacts",
        "title": "no build output, dependencies, or env files tracked",
        "scope": "{root}",
    },
    {
        "id": "GIT-BULK", "category": "git", "applies": "*",
        "kind": "git_bulk_commits", "regression": True,
        "title": "no wholesale sync/dump commits",
        "scope": "{root}", "limit": "{commit_file_limit}",
    },
    {
        "id": "GIT-MESSAGES", "category": "git", "applies": "*",
        "kind": "git_message_convention",
        "title": "commit subjects follow one readable convention",
        "scope": "{root}",
    },
    {
        "id": "GIT-LANGUAGE", "category": "git", "applies": "*",
        "kind": "git_language_consistency",
        "title": "commit subjects stay in one language",
        "scope": "{root}",
    },
    {
        "id": "GIT-BRANCH-NAMES", "category": "git", "applies": "*",
        "kind": "git_branch_naming",
        "title": "branch names follow the declared workflow prefix scheme",
        "scope": "{root}", "pattern": "{branch_pattern}",
    },
    {
        "id": "GIT-DIRECT-MAIN", "category": "git", "applies": "*",
        "kind": "git_direct_main", "regression": True,
        "title": "integration branch advances through branches, not direct commits",
        "scope": "{root}", "main_branch": "{main_branch}",
    },
]
