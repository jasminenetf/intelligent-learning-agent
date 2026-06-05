"""Study plan service — personalized learning path generation.

Combines: student profile + RAG retrieval + DeepSeek LLM
Outputs: structured study plan with ordered steps.
"""

import json
import logging
import re
from typing import Optional

from sqlmodel import Session

from app.models.course import Course
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.services.llm_provider import get_llm_provider
from app.services.rag_service import search_course

logger = logging.getLogger(__name__)

_STUDY_PLAN_PROMPT = """你是一位大学课程设计专家。请根据学生画像和课程资料，生成个性化学习路径。

学生画像：
{profile_text}

课程：{course_name}
学习主题：{topic}

课程相关资料：
{context_text}

请输出纯JSON（不要markdown标记）：
{{
  "title": "学习路径标题",
  "profile_summary": "基于画像的一句话总结",
  "steps": [
    {{
      "order": 1,
      "topic": "学习主题",
      "reason": "为什么先学这个（关联画像和前置知识）",
      "resource_types": ["mindmap", "lecture_doc"],
      "estimated_minutes": 20,
      "practice": "具体练习建议"
    }}
  ],
  "recommended_topics": ["建议后续学习主题"],
  "next_action": "下一步具体行动建议"
}}

要求：
1. 只输出JSON，不要其他文本。
2. steps 按学习顺序排列，至少3步。
3. 每步 resource_types 从 ["mindmap","lecture_doc","quiz","ppt"] 中选择。
4. 结合学生画像：知识薄弱点多安排练习，偏好可视化多安排mindmap。
5. 如果课程资料不足，在 profile_summary 中说明。
"""


def _chunks_to_text(chunks: list[dict], max_len: int = 2000) -> str:
    """Merge chunk contents into a single context string."""
    parts = []
    total = 0
    for i, c in enumerate(chunks):
        content = (c.get("content", "") or "").strip()
        if not content:
            continue
        src = c.get("source", "unknown")
        part = f"[来源{i+1}: {src}]\n{content}"
        if total + len(part) > max_len:
            remaining = max_len - total
            parts.append(part[:remaining] + "...")
            break
        parts.append(part)
        total += len(part)
    return "\n\n".join(parts)


def _build_profile_text(profile: Optional[StudentProfile]) -> str:
    """Format student profile as human-readable text."""
    if not profile:
        return "学生画像尚未建立。"

    lines = []
    if profile.major:
        lines.append(f"- 专业：{profile.major}")
    if profile.learning_goal:
        lines.append(f"- 学习目标：{profile.learning_goal}")
    lines.append(f"- 知识水平：{profile.knowledge_level}")
    lines.append(f"- 认知风格：{profile.cognitive_style}")
    if profile.weak_points:
        try:
            wps = json.loads(profile.weak_points)
            if wps:
                lines.append(f"- 薄弱知识点：{', '.join(wps)}")
        except (json.JSONDecodeError, TypeError):
            pass
    lines.append(f"- 学习节奏：{profile.pace_preference}")
    if profile.resource_preference:
        try:
            rps = json.loads(profile.resource_preference)
            if rps:
                lines.append(f"- 资源偏好：{', '.join(rps)}")
        except (json.JSONDecodeError, TypeError):
            pass
    return "\n".join(lines)


def _rule_plan(topic: str, profile_text: str) -> dict:
    """Generate a basic study plan without LLM (rule-based fallback)."""
    return {
        "title": f"{topic} 学习路径",
        "profile_summary": f"基于当前学习状态生成的 {topic} 学习路径（规则生成）",
        "steps": [
            {
                "order": 1,
                "topic": f"{topic} — 基础概念",
                "reason": "先建立核心概念理解",
                "resource_types": ["lecture_doc", "mindmap"],
                "estimated_minutes": 25,
                "practice": "阅读讲义后画出概念关系图",
            },
            {
                "order": 2,
                "topic": f"{topic} — 关键方法",
                "reason": "掌握基本方法和公式",
                "resource_types": ["lecture_doc", "quiz"],
                "estimated_minutes": 30,
                "practice": "完成基础练习题5道",
            },
            {
                "order": 3,
                "topic": f"{topic} — 综合应用",
                "reason": "巩固知识，提升解题能力",
                "resource_types": ["quiz", "ppt"],
                "estimated_minutes": 35,
                "practice": "完成综合练习题3道，回顾错题",
            },
        ],
        "recommended_topics": [f"{topic} 进阶", "相关知识点串联"],
        "next_action": f"从 {topic} 基础概念开始学习",
    }


def generate_study_plan(
    course_id: int,
    topic: str,
    profile: Optional[StudentProfile],
    session: Session,
    top_k: int = 5,
) -> dict:
    """Generate a personalized study plan.

    Pipeline: verify course → RAG search → build prompt → LLM → plan
    Falls back to rule-based plan if LLM unavailable.
    """
    course = session.get(Course, course_id)
    if not course:
        raise ValueError(f"course not found: {course_id}")

    # RAG search
    search_result = search_course(course_id, topic, min(top_k, 8), session)
    chunks = search_result.get("results", []) if "results" in search_result else []
    context = _chunks_to_text(chunks) if chunks else "（暂无课程资料）"
    profile_text = _build_profile_text(profile)

    # Try LLM
    try:
        provider = get_llm_provider()
        if provider.provider != "mock":
            prompt = _STUDY_PLAN_PROMPT.format(
                profile_text=profile_text,
                course_name=course.name or "当前课程",
                topic=topic,
                context_text=context,
            )
            resp = provider.generate([{"role": "user", "content": prompt}], temperature=0.3)
            content = resp.content.strip()
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            plan = json.loads(content)
            plan["provider"] = provider.provider
            plan["model"] = provider.model
            logger.info("Study plan generated via LLM")
            return plan
    except Exception as e:
        logger.warning("LLM study plan failed (%s), using rule fallback", e)

    # Rule fallback
    plan = _rule_plan(topic, profile_text)
    plan["provider"] = "rule"
    plan["model"] = "rule_based"
    return plan


def render_study_plan_markdown(plan: dict) -> str:
    """Render a study plan dict to Markdown."""
    lines = [
        f"# {plan.get('title', '学习路径')}",
        "",
        f"**画像总结**: {plan.get('profile_summary', '')}",
        "",
        "## 学习步骤",
        "",
    ]

    for step in plan.get("steps", []):
        order = step.get("order", "?")
        topic = step.get("topic", "")
        reason = step.get("reason", "")
        minutes = step.get("estimated_minutes", 0)
        rtypes = step.get("resource_types", [])
        practice = step.get("practice", "")
        lines.append(f"### 第{order}步：{topic}")
        lines.append(f"- **原因**: {reason}")
        lines.append(f"- **推荐资源**: {', '.join(rtypes)}")
        lines.append(f"- **预计时间**: {minutes} 分钟")
        lines.append(f"- **练习**: {practice}")
        lines.append("")

    if plan.get("recommended_topics"):
        lines.append("## 后续建议主题")
        for t in plan["recommended_topics"]:
            lines.append(f"- {t}")
        lines.append("")

    if plan.get("next_action"):
        lines.append(f"## 下一步行动")
        lines.append(f"> {plan['next_action']}")

    return "\n".join(lines)
