"""OpenAI-compatible API schemas for LobeChat integration.

Implements /v1/models and /v1/chat/completions endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── /v1/models ────────────────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    owned_by: str = "intelligent-learning-agent"


class ModelList(BaseModel):
    object: str = "list"
    data: list[ModelInfo]


# ── /v1/chat/completions ─────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., description="system/user/assistant")
    content: str = Field(..., min_length=1)


class ChatCompletionRequest(BaseModel):
    model: str = Field(default="intelligent-learning-tutor")
    messages: list[ChatMessage] = Field(..., min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=2048, ge=1)
    stream: bool = False
    # Custom extension: course_id for context
    course_id: Optional[int] = None


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str = ""
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str = "intelligent-learning-tutor"
    choices: list[ChatChoice]
    usage: UsageInfo = UsageInfo()
    # Custom extension: agent trace and citations
    agent_trace: Optional[list[dict]] = None
    citations: Optional[list[dict]] = None
    student_profile: Optional[dict] = None
