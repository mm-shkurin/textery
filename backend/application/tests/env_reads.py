"""Find every environment variable production code reads, including via a constant.

Written with `ast` rather than a regex, and that is not a style preference. The
regex version of this shipped on 2026-08-07 and matched only inline literals like
`os.environ.get("YANDEX_REDIRECT_URI")`. Most of this codebase does not write them
that way -- `logging_config` reads `LOG_LEVEL_ENV_VAR`, `runtime` reads
`STALE_AFTER_MINUTES_ENV_VAR`, `api_docs` reads `API_DOCS_ENABLED_ENV_VAR` -- so
the scan found 2 variables out of 15 and the check it fed passed by looking at
almost nothing. It proved that the day `API_DOCS_ENABLED` was added undocumented
and the guard stayed green.

The constant indirection is the codebase's own convention and worth keeping: the
name is then written once and shared between the reader and its tests. So the
scanner resolves it instead of the source being asked to change.
"""

import ast
from pathlib import Path


def _is_environ(node: ast.expr) -> bool:
    """`os.environ` or the bare `environ` a `from os import environ` produces."""
    if isinstance(node, ast.Attribute):
        return node.attr == "environ"
    return isinstance(node, ast.Name) and node.id == "environ"


def _is_environ_read(func: ast.expr) -> bool:
    """`os.environ.get` / `environ.get` / `os.getenv` / `getenv`, and nothing else.

    The object matters, not just the method name. Accepting any `.get(...)` --
    which the first version of this did -- pulls in every dictionary lookup in the
    codebase, so the check it feeds reported `/health` and a URL template as
    undocumented environment variables.
    """
    if isinstance(func, ast.Attribute):
        return (func.attr == "get" and _is_environ(func.value)) or func.attr == "getenv"
    return isinstance(func, ast.Name) and func.id == "getenv"


def _string_constants(tree: ast.Module) -> dict[str, str]:
    """Module-level `NAME = "literal"` bindings.

    Module level only, and deliberately: an environment variable name assembled
    inside a function is not discoverable by an operator reading the file either,
    so it should not be silently accepted by the check this feeds.
    """
    bound: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        if not isinstance(node.value.value, str):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                bound[target.id] = node.value.value
    return bound


def _resolved(node: ast.expr, constants: dict[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _environ_wrappers(tree: ast.Module) -> set[str]:
    """Module-level functions that read the environment out of their own parameter.

    `oauth_wiring` defines `_require(var_name)` and calls it as
    `_require("YANDEX_CLIENT_ID")`. Nothing in that call reaches `os.environ`
    syntactically, so a scan looking only for direct reads misses the variable
    entirely -- and a wrapper is the most natural way for the next one to become
    invisible without anyone intending it.

    Only the single-parameter shape is recognised, and only one level deep. A
    wrapper around a wrapper is not resolved; if one ever appears, this returns
    less than the truth, and the honest consequence is that the check goes quiet
    rather than wrong. The guard test's minimum count is what would notice.
    """
    wrappers = set()
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or len(node.args.args) != 1:
            continue
        parameter = node.args.args[0].arg
        for inner in ast.walk(node):
            reads_call = (
                isinstance(inner, ast.Call)
                and inner.args
                and _is_environ_read(inner.func)
                and isinstance(inner.args[0], ast.Name)
                and inner.args[0].id == parameter
            )
            reads_subscript = (
                isinstance(inner, ast.Subscript)
                and _is_environ(inner.value)
                and isinstance(inner.slice, ast.Name)
                and inner.slice.id == parameter
            )
            if reads_call or reads_subscript:
                wrappers.add(node.name)
                break
    return wrappers


def _reads_in(tree: ast.Module, constants: dict[str, str]) -> set[str]:
    found: set[str] = set()
    wrappers = _environ_wrappers(tree)
    for node in ast.walk(tree):
        # _require("X"), where `_require` was found to read os.environ[its parameter]
        if (
            isinstance(node, ast.Call)
            and node.args
            and isinstance(node.func, ast.Name)
            and node.func.id in wrappers
        ):
            resolved = _resolved(node.args[0], constants)
            if resolved:
                found.add(resolved)
        # os.environ.get("X") / environ.get("X") / os.getenv("X") / getenv("X")
        if isinstance(node, ast.Call) and node.args and _is_environ_read(node.func):
            resolved = _resolved(node.args[0], constants)
            if resolved:
                found.add(resolved)
        # os.environ["X"] / environ["X"]
        elif isinstance(node, ast.Subscript) and _is_environ(node.value):
            resolved = _resolved(node.slice, constants)
            if resolved:
                found.add(resolved)
    return found


def environment_reads(roots: tuple[Path, ...]) -> set[str]:
    """Every variable name read from the environment under `roots`."""
    found: set[str] = set()
    for root in roots:
        for source in root.rglob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
            found |= _reads_in(tree, _string_constants(tree))
    return found
