"""OpenAI-compatible API for LobeChat integration.

GET  /v1/models              → list available models
POST /v1/chat/completions    → chat completion (routes to LangGraph Tutor + Resource Generator)
"""

import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.auth import get_current_user_optional
from app.core.database import get_session
from app.models.course import Course
from app.models.user import User
from app.schemas.openai_compat import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ModelInfo,
    ModelList,
    UsageInfo,
)
from app.schemas.resource import ResourceType
from app.services.agent_graph import run_tutor_graph
from app.services.resource_generator import generate_resource_pack

router = APIRouter(tags=["openai-compat"])

OUR_MODEL_ID = "intelligent-learning-tutor"
OUR_MODEL_NAME = "智能学习 Tutor (LangGraph Multi-Agent)"

# Resource trigger patterns
_RESOURCE_PATTERNS: dict[ResourceType, list[str]] = {
    ResourceType.MINDMAP: ["思维导图", "知识图谱", "mindmap", "mind map", "脑图", "知识结构"],
    ResourceType.QUIZ: ["自测", "练习", "测验", "quiz", "考试", "测试", "题目", "做题"],
    ResourceType.LECTURE_DOC: ["讲解", "讲义", "lecture", "笔记", "课程", "教材"],
}


def _extract_question(messages: list[ChatMessage]) -> str:
    """Extract the last user message as the question."""
    for m in reversed(messages):
        if m.role == "user":
            return m.content.strip()
    return ""


def _detect_course_id(question: str, session: Session) -> Optional[int]:
    """Try to match course name in the question to a known course."""
    # Check for explicit course mentions
    courses = session.exec(select(Course)).all()
    for course in courses:
        name = course.name or ""
        if name and name in question:
            return int(course.id) if course.id else None
    # Default to first course
    if courses:
        return int(courses[0].id) if courses[0].id else None
    return None


def _detect_resource_types(question: str) -> list[ResourceType]:
    """Detect which resource types the user is asking for."""
    requested: set[ResourceType] = set()
    q_lower = question.lower()

    for rt, patterns in _RESOURCE_PATTERNS.items():
        if any(p.lower() in q_lower for p in patterns):
            requested.add(rt)

    return list(requested)


def _build_response_content(
    verified_answer: str,
    agent_trace: list[dict],
    student_profile: dict,
    citations: list[dict],
    resources: Optional[list] = None,
) -> str:
    """Build the final response content string with markdown formatting."""
    parts = []

    # Main answer
    parts.append(verified_answer)
    parts.append("")

    # Agent trace summary
    if agent_trace:
        agents = [t.get("agent", "?") for t in agent_trace]
        parts.append(f"---")
        parts.append(f"**Agent 协作链路**: {' → '.join(agents)}")

    # Student profile
    if student_profile:
        level = student_profile.get("knowledge_level", "?")
        style = student_profile.get("cognitive_style", "?")
        parts.append(f"**学生画像**: 水平={level}, 风格={style}")

    # Citations
    if citations:
        parts.append("")
        parts.append("**参考来源**:")
        seen = set()
        for c in citations:
            src = c.get("source", "unknown")
            if src not in seen:
                seen.add(src)
                parts.append(f"- {src}")

    # Resources hint
    if resources:
        parts.append("")
        parts.append("**生成资源**:")
        for r in resources:
            rtype = r.get("type", "?")
            title = r.get("title", "")
            parts.append(f"- [{rtype}] {title}")

    return "\n".join(parts)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/v1/models", response_model=ModelList)
def api_list_models():
    """List available models for LobeChat model selector."""
    return ModelList(
        data=[
            ModelInfo(
                id=OUR_MODEL_ID,
                owned_by="intelligent-learning-agent",
            )
        ]
    )


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
def api_chat_completions(
    body: ChatCompletionRequest,
    user: Optional[User] = Depends(get_current_user_optional),
    session: Session = Depends(get_session),
):
    """OpenAI-compatible chat completion endpoint.

    Routes to LangGraph multi-agent tutor. If resource generation keywords
    are detected, also generates mindmap/lecture/quiz.
    """
    if body.stream:
        raise HTTPException(status_code=400, detail="streaming not supported yet")

    question = _extract_question(body.messages)
    if not question:
        raise HTTPException(status_code=400, detail="no user message found")

    # Determine course
    course_id = body.course_id or _detect_course_id(question, session)
    if course_id is None:
        raise HTTPException(status_code=400, detail="no course available, please specify course_id")

    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail=f"course {course_id} not found")

    # Run LangGraph Tutor
    result = run_tutor_graph(
        course_id=course_id,
        course_name=course.name,
        question=question,
        top_k=5,
        session=session,
        user=user,
    )

    verified_answer = result.get("verified_answer", "")
    agent_trace = result.get("agent_trace", [])
    student_profile = result.get("student_profile", {})
    citations = result.get("citations", [])

    # Detect resource requests
    resource_types = _detect_resource_types(question)
    resource_items = []
    if resource_types:
        try:
            pack = generate_resource_pack(
                course_id=course_id,
                topic=question[:100],
                resource_types=resource_types,
                student_profile=student_profile,
                top_k=5,
                session=session,
                user=user,
            )
            # Convert to frontend-friendly format
            for res in pack.resources:
                item = {"type": res.type.value, "title": res.title}
                if res.mermaid:
                    item["mermaid"] = res.mermaid
                if res.content:
                    item["content"] = res.content[:2000]  # truncate for chat
                if res.items:
                    item["items"] = res.items
                resource_items.append(item)
        except Exception:
            pass  # resource generation is best-effort

    # Build response
    content = _build_response_content(
        verified_answer, agent_trace, student_profile, citations, resource_items
    )

    completion_tokens = len(content) // 2  # rough estimate

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
        choices=[
            ChatChoice(
                message=ChatMessage(role="assistant", content=content),
                finish_reason="stop",
            )
        ],
        usage=UsageInfo(
            prompt_tokens=len(question) // 2,
            completion_tokens=completion_tokens,
            total_tokens=len(question) // 2 + completion_tokens,
        ),
        agent_trace=agent_trace,
        citations=citations,
        student_profile=student_profile,
    )
