"""Version endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["version"], prefix="/api")


@router.get("/version")
async def get_version():
    return {
        "name": "intelligent-learning-agent",
        "phase": "phase-1-skeleton",
        "version": "0.1.0",
    }
