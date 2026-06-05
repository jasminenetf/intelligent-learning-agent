"""App settings API: configure LLM keys, test connections."""

import os
import time
import logging

from fastapi import APIRouter, HTTPException
from openai import OpenAI

from app.core.config import settings
from app.schemas.settings import (
    LLMConfigRequest,
    LLMTestRequest,
    LLMTestResponse,
    SettingsStatusResponse,
)
from app.services.llm_provider import reset_llm_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")


def _read_env_lines() -> list[str]:
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            return f.readlines()
    return []


def _write_env_lines(lines: list[str]):
    os.makedirs(os.path.dirname(ENV_PATH), exist_ok=True)
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return key[:2] + "***"
    return key[:4] + "***" + key[-4:]


@router.get("/status", response_model=SettingsStatusResponse)
def api_settings_status():
    """Return current app configuration status without exposing keys."""
    from app.services.llm_provider import get_llm_provider
    provider = get_llm_provider()
    spark_password = settings.SPARK_API_PASSWORD or settings.SPARK_API_KEY
    fallback_available = bool(settings.DEEPSEEK_API_KEY) if provider.provider == "spark" else (
        bool(settings.SPARK_API_PASSWORD or settings.SPARK_API_KEY) and settings.SPARK_ENABLED
    )
    return SettingsStatusResponse(
        llm_provider=provider.provider,
        llm_model=provider.model,
        is_mock=(provider.provider == "mock"),
        deepseek_configured=bool(settings.DEEPSEEK_API_KEY),
        deepseek_model=settings.DEEPSEEK_MODEL,
        spark_enabled=settings.SPARK_ENABLED,
        spark_configured=bool(spark_password),
        spark_model=settings.SPARK_MODEL,
        spark_base_url_configured=bool(settings.SPARK_BASE_URL),
        fallback_provider=settings.SPARK_FALLBACK_PROVIDER,
        fallback_available=fallback_available,
        embedding_provider=settings.EMBEDDING_PROVIDER,
        embedding_is_mock=(settings.EMBEDDING_PROVIDER == "hash_mock"),
    )


@router.post("/llm")
def api_save_llm_config(body: LLMConfigRequest):
    """Save LLM configuration to backend/.env."""
    provider = body.provider.strip().lower()
    if provider not in ("deepseek", "spark"):
        raise HTTPException(status_code=400, detail="provider must be deepseek or spark")

    lines = _read_env_lines()

    if provider == "spark":
        updates = {
            "LLM_PROVIDER": provider,
            "SPARK_ENABLED": "true",
            "SPARK_API_PASSWORD": body.api_key,
            "SPARK_BASE_URL": body.base_url,
            "SPARK_MODEL": body.model,
        }
    else:
        timeout = body.timeout_seconds if body.timeout_seconds > 0 else 60
        updates = {
            "LLM_PROVIDER": provider,
            f"DEEPSEEK_API_KEY": body.api_key,
            f"DEEPSEEK_BASE_URL": body.base_url,
            f"DEEPSEEK_MODEL": body.model,
            f"DEEPSEEK_TIMEOUT_SECONDS": str(timeout),
            f"LLM_TIMEOUT_SECONDS": str(timeout),
        }

    new_lines = []
    updated = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                updated.add(key)
                continue
        new_lines.append(line)

    for key, val in updates.items():
        if key not in updated:
            new_lines.append(f"{key}={val}\n")

    try:
        _write_env_lines(new_lines)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to save config: {e}")

    # Apply in process
    try:
        settings.LLM_PROVIDER = provider
        if provider == "deepseek":
            settings.DEEPSEEK_API_KEY = body.api_key
            settings.DEEPSEEK_BASE_URL = body.base_url
            settings.DEEPSEEK_MODEL = body.model
            timeout = body.timeout_seconds if body.timeout_seconds > 0 else 60
            settings.DEEPSEEK_TIMEOUT_SECONDS = timeout
            settings.LLM_TIMEOUT_SECONDS = timeout
        elif provider == "spark":
            settings.SPARK_ENABLED = True
            settings.SPARK_API_PASSWORD = body.api_key
            settings.SPARK_BASE_URL = body.base_url
            settings.SPARK_MODEL = body.model
        reset_llm_provider()
    except Exception:
        pass

    # Log WITHOUT the key
    masked = _mask_key(body.api_key)
    logger.info("LLM config saved: provider=%s model=%s key=%s", provider, body.model, masked)
    return {
        "ok": True,
        "provider": provider,
        "saved": True,
        "applied": True,
        "hint": "配置已保存，请测试连接；如状态未刷新，可重启后端"
    }


@router.post("/test-llm", response_model=LLMTestResponse)
def api_test_llm(body: LLMTestRequest):
    """Test LLM connection for deepseek or spark."""
    req_provider = (body.provider or settings.LLM_PROVIDER).strip().lower()

    if req_provider == "spark":
        spark_key = settings.SPARK_API_PASSWORD or settings.SPARK_API_KEY
        if not spark_key:
            return LLMTestResponse(
                ok=False, provider="spark",
                error="讯飞星火未配置 APIPassword",
                message="讯飞星火连接失败，请检查 APIPassword 配置"
            )
        api_key = spark_key
        base_url = settings.SPARK_BASE_URL
        model = body.model or settings.SPARK_MODEL
        provider_label = "spark"
        fallback_available = bool(settings.DEEPSEEK_API_KEY)
    else:
        if not settings.DEEPSEEK_API_KEY:
            return LLMTestResponse(
                ok=False, provider="deepseek",
                error="DeepSeek API Key 未配置",
                message="请先在设置页填写 DeepSeek API Key",
                fallback_available=False
            )
        api_key = settings.DEEPSEEK_API_KEY
        base_url = settings.DEEPSEEK_BASE_URL
        model = body.model or settings.DEEPSEEK_MODEL
        provider_label = "deepseek"
        fallback_available = (bool(settings.SPARK_API_PASSWORD or settings.SPARK_API_KEY) and settings.SPARK_ENABLED)

    # Validate model name for deepseek-v4-pro
    is_v4_pro = (provider_label == "deepseek" and model == "deepseek-v4-pro")

    try:
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=15, max_retries=1)
        t0 = time.time()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": body.message}],
            max_tokens=100,
        )
        latency = (time.time() - t0) * 1000
        content = resp.choices[0].message.content or ""

        # Build success message
        if provider_label == "deepseek":
            model_display = "DeepSeek V4 Pro" if is_v4_pro else f"DeepSeek ({model})"
            msg = f"{model_display} 连接成功"
        elif provider_label == "spark":
            msg = f"讯飞星火 ({model}) 连接成功"
        else:
            msg = f"{provider_label} 连接成功"

        return LLMTestResponse(
            ok=True,
            provider=provider_label,
            model=model,
            response=content[:500],
            latency_ms=round(latency, 1),
            message=msg,
            fallback_available=fallback_available,
        )
    except Exception as e:
        msg = str(e)[:300]
        logger.warning("LLM test failed: provider=%s model=%s error=%s", provider_label, model, msg[:100])

        # Build Chinese error message
        if provider_label == "deepseek":
            if is_v4_pro:
                error_msg = f"DeepSeek V4 Pro 连接失败，请检查 API Key、模型权限或账户余额"
                hint = "deepseek-v4-pro 如无权限，可改用 deepseek-v4-flash 或旧兼容模型 deepseek-chat"
            else:
                error_msg = f"DeepSeek 连接失败，请检查 API Key、模型权限或账户余额"
                hint = None
        elif provider_label == "spark":
            error_msg = f"讯飞星火连接失败: {msg[:80]}"
            hint = None
        else:
            error_msg = f"连接失败: {msg[:80]}"
            hint = None

        result = LLMTestResponse(
            ok=False,
            provider=provider_label,
            model=model,
            error=error_msg,
            message=hint or error_msg,
            fallback_available=fallback_available,
        )
        return result
