"""File walking, comment stripping, and probe kinds for /sprint-check.

Read-only. Every kind returns (status, evidence[]) for one rule dict.
"""
from __future__ import annotations

import io
import re
import tokenize
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EXCLUDED_DIRS = {
    ".git", "node_modules", "dist", "build", "coverage", "htmlcov",
    ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".next", "site-packages", "migrations",
}
EXCLUDED_FILE_GLOBS = ("*.min.*", "*.lock", "*-lock.json", "*.map", "*.svg")
STRIPPABLE = {".py", ".ts", ".tsx", ".js", ".mjs", ".css"}
MAX_EVIDENCE = 12


def walk(roots: list[str], globs: list[str], exclude: str | None = None):
    skip = re.compile(exclude) if exclude else None
    for root in roots:
        base = ROOT / root
        if not base.exists():
            continue
        candidates = [base] if base.is_file() else base.rglob("*")
        for path in candidates:
            if not path.is_file():
                continue
            if EXCLUDED_DIRS & {p.name for p in path.parents}:
                continue
            if any(fnmatch(path.name, g) for g in EXCLUDED_FILE_GLOBS):
                continue
            if globs and not any(fnmatch(path.name, g) for g in globs):
                continue
            if skip and skip.search(path.relative_to(ROOT).as_posix()):
                continue
            yield path


def read(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def code_lines(path: Path) -> list[str]:
    """Comments and docstrings blanked, line numbering preserved.

    A rule named in prose ("we never call sys.path here") is not a violation.
    String *literals* stay — a hardcoded URL lives inside one.
    """
    lines = read(path)
    if path.suffix not in STRIPPABLE:
        return lines
    return strip_python(lines) if path.suffix == ".py" else strip_block(lines)


def strip_python(lines: list[str]) -> list[str]:
    out = list(lines)
    opens_statement = {tokenize.NEWLINE, tokenize.NL, tokenize.INDENT,
                       tokenize.DEDENT, tokenize.ENCODING}
    previous, depth = tokenize.NEWLINE, 0
    try:
        for token in tokenize.generate_tokens(io.StringIO("\n".join(lines)).readline):
            if token.type == tokenize.OP and token.string in "([{)]}":
                depth += 1 if token.string in "([{" else -1
            # inside brackets the tokenizer emits NL, so a string there is an
            # argument, not a docstring — depth keeps literals visible
            docstring = (
                token.type == tokenize.STRING
                and previous in opens_statement
                and depth == 0
            )
            if token.type == tokenize.COMMENT or docstring:
                for number in range(token.start[0], token.end[0] + 1):
                    if 0 < number <= len(out):
                        out[number - 1] = ""
            if token.type not in (tokenize.COMMENT,):
                previous = token.type
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return lines  # unparseable: a false positive beats a blind spot
    return out


def strip_block(lines: list[str]) -> list[str]:
    out, inside = [], False
    for line in lines:
        if inside:
            end = line.find("*/")
            out.append("" if end < 0 else line[end + 2:])
            inside = end < 0
            continue
        start = line.find("/*")
        if start >= 0 and "*/" not in line[start + 2:]:
            inside = True
            out.append(line[:start])
            continue
        out.append(re.sub(r"//.*|/\*.*?\*/", "", line))
    return out


def matches(rule: dict) -> list[str]:
    pattern = re.compile(rule["regex"])
    negative = re.compile(rule["unless"]) if rule.get("unless") else None
    hits: list[str] = []
    for path in walk(rule["roots"], rule.get("globs", []), rule.get("exclude")):
        raw = read(path)
        source = code_lines(path) if rule.get("code_only", True) else raw
        for number, line in enumerate(source, 1):
            if not pattern.search(line):
                continue
            if negative and negative.search(raw[number - 1]):
                continue
            hits.append(f"{rel(path)}:{number}: {raw[number - 1].strip()[:140]}")
    return hits


def probe_forbid(rule: dict) -> tuple[str, list[str]]:
    hits = matches(rule)
    return ("FAIL" if hits else "PASS", hits[:MAX_EVIDENCE])


def probe_require(rule: dict) -> tuple[str, list[str]]:
    if not any(True for _ in walk(rule["roots"], rule.get("globs", []))):
        return ("UNKNOWN", [f"no file to inspect under {rule['roots']}"])
    hits = matches(rule)
    return ("PASS", hits[:3]) if hits else ("FAIL", ["no match for " + rule["regex"]])


def probe_max_lines(rule: dict) -> tuple[str, list[str]]:
    limit = rule["limit"]
    hits = [
        f"{rel(p)}: {len(read(p))} lines (limit {limit})"
        for p in walk(rule["roots"], rule.get("globs", []), rule.get("exclude"))
        if len(read(p)) > limit
    ]
    return ("FAIL" if hits else "PASS", sorted(hits)[:MAX_EVIDENCE])


def probe_max_per_file(rule: dict) -> tuple[str, list[str]]:
    pattern = re.compile(rule["regex"])
    limit = rule["limit"]
    hits = []
    for path in walk(rule["roots"], rule.get("globs", []), rule.get("exclude")):
        count = sum(len(pattern.findall(line)) for line in code_lines(path))
        if count > limit:
            hits.append(f"{rel(path)}: {count} occurrences (limit {limit})")
    return ("FAIL" if hits else "PASS", sorted(hits)[:MAX_EVIDENCE])


KINDS = {
    "forbid": probe_forbid,
    "require": probe_require,
    "max_lines": probe_max_lines,
    "max_per_file": probe_max_per_file,
}
