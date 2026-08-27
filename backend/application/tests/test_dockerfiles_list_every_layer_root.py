"""Every layer root must be on the image's PYTHONPATH — both images.

`main.py` stopped patching `sys.path` at import (that was a broken package setup
wearing a workaround), so the list in the Dockerfile is now the ONLY thing that
makes a layer importable. The failure mode is a container that dies at boot with
`ModuleNotFoundError`, and it is invisible until deploy: the suite gets its roots
from `pyproject.toml`, so a missing entry here is green everywhere except on the
running stand.

That is not hypothetical. `adapters/geolocation_provider` shipped with story 14
and was added to `backend/Dockerfile` but not to `infra/docker/backend.Dockerfile`;
the deploy crashed on `No module named 'geolocation'`.

Two images, because the directory is published as its own repository:
`backend/Dockerfile` builds with this directory as context, and
`infra/docker/backend.Dockerfile` builds the monorepo's stack from the repo root.
The second one is absent in the published repository, so the parameter list is built
from the images that are actually present rather than skipped at run time. A skip is
indistinguishable from a check that silently stopped running; `test_at_least_one_image_is_checked`
is what keeps an empty list from reading as a pass.
"""

from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STANDALONE_DOCKERFILE = BACKEND_ROOT / "Dockerfile"
MONOREPO_DOCKERFILE = BACKEND_ROOT.parent / "infra" / "docker" / "backend.Dockerfile"


def _layer_roots() -> list[str]:
    """Every directory that is a layer root: `<layer>/src` holding importable code."""
    roots = [BACKEND_ROOT / "domain", BACKEND_ROOT / "usecase", BACKEND_ROOT / "application"]
    roots += sorted(p for p in (BACKEND_ROOT / "adapters").iterdir() if (p / "src").is_dir())
    return [p.name for p in roots]


def _pythonpath_line(dockerfile: Path) -> str:
    for line in dockerfile.read_text(encoding="utf-8").splitlines():
        if line.startswith("ENV PYTHONPATH="):
            return line
    raise AssertionError(f"{dockerfile} declares no ENV PYTHONPATH")


def _present_dockerfiles() -> list[Path]:
    """The images this checkout actually contains.

    `infra/docker/backend.Dockerfile` exists only in the monorepo; the published
    repository is the `backend/` directory alone. Filtering here rather than skipping
    inside the test keeps the suite free of run-time skips, which hide a check that
    has stopped running behind the same green as one that ran.
    """
    return [p for p in (STANDALONE_DOCKERFILE, MONOREPO_DOCKERFILE) if p.is_file()]


def test_at_least_one_image_is_checked():
    """The standalone image is present in every checkout, so an empty list is a bug here."""
    present = _present_dockerfiles()

    assert STANDALONE_DOCKERFILE in present, (
        f"{STANDALONE_DOCKERFILE} is missing. Without it the parametrised check below "
        "collects nothing and the suite passes while verifying no image at all."
    )


@pytest.mark.parametrize("dockerfile", _present_dockerfiles(), ids=lambda p: p.parent.name)
def test_the_image_puts_every_layer_root_on_the_import_path(dockerfile: Path):
    declared = _pythonpath_line(dockerfile)
    missing = [name for name in _layer_roots() if f"/{name}/src" not in declared]

    assert missing == [], (
        f"{dockerfile.name} leaves {missing} off PYTHONPATH. The container will boot "
        "until the first import from that layer and then die with ModuleNotFoundError; "
        "nothing else in the suite can see it, because pytest gets its roots from "
        "pyproject.toml instead."
    )
