"""Structural detectors that a regex cannot express: function length, duplicated
blocks, naming consistency, indentation consistency.

Each returns (status, evidence[]) like every other probe kind.
"""
from __future__ import annotations

import ast
import hashlib
import re
from collections import defaultdict
from pathlib import Path


def _engine():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "engine", Path(__file__).with_name("engine.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


E = _engine()


def max_function_lines(rule: dict) -> tuple[str, list[str]]:
    """Long method / long function — the classic God-method smell."""
    limit = int(rule.get("limit", 30))
    hits = []
    for path in E.walk(rule["roots"], rule.get("globs", []), rule.get("exclude")):
        hits.extend(
            python_functions(path, limit) if path.suffix == ".py"
            else brace_functions(path, limit)
        )
    return ("FAIL" if hits else "PASS", sorted(hits, reverse=True)[:E.MAX_EVIDENCE])


def python_functions(path: Path, limit: int) -> list[str]:
    try:
        tree = ast.parse("\n".join(E.read(path)))
    except (SyntaxError, ValueError):
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        length = (node.end_lineno or node.lineno) - node.lineno
        if length > limit:
            out.append(f"{E.rel(path)}:{node.lineno}: {node.name}() is {length} lines "
                       f"(limit {limit})")
    return out


FUNC_START = re.compile(r"\b(function\s+\w+|=>\s*\{|\w+\s*\([^)]*\)\s*\{)")


def brace_functions(path: Path, limit: int) -> list[str]:
    """Brace-language approximation: depth-0 block openings and their span."""
    lines = E.code_lines(path)
    out, stack = [], []
    for number, line in enumerate(lines, 1):
        if FUNC_START.search(line):
            stack.append((number, line.count("{") - line.count("}")))
            continue
        if not stack:
            continue
        start, depth = stack[-1]
        depth += line.count("{") - line.count("}")
        if depth <= 0:
            stack.pop()
            if number - start > limit:
                out.append(f"{E.rel(path)}:{start}: block is {number - start} lines "
                           f"(limit {limit})")
        else:
            stack[-1] = (start, depth)
    return out


NORMALIZE = re.compile(r"[\"'][^\"']*[\"']|\s+")


def duplicate_blocks(rule: dict) -> tuple[str, list[str]]:
    """DRY violations: identical normalized windows in two or more places."""
    window = int(rule.get("window", 6))
    seen: dict[str, list[str]] = defaultdict(list)
    for path in E.walk(rule["roots"], rule.get("globs", []), rule.get("exclude")):
        lines = [line for line in E.code_lines(path) if line.strip()]
        for index in range(len(lines) - window):
            chunk = NORMALIZE.sub(" ", " ".join(lines[index:index + window]))
            if len(chunk) < 120:
                continue
            digest = hashlib.sha1(chunk.encode()).hexdigest()[:12]
            seen[digest].append(f"{E.rel(path)}:{index + 1}")
    hits = [
        f"{window}-line block repeated {len(places)}x: " + ", ".join(places[:3])
        for places in seen.values()
        if len({p.split(":")[0] for p in places}) > 1
    ]
    return ("FAIL" if hits else "PASS", sorted(hits)[:E.MAX_EVIDENCE])


STYLES = {
    "snake": re.compile(r"^[a-z][a-z0-9_]*$"),
    "kebab": re.compile(r"^[a-z][a-z0-9-]*$"),
    "camel": re.compile(r"^[a-z][a-zA-Z0-9]*$"),
    "pascal": re.compile(r"^[A-Z][a-zA-Z0-9]*$"),
}


def naming_consistency(rule: dict) -> tuple[str, list[str]]:
    """One file-naming convention per directory, not four."""
    by_dir: dict[str, set[str]] = defaultdict(set)
    samples: dict[str, list[str]] = defaultdict(list)
    for path in E.walk(rule["roots"], rule.get("globs", []), rule.get("exclude")):
        stem = path.stem.split(".")[0]
        for name, pattern in STYLES.items():
            if pattern.match(stem):
                by_dir[path.parent.as_posix()].add(name)
                samples[path.parent.as_posix()].append(f"{path.name}({name})")
                break
    hits = [
        f"{Path(folder).as_posix().split('/')[-3:][-1]}: {sorted(styles)} — "
        + ", ".join(samples[folder][:4])
        for folder, styles in by_dir.items()
        if len(styles - {"camel", "pascal"}) + len(styles & {"camel", "pascal"}) > 2
    ]
    return ("FAIL" if hits else "PASS", sorted(hits)[:E.MAX_EVIDENCE])


def indentation_consistency(rule: dict) -> tuple[str, list[str]]:
    """Mixed tabs/spaces or mixed indent widths inside one file."""
    hits = []
    for path in E.walk(rule["roots"], rule.get("globs", []), rule.get("exclude")):
        lines = E.read(path)
        tabs = sum(1 for line in lines if line.startswith("\t"))
        spaces = sum(1 for line in lines if line.startswith("  "))
        if tabs and spaces:
            hits.append(f"{E.rel(path)}: {tabs} tab-indented, {spaces} space-indented")
    return ("FAIL" if hits else "PASS", sorted(hits)[:E.MAX_EVIDENCE])


KINDS = {
    "max_function_lines": max_function_lines,
    "duplicate_blocks": duplicate_blocks,
    "naming_consistency": naming_consistency,
    "indentation_consistency": indentation_consistency,
}
