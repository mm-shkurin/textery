"""Turn the generic rule catalogue into concrete per-layer probes.

A rule is written once with placeholders (`{code}`, `{src}`, `{root}`, …); this
module resolves them against `config.json` for every layer the rule applies to and
stamps the layer onto the id (`ARCH-SIZE@front`). Layer-boundary rules have no
entry in the catalogue at all — they are generated from each layer's declared
`forbidden_imports`, which is the only place a project's topology is written down.
"""
from __future__ import annotations

import re

TEST_PATHS = r"/tests?/|__tests__|\.test\.|\.spec\.|fixtures|test_|conftest"


def resolve(value, layer: dict, config: dict):
    if isinstance(value, list):
        out = []
        for item in value:
            resolved = resolve(item, layer, config)
            out.extend(resolved if isinstance(resolved, list) else [resolved])
        return out
    if not isinstance(value, str):
        return value
    if value == "{tests}":
        return TEST_PATHS
    whole = re.fullmatch(r"\{(\w+)\}", value)
    if whole:
        key = whole.group(1)
        found = layer.get(key, config.get(key))
        return TEST_PATHS if found is None and key == "tests" else found
    return re.sub(
        r"\{(\w+)\}",
        lambda m: str(layer.get(m.group(1), config.get(m.group(1), m.group(0)))),
        value,
    )


def expand(rules: list[dict], config: dict, wanted: str) -> list[dict]:
    """One catalogue entry becomes one probe per applicable layer."""
    out: list[dict] = []
    selected = {part.strip() for part in wanted.split(",") if part.strip()}
    for name, layer in config["layers"].items():
        if "all" not in selected and name not in selected:
            continue
        for rule in rules:
            applies = rule.get("applies", "*")
            if applies != "*" and name not in applies:
                continue
            # a UI-only concern (design tokens, abort signals) is not a finding
            # against a service layer, and vice versa
            if rule.get("layer_kind") and rule["layer_kind"] != layer.get("kind"):
                continue
            concrete = {k: resolve(v, layer, config) for k, v in rule.items()}
            concrete["id"] = f"{rule['id']}@{name}"
            concrete["layer"] = name
            if concrete["kind"] in GIT_KINDS:
                out.append(concrete)
                continue
            if not concrete.get("roots"):
                continue  # layer declares no such input
            if "globs" in rule and not concrete.get("globs"):
                continue  # e.g. a service layer with no stylesheets
            out.append(concrete)
        out.extend(boundary_rules(name, layer))
    return out


GIT_KINDS = {
    "git_tracked_artifacts", "git_bulk_commits", "git_message_convention",
    "git_direct_main", "git_language_consistency", "git_branch_naming",
}


def boundary_rules(name: str, layer: dict) -> list[dict]:
    """Dependency-direction probes, generated from the layer's own declaration."""
    rules = []
    for index, boundary in enumerate(layer.get("forbidden_imports", []), 1):
        rules.append({
            "id": f"ARCH-BOUNDARY-{index}@{name}",
            "layer": name,
            "category": "arch",
            "regression": True,
            "kind": "forbid",
            "title": boundary["name"],
            "roots": boundary["in"],
            "globs": layer.get("src", []),
            "exclude": TEST_PATHS,
            "regex": boundary["regex"],
        })
    return rules
