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
The second one is absent in the published repository, and its check is skipped
there rather than failing a suite that cannot fix it.
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


@pytest.mark.parametrize(
    "dockerfile", [STANDALONE_DOCKERFILE, MONOREPO_DOCKERFILE], ids=["standalone", "monorepo"]
)
def test_the_image_puts_every_layer_root_on_the_import_path(dockerfile: Path):
    if not dockerfile.is_file():
        pytest.skip(f"{dockerfile} is absent — this is the published repository")

    declared = _pythonpath_line(dockerfile)
    missing = [name for name in _layer_roots() if f"/{name}/src" not in declared]

    assert missing == [], (
        f"{dockerfile.name} leaves {missing} off PYTHONPATH. The container will boot "
        "until the first import from that layer and then die with ModuleNotFoundError; "
        "nothing else in the suite can see it, because pytest gets its roots from "
        "pyproject.toml instead."
    )
