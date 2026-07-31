from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from health.check_health import CheckHealth

router = APIRouter(tags=["health"])

HEALTHY_STATUS = "ok"
UNHEALTHY_STATUS = "unavailable"


def get_check_health_usecase() -> CheckHealth:
    raise NotImplementedError("wired by the application composition root")


@router.get("/health")
async def check_health(
    usecase: CheckHealth = Depends(get_check_health_usecase),
) -> JSONResponse:
    """Liveness *and* readiness for the container probe.

    Unauthenticated, and outside `/api/v1`: the caller is the orchestrator, which
    holds no token, and the path is an operational surface rather than part of the
    versioned client API -- moving it under a version would make an infrastructure
    probe depend on an application version bump.

    503 rather than 200-with-a-body on failure. A probe reads the status code; a
    body saying `"unavailable"` under a 200 is a healthy container to every
    orchestrator that has ever shipped.

    The response names which dependency failed but never why. The reason is a
    driver error that can carry a host, a port, or a user name, and this endpoint
    is reachable without a token -- the same rule the other error handlers follow.
    The traceback goes to the log.
    """
    report = await usecase.execute()
    if not report.is_healthy:
        return JSONResponse(
            status_code=503,
            content={
                "status": UNHEALTHY_STATUS,
                "failed_dependencies": list(report.failed_dependencies),
            },
        )
    return JSONResponse(
        status_code=200, content={"status": HEALTHY_STATUS, "failed_dependencies": []}
    )
