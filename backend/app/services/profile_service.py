"""Student profile service — profile extraction and management."""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.models.student_profile import StudentProfile
from app.models.user import User
from app.services.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """你是一位教育数据分析专家。请从以下学生自述中提取学习画像，输出纯JSON（不要markdown标记）。

学生自述：
{message}

输出JSON格式：
{{
  "major": "专业/学科（如 计算机、数学、物理 等，无法判断填null）",
  "learning_goal": "学习目标（一句话概括，无法判断填null）",
  "knowledge_level": "知识基础：beginner/intermediate/advanced",
  "cognitive_style": "认知风格：conceptual(概念型)/logical(逻辑推理型)/practice_oriented(实践型)",
  "weak_points": ["知识短板1", "知识短板2"],
  "pace_preference": "学习节奏：slow/moderate/fast",
  "resource_preference": ["mindmap", "quiz", "lecture_doc", "ppt"],
  "motivation": "学习动机强度：low/medium/high 或 null",
  "meta_learning_level": "元学习能力：low/medium/high",
  "confidence": 0.0-1.0之间的置信度
}}

要求：
1. 只输出JSON，不要任何其他文本。
2. weak_points 是学生提到的不懂/薄弱的学科知识点。
3. resource_preference 根据学生提到的偏好从 ["mindmap","quiz","lecture_doc","ppt"] 中选择。
4. 如果某个字段无法判断，knowledge_level/cognitive_style/pace_preference/meta_learning_level 用默认值，其他填null或[]。
"""

_RULE_PATTERNS = {
    "knowledge_level": [
        (r"基础[较很]?差|初学|入门|不会|不懂|零基础", "beginner"),
        (r"考研|深入|证明|理论|研究|高级", "advanced"),
    ],
    "cognitive_style": [
        (r"图|思维导图|脑图|可视化|画", "conceptual"),
        (r"证明|推导|逻辑|推理", "logical"),
        (r"练习|做题|例子|例题|应用|实践", "practice_oriented"),
    ],
    "pace_preference": [
        (r"慢[一点些]|仔细|慢一点|慢慢", "slow"),
        (r"快[一点些]|快速|速成|赶时间", "fast"),
    ],
    "resource_preference": [
        (r"思维导图|脑图|mindmap", "mindmap"),
        (r"测验|题目|做题|quiz|练习", "quiz"),
        (r"讲义|笔记|lecture|讲解", "lecture_doc"),
        (r"PPT|ppt|课件", "ppt"),
    ],
}


def _rule_fallback(message: str) -> dict:
    """Extract profile fields using regex rules (fallback when LLM unavailable)."""
    result = {
        "knowledge_level": "intermediate",
        "cognitive_style": "conceptual",
        "pace_preference": "moderate",
        "resource_preference": [],
        "meta_learning_level": "medium",
        "confidence": 0.3,
    }

    for field, patterns in _RULE_PATTERNS.items():
        if field == "resource_preference":
            prefs = []
            for pat, val in patterns:
                if re.search(pat, message, re.IGNORECASE):
                    if val not in prefs:
                        prefs.append(val)
            if prefs:
                result["resource_preference"] = prefs
                result["confidence"] = max(result["confidence"], 0.4)
        else:
            for pat, val in patterns:
                if re.search(pat, message, re.IGNORECASE):
                    result[field] = val
                    result["confidence"] = max(result["confidence"], 0.5)
                    break

    # Extract major
    major_match = re.search(r"(计算机|数学|物理|化学|生物|英语|机械|电子|经济|管理)", message)
    result["major"] = major_match.group(1) if major_match else None

    # Extract weak points
    weak_match = re.findall(r"(?:不会|不懂|薄弱|差)[：:]*([^，。,\.\n]{2,20})", message)
    result["weak_points"] = weak_match[:5] if weak_match else []

    return result


def extract_profile(user: User, message: str, session: Session) -> dict:
    """Extract student profile from natural language description.

    Uses DeepSeek real LLM when available, falls back to regex rules.
    """
    # Try LLM extraction
    try:
        provider = get_llm_provider()
        if provider.provider != "mock":
            prompt = _EXTRACTION_PROMPT.format(message=message)
            resp = provider.generate([{"role": "user", "content": prompt}], temperature=0.1)
            content = resp.content.strip()
            # Strip markdown code fences
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            extracted = json.loads(content)
            extracted["confidence"] = max(0.6, float(extracted.get("confidence", 0.6)))
            logger.info("Profile extracted via LLM (confidence=%.2f)", extracted["confidence"])
            return extracted
    except Exception as e:
        logger.warning("LLM profile extraction failed (%s), using rule fallback", e)

    # Rule fallback
    extracted = _rule_fallback(message)
    logger.info("Profile extracted via rules (confidence=%.2f)", extracted["confidence"])
    return extracted


def _merge_profile(profile: StudentProfile, extracted: dict) -> StudentProfile:
    """Update profile fields from extracted dict (non-destructive merge)."""
    for field in [
        "major", "learning_goal", "knowledge_level", "cognitive_style",
        "pace_preference", "meta_learning_level", "motivation",
    ]:
        val = extracted.get(field)
        if val is not None:
            setattr(profile, field, val)

    # JSON fields
    if extracted.get("weak_points"):
        profile.weak_points = json.dumps(extracted["weak_points"], ensure_ascii=False)
    if extracted.get("resource_preference"):
        profile.resource_preference = json.dumps(extracted["resource_preference"], ensure_ascii=False)

    # Evidence
    if extracted.get("raw_evidence"):
        profile.raw_evidence = extracted["raw_evidence"]

    profile.updated_at = datetime.now(timezone.utc)
    profile.last_extracted_at = datetime.now(timezone.utc)
    return profile


def get_or_create_profile(user_id: int, session: Session) -> StudentProfile:
    """Get existing profile or create default."""
    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    ).first()

    if not profile:
        profile = StudentProfile(user_id=user_id)
        session.add(profile)
        session.commit()
        session.refresh(profile)

    return profile


def update_profile_from_extraction(
    user: User,
    message: str,
    session: Session,
) -> dict:
    """Extract and save profile in one shot. Returns the extracted fields."""
    extracted = extract_profile(user, message, session)
    profile = get_or_create_profile(int(user.id) if user.id else 0, session)
    _merge_profile(profile, extracted)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return extracted
