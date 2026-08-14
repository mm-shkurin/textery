"""Copy the backend-facing test cases into this repository, from the monorepo.

`backend/` is republished as its own repository, and `ProductSpecification/` does
not travel with it. The written test cases -- preconditions, steps, expected
results, per story -- therefore existed for the team and for nobody reading the
published repo: a reviewer cloning it saw automated test code and no test cases
at all.

Copies, not moves. `ProductSpecification/stories/*/tests/` stays the source of
truth: it is where `/test-spec` writes and where the story workflow reads. Every
file written here carries a banner saying so, so an edit lands upstream rather
than in a copy that the next sync overwrites.

UI tests are excluded on purpose -- they belong to the frontend repository, which
publishes its own copy.

Run it before pushing a release:

    python scripts/sync_test_cases.py          # write
    python scripts/sync_test_cases.py --check  # fail if the copy is stale

`--check` is for a monorepo pre-release step, not for this repo's CI: in the
split repository the source directory does not exist and the script exits saying
so rather than failing a pipeline that cannot possibly fix it.
"""

import shutil
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = BACKEND_ROOT.parent / "ProductSpecification" / "stories"
TARGET_ROOT = BACKEND_ROOT / "docs" / "testing"

# The five suites a backend reviewer is asked to judge. `02_UI_Tests` is the
# frontend's; `00_Hazard_Scan_Record` is a process artifact, not a test case.
BACKEND_SUITES = ("01_API", "03_Load", "04_Infrastructure", "05_Security", "06_Integration")

BANNER = (
    "<!-- COPIED FILE. Source of truth: {source}\n"
    "     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.\n"
    "     Edits made here are overwritten by the next sync. -->\n\n"
)


def _is_backend_suite(path: Path) -> bool:
    return path.suffix == ".md" and path.name.startswith(BACKEND_SUITES)


def _sources() -> list[tuple[Path, Path]]:
    """Every (source, target) pair, including the `extended/` subdirectories."""
    pairs: list[tuple[Path, Path]] = []
    for tests_dir in sorted(SOURCE_ROOT.glob("*/tests")):
        story = tests_dir.parent.name
        for source in sorted(tests_dir.rglob("*.md")):
            if not _is_backend_suite(source):
                continue
            pairs.append((source, TARGET_ROOT / story / source.relative_to(tests_dir)))
    return pairs


def _rendered(source: Path) -> str:
    relative = source.relative_to(BACKEND_ROOT.parent).as_posix()
    return BANNER.format(source=relative) + source.read_text(encoding="utf-8")


def main(check_only: bool) -> int:
    if not SOURCE_ROOT.is_dir():
        print(f"{SOURCE_ROOT} is absent -- this is the published repository, nothing to sync.")
        return 0

    pairs = _sources()
    if not pairs:
        print(f"no backend test cases found under {SOURCE_ROOT}")
        return 1

    stale = [
        target
        for source, target in pairs
        if not target.is_file() or target.read_text(encoding="utf-8") != _rendered(source)
    ]
    if check_only:
        if stale:
            print(f"{len(stale)} of {len(pairs)} test-case files are stale or missing:")
            for target in stale[:20]:
                print(f"  {target.relative_to(BACKEND_ROOT).as_posix()}")
            return 1
        print(f"{len(pairs)} test-case files are in sync.")
        return 0

    if TARGET_ROOT.exists():
        # Full rebuild: a story renamed or a suite deleted upstream must not leave
        # an orphan here, which would be a test case the jury reads and the team
        # no longer maintains.
        shutil.rmtree(TARGET_ROOT)
    for source, target in pairs:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_rendered(source), encoding="utf-8")
    print(f"wrote {len(pairs)} test-case files into {TARGET_ROOT.relative_to(BACKEND_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(check_only="--check" in sys.argv))
