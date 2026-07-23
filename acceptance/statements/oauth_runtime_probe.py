import os
import subprocess

COMPOSE_FILE = os.path.join("infra", "docker-compose.yml")
BOOT_IMPORT = "import sys; sys.path.insert(0, 'backend/application/src'); import app.main"


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _compose(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, *args],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, **(env or {})},
    )


def backend_logs() -> str:
    """Everything the running backend has written, for the no-secrets-in-logs invariant.

    Deliberately NOT skip-on-missing-docker: the invariant gate is only meaningful if
    it actually reads a log, and a silently skipped secret-leak check is worse than a
    loud failure telling you to bring the stack up the documented way.
    """
    result = _compose("logs", "--no-color", "backend")
    assert result.returncode == 0, (
        "the log invariant needs the compose backend service running "
        f"(docker compose -f {COMPOSE_FILE} up -d backend); got: {result.stderr.strip()}"
    )
    return result.stdout + result.stderr


def boot_with_blank_provider_config() -> subprocess.CompletedProcess:
    """Boot the app image with the Yandex client id blanked out.

    Runs the import in a one-off container rather than in this process: fail-fast is a
    property of the deployed image's startup, and asserting it anywhere else would pass
    while the real container came up half-configured.
    """
    return _compose(
        "run",
        "--rm",
        "--no-deps",
        "-e",
        "YANDEX_CLIENT_ID=",
        "-e",
        "YANDEX_CLIENT_SECRET=",
        "backend",
        "python",
        "-c",
        BOOT_IMPORT,
    )
