"""Git-history detectors. Every one is pathspec-scoped to a single layer, so a
bulk commit in the other layer is never reported as this layer's finding.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ARTIFACTS = r"\.env$|node_modules/|__pycache__/|/dist/|/build/|\.pyc$|coverage/"
CONVENTIONAL = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|task|revert)(\([^)]+\))?!?: .+"
)


def git(*args: str) -> str:
    try:
        done = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=25
        )
        return done.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def scope(rule: dict) -> str:
    return rule.get("scope") or "."


def git_tracked_artifacts(rule: dict) -> tuple[str, list[str]]:
    """Build output, dependencies, or env files committed by accident."""
    tracked = git("ls-files", scope(rule)).splitlines()
    hits = [f"tracked: {p}" for p in tracked if re.search(ARTIFACTS, p)]
    return ("FAIL" if hits else "PASS", hits[:12])


def git_bulk_commits(rule: dict) -> tuple[str, list[str]]:
    """Wholesale dumps that destroy the atomicity of the history."""
    limit = int(rule.get("limit", 40))
    log = git("log", "--no-merges", "--format=%h|%s", "--shortstat",
              f"-{rule.get('depth', 60)}", "--", scope(rule))
    hits, header = [], None
    for line in log.splitlines():
        if "|" in line and not line.strip().startswith(("1 file", "2 file")):
            header = line
        found = re.search(r"(\d+) files? changed", line)
        if found and header and int(found.group(1)) > limit:
            hits.append(f"{header} — {found.group(1)} files")
    return ("FAIL" if hits else "PASS", hits[:12])


def git_message_convention(rule: dict) -> tuple[str, list[str]]:
    """A history a reviewer can read: conventional, scoped, imperative."""
    subjects = git("log", "--no-merges", "--format=%h %s",
                   f"-{rule.get('depth', 40)}", "--", scope(rule)).splitlines()
    if not subjects:
        return ("UNKNOWN", ["no commits touching this scope"])
    bad = [s for s in subjects if not CONVENTIONAL.match(s.split(" ", 1)[-1])]
    ratio = len(bad) / len(subjects)
    return ("FAIL" if ratio > 0.2 else "PASS",
            [f"{len(bad)}/{len(subjects)} off-convention"] + bad[:8])


def git_direct_main(rule: dict) -> tuple[str, list[str]]:
    """Commits landed on the integration branch without going through a branch."""
    branch = rule.get("main_branch", "main")
    subjects = git("log", "--first-parent", "--no-merges", "--format=%h %s",
                   f"-{rule.get('depth', 40)}", branch, "--", scope(rule)).splitlines()
    return ("FAIL" if subjects else "PASS", subjects[:12])


def git_doc_freshness(rule: dict) -> tuple[str, list[str]]:
    """Commits piled up since the changelog last moved."""
    targets = rule.get("roots") or []
    if not targets or not (ROOT / targets[0]).exists():
        return ("UNKNOWN", [f"no changelog at {targets}"])
    last = git("log", "-1", "--format=%h", "--", *targets).strip()
    if not last:
        return ("UNKNOWN", ["changelog never committed"])
    since = git("log", "--oneline", f"{last}..HEAD", "--", scope(rule)).splitlines()
    limit = int(rule.get("limit", 25))
    return ("FAIL" if len(since) > limit else "PASS",
            [f"{len(since)} commits since changelog commit {last} (limit {limit})"])


CYRILLIC = re.compile(r"[а-яё]", re.I)


def git_language_consistency(rule: dict) -> tuple[str, list[str]]:
    """Started in one language — stay in it. Mixed subjects read as two projects."""
    subjects = git("log", "--no-merges", "--format=%s",
                   f"-{rule.get('depth', 60)}", "--", scope(rule)).splitlines()
    if not subjects:
        return ("UNKNOWN", ["no commits touching this scope"])
    cyrillic = [s for s in subjects if CYRILLIC.search(s)]
    minority = min(len(cyrillic), len(subjects) - len(cyrillic))
    return ("FAIL" if minority else "PASS",
            [f"{len(cyrillic)} Cyrillic vs {len(subjects) - len(cyrillic)} Latin subjects"])


def git_branch_naming(rule: dict) -> tuple[str, list[str]]:
    """Branch names carry the workflow: prefix plus a described unit of work."""
    pattern = re.compile(rule.get("pattern", r"^(feature|feat|fix|hotfix|release|chore)/[\w.-]+$"))
    protected = {"main", "master", "develop", "dev", "HEAD"}
    names = [
        line.strip().lstrip("* ").split("/", 1)[-1] if line.strip().startswith("remotes/")
        else line.strip().lstrip("* ")
        for line in git("branch", "--format=%(refname:short)").splitlines()
    ]
    bad = [n for n in names if n and n not in protected and not pattern.match(n)]
    return ("FAIL" if bad else "PASS", bad[:12])


KINDS = {
    "git_language_consistency": git_language_consistency,
    "git_branch_naming": git_branch_naming,
    "git_tracked_artifacts": git_tracked_artifacts,
    "git_bulk_commits": git_bulk_commits,
    "git_message_convention": git_message_convention,
    "git_direct_main": git_direct_main,
    "git_doc_freshness": git_doc_freshness,
}
