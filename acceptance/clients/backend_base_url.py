import os

DEFAULT_BACKEND_PORT = "8000"


def backend_base_url() -> str:
    """The running backend's origin, from `BACKEND_PORT`.

    Parallel repo instances each run their backend on their own port, so the port is
    never hardcoded (see .claude/rules/infrastructure.md). Every acceptance client and
    statement resolves it here, so the env-var name and the fallback exist once: a
    second copy that drifted would silently point a subset of the suite at another
    session's backend, and the tests would pass or fail against the wrong process.
    """
    return f"http://localhost:{os.environ.get('BACKEND_PORT', DEFAULT_BACKEND_PORT)}"
