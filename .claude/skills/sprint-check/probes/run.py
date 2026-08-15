#!/usr/bin/env python3
"""Mechanical probe runner for /sprint-check.

The rule catalogue (`rules_*.py`) is stack-agnostic; `config.json` binds it to this
repository's layers. Emits {generated, root, branch, head, results[]}, each result
{id, layer, category, title, regression, status, evidence[]}.
Status: PASS | FAIL | WAIVED | UNKNOWN. Read-only — walks files, reads git.

Usage: python run.py [--layer back|front|all] [--category docs|arch|smell|...]
                     [--out report.json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOGUE = ("rules_docs", "rules_arch", "rules_quality", "rules_git")


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ENGINE = load("engine")
EXPAND = load("expand")
GIT = load("git_kinds")
ANALYSIS = load("analysis")
KINDS = {**ENGINE.KINDS, **GIT.KINDS, **ANALYSIS.KINDS}


def git(*args: str) -> str:
    try:
        done = subprocess.run(
            ["git", *args], cwd=ENGINE.ROOT, capture_output=True, text=True, timeout=25
        )
        return done.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def load_json(name: str, fallback):
    path = HERE / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def load_waivers() -> dict[str, dict]:
    today = date.today().isoformat()
    entries = load_json("waivers.json", [])
    return {e["id"]: e for e in entries if e.get("expires", "") > today}


def evaluate(rule: dict) -> dict:
    handler = KINDS.get(rule["kind"])
    try:
        status, evidence = handler(rule) if handler else (
            "UNKNOWN", [f"unknown kind: {rule['kind']}"])
    except Exception as error:  # one broken probe must not hide the other fifty
        status, evidence = "UNKNOWN", [f"probe error: {type(error).__name__}: {error}"]
    return {
        "id": rule["id"],
        "layer": rule["layer"],
        "category": rule.get("category", "other"),
        "title": rule["title"],
        "regression": bool(rule.get("regression")),
        "status": status,
        "evidence": evidence,
    }


def apply_waiver(result: dict, waivers: dict[str, dict]) -> dict:
    waiver = waivers.get(result["id"])
    if waiver and result["status"] == "FAIL":
        result["status"] = "WAIVED"
        result["evidence"] = [f"waived until {waiver['expires']}: {waiver['reason']}"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layer", default="all")
    parser.add_argument("--category", help="docs | arch | smell | security | tests | git")
    parser.add_argument("--root", help="grade this directory instead of the repo "
                        "(point it at a worktree of the release ref)")
    parser.add_argument("--out", help="write JSON here instead of stdout")
    args = parser.parse_args()

    if args.root:  # code is graded from the release branch, not the desk
        target = Path(args.root).resolve()
        ENGINE.ROOT = ANALYSIS.E.ROOT = GIT.ROOT = target

    config = load_json("config.json", {"layers": {}})
    catalogue = [rule for name in CATALOGUE for rule in load(name).RULES]
    rules = EXPAND.expand(catalogue, config, args.layer)
    if args.category:
        rules = [r for r in rules if r.get("category") == args.category]

    waivers = load_waivers()
    results = [apply_waiver(evaluate(rule), waivers) for rule in rules]
    document = json.dumps({
        "generated": datetime.now().isoformat(timespec="seconds"),
        "root": ENGINE.ROOT.as_posix(),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "head": git("rev-parse", "--short", "HEAD"),
        "scope": args.layer,
        "results": results,
    }, ensure_ascii=False, indent=2)

    if args.out:
        Path(args.out).write_text(document, encoding="utf-8")
        return
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(document)


if __name__ == "__main__":
    main()
