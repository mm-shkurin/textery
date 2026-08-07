"""`.env.example` claims to list every variable the backend consumes. Hold it to that.

Its own header says so, and that claim is the only reason the file is worth
reading: an operator configuring a deployment has no other inventory of what the
process looks at. A variable that is read but not listed is invisible until
someone reads the composition root, and the failure it causes is a default
quietly applying in an environment that meant to override it.

`OAUTH_FAKE_AUTHORIZE_URL` was in exactly that state until 2026-08-07 -- read by
`container/oauth_wiring.py`, absent from the file that promised to name it.
"""

import re
from pathlib import Path

# The layer roots are separate sys.path entries, so `__file__` is the only honest
# way back to the backend directory: application/tests/<this file> -> backend/.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ENV_EXAMPLE = _BACKEND_ROOT / ".env.example"

_PRODUCTION_ROOTS = (
    "domain/src",
    "usecase/src",
    "adapters/rest/src",
    "adapters/db/src",
    "adapters/security/src",
    "adapters/rendering/src",
    "adapters/generation_provider/src",
    "adapters/oauth_provider/src",
    "application/src",
)

# The three ways this codebase reads the environment. Matching the literal rather
# than resolving a constant is deliberate: a variable named through an indirection
# is not discoverable by an operator reading the source either, so if one ever
# appears it should be given a literal here as well as an entry in the file.
_ENV_READ = re.compile(
    r"""(?:os\.)?(?:getenv|environ\.get)\(\s*["']([A-Z][A-Z0-9_]*)["']"""
    r"""|(?:os\.)?environ\[\s*["']([A-Z][A-Z0-9_]*)["']\s*\]"""
)

# Set by the test runner and by the container, never by an operator editing
# .env: DATABASE_URL is written over by the db suite's own URL guard, and
# TEST_DATABASE_URL only exists for that suite.
_NOT_OPERATOR_FACING = frozenset({"TEST_DATABASE_URL"})


def _variables_read_in_production_code() -> set[str]:
    found = set()
    for root in _PRODUCTION_ROOTS:
        for source in (_BACKEND_ROOT / root).rglob("*.py"):
            for match in _ENV_READ.finditer(source.read_text(encoding="utf-8")):
                found.add(match.group(1) or match.group(2))
    return found - _NOT_OPERATOR_FACING


def _variables_documented() -> set[str]:
    # Commented-out entries count as documented: `# YANDEX_REDIRECT_URI=` is how
    # this file marks an optional variable, and that is a description, not an
    # omission.
    text = _ENV_EXAMPLE.read_text(encoding="utf-8")
    return set(re.findall(r"^\s*#?\s*([A-Z][A-Z0-9_]*)\s*=", text, flags=re.MULTILINE))


class TestEnvExampleIsTheInventoryItClaimsToBe:
    def test_should_document_every_variable_production_code_reads(self):
        undocumented = sorted(_variables_read_in_production_code() - _variables_documented())

        assert undocumented == [], (
            f".env.example says it documents every variable the backend consumes, but "
            f"{undocumented} are read by production code and listed nowhere in it. An "
            f"operator has no way to discover them except by reading the composition "
            f"root, and the symptom of missing one is a default silently applying."
        )

    def test_should_find_the_variables_it_is_checking(self):
        """Guard the guard: an empty scan would satisfy the test above vacuously.

        The regex, the roots and the `.env.example` path are all things a refactor
        can break silently -- a moved layer root or a renamed file would leave
        `_variables_read_in_production_code()` returning nothing, and the real
        check would then pass no matter what was undocumented.
        """
        assert _ENV_EXAMPLE.is_file(), f"expected .env.example at {_ENV_EXAMPLE}"
        assert len(_variables_read_in_production_code()) >= 2, (
            "expected the scan to find the environment reads in the composition root; "
            "finding none means the regex or the source roots stopped matching, not "
            "that the code stopped reading the environment"
        )
        assert len(_variables_documented()) >= 10, (
            "expected .env.example to declare at least ten variables; finding fewer "
            "means the entry pattern stopped matching the file's format"
        )
