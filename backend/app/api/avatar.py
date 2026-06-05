"""Digital Avatar API — Xfyun Virtual Human backend proxy."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.virtual_human_service import get_vh_service

router = APIRouter(prefix="/api/avatar", tags=["avatar"])


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    source: str = Field(default="answer", description="answer|study_plan|mindmap")


@router.get("/status")
def avatar_status():
    """Get avatar service status. No auth required."""
    svc = get_vh_service()
    return svc.get_status()


@router.post("/speak")
def avatar_speak(body: SpeakRequest):
    """Drive avatar to speak the given text."""
    svc = get_vh_service()
    if not svc.enabled:
        return {
            "ok": False,
            "error_code": "VIRTUAL_HUMAN_NOT_CONFIGURED",
            "message": "数字人服务尚未配置，可继续使用普通学习助手",
        }
    result = svc.speak_text(body.text)
    return {
        **result,
        "source": body.source,
        "text_length": len(body.text),
    }
