import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.infrastructure.db.connection import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


def database_is_ready() -> bool:
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        return True
    except Exception as error:
        logger.warning("Database readiness check failed: %s", error)
        return False


@router.get("")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/startup")
def startup() -> dict[str, str]:
    return {"status": "started"}


@router.get("/ready")
def readiness():
    if not database_is_ready():
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "checks": {"database": "down"},
            },
        )

    return {
        "status": "ready",
        "checks": {"database": "up"},
    }
