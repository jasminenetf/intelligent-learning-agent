"""Xfyun Virtual Human / Digital Avatar service.

API docs: https://www.xfyun.cn/doc/virtual-human/

Endpoints:
- POST /v1/private/vms2d_start  — start session
- POST /v1/private/vms2d_ctrl   — text-driven speech
- POST /v1/private/vms2d_audio_ctrl — audio-driven speech
- POST /v1/private/vms2d_stop   — stop session
- POST /v1/private/vms2d_ping   — heartbeat
"""

import hashlib
import hmac
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class XfyunVirtualHumanService:
    """Xfyun Virtual Human 2D service — backend proxy for digital avatar."""

    def __init__(self):
        self.enabled = settings.VIRTUAL_HUMAN_ENABLED
        self.api_key = settings.XFYUN_VH_API_KEY
        self.api_secret = settings.XFYUN_VH_API_SECRET
        self.base_url = settings.XFYUN_VH_BASE_URL.rstrip("/")
        self.avatar_id = settings.XFYUN_VH_AVATAR_ID
        self.voice_id = settings.XFYUN_VH_VOICE_ID
        self.timeout = settings.VH_TIMEOUT_SECONDS

    def _build_auth_url(self, path: str) -> str:
        """Build signed URL with Xfyun VH auth parameters."""
        host = self.base_url.replace("https://", "").replace("http://", "")
        now = datetime.now(timezone.utc)
        date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

        signature_origin = f"host: {host}\ndate: {date}\nPOST {path} HTTP/1.1"
        signature = hmac.new(
            self.api_secret.encode(),
            signature_origin.encode(),
            hashlib.sha256,
        ).digest()
        signature_b64 = __import__("base64").b64encode(signature).decode()

        authorization = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature_b64}"'
        )
        return f"{self.base_url}{path}", {
            "Host": host,
            "Date": date,
            "Authorization": authorization,
        }

    def get_status(self) -> dict:
        return {
            "ok": True,
            "enabled": self.enabled,
            "configured": bool(self.enabled and self.api_key and self.api_secret),
            "provider": "xfyun" if self.enabled else "none",
            "avatar_id": self.avatar_id or "(not set)",
            "voice_id": self.voice_id,
        }

    def _post(self, path: str, body: dict) -> dict:
        if not self.enabled or not self.api_key:
            return {
                "ok": False,
                "error_code": "VIRTUAL_HUMAN_NOT_CONFIGURED",
                "message": "数字人服务尚未配置，可继续使用普通学习助手",
            }

        url, headers = self._build_auth_url(path)
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=body)
                data = resp.json() if resp.text else {}
                return {
                    "ok": resp.status_code < 400,
                    "status_code": resp.status_code,
                    "data": data,
                    "provider": "xfyun",
                }
        except Exception as e:
            logger.warning("Xfyun VH request failed: %s", e)
            return {
                "ok": False,
                "error_code": "VH_REQUEST_FAILED",
                "message": f"数字人服务请求失败: {e}",
            }

    def start_session(self) -> dict:
        body = {
            "header": {
                "app_id": self.avatar_id or "default",
                "uid": f"hermes-{uuid.uuid4().hex[:8]}",
            },
            "parameter": {
                "vms2d": {
                    "avatar_id": self.avatar_id,
                    "voice_id": self.voice_id,
                }
            },
        }
        return self._post("/v1/private/vms2d_start", body)

    def speak_text(self, text: str) -> dict:
        body = {
            "header": {"app_id": self.avatar_id or "default"},
            "parameter": {"vms2d": {"command": "speak", "text": text[:1000]}},
        }
        return self._post("/v1/private/vms2d_ctrl", body)

    def stop_session(self) -> dict:
        body = {"header": {"app_id": self.avatar_id or "default"}}
        return self._post("/v1/private/vms2d_stop", body)

    def ping(self) -> dict:
        body = {"header": {"app_id": self.avatar_id or "default"}}
        return self._post("/v1/private/vms2d_ping", body)


_vh_service: Optional[XfyunVirtualHumanService] = None


def get_vh_service() -> XfyunVirtualHumanService:
    global _vh_service
    if _vh_service is None:
        _vh_service = XfyunVirtualHumanService()
    return _vh_service
