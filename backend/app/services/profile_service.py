"""Student profile service — profile extraction and management."""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.models.student_profile import StudentProfile
from app.models.student_profile_change_log import StudentProfileChangeLog
from app.models.student_profile_version import StudentProfileVersion
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
  "learning_stage": "学习阶段：foundation(基础夯实)/consolidating(基础巩固)/practice(强化练习)/review(错题复盘)/advanced(进阶拓展)",
  "resource_preference": ["mindmap", "quiz", "lecture_doc", "ppt"],
  "motivation": "学习动机强度：low/medium/high 或 null",
  "meta_learning_level": "元学习能力：low/medium/high",
  "emotion_tendency": "情绪倾向：anxious(焦虑)/confident(自信)/frustrated(受挫)/neutral(平稳) 或 null",
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
    "learning_stage": [
        (r"复习|错题|复盘|巩固", "review"),
        (r"练习|刷题|做题|强化", "practice"),
        (r"考研|深入|进阶|提高", "advanced"),
        (r"入门|初学|基础|夯实", "foundation"),
    ],
    "resource_preference": [
        (r"思维导图|脑图|mindmap", "mindmap"),
        (r"测验|题目|做题|quiz|练习", "quiz"),
        (r"讲义|笔记|lecture|讲解", "lecture_doc"),
        (r"PPT|ppt|课件", "ppt"),
    ],
    "emotion_tendency": [
        (r"焦虑|紧张|担心|害怕|没信心", "anxious"),
        (r"受挫|沮丧|挫折|灰心|烦躁", "frustrated"),
        (r"自信|有信心|擅长|轻松", "confident"),
    ],
}


def _rule_fallback(message: str) -> dict:
    """Extract profile fields using regex rules (fallback when LLM unavailable)."""
    result = {
        "knowledge_level": "intermediate",
        "cognitive_style": "conceptual",
        "pace_preference": "moderate",
        "learning_stage": "foundation",
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


def _profile_snapshot(profile: StudentProfile) -> dict:
    return {
        "major": profile.major,
        "learning_goal": profile.learning_goal,
        "knowledge_level": profile.knowledge_level,
        "cognitive_style": profile.cognitive_style,
        "weak_points": json.loads(profile.weak_points) if profile.weak_points else [],
        "pace_preference": profile.pace_preference,
        "learning_stage": profile.learning_stage,
        "resource_preference": json.loads(profile.resource_preference) if profile.resource_preference else [],
        "motivation": profile.motivation,
        "meta_learning_level": profile.meta_learning_level,
        "emotion_tendency": profile.emotion_tendency,
    }


def _append_change_logs(
    profile_id: int,
    old_snapshot: dict,
    new_snapshot: dict,
    source: str,
    trigger_text: str | None,
    session: Session,
) -> None:
    for field, old_value in old_snapshot.items():
        new_value = new_snapshot.get(field)
        if old_value != new_value:
            session.add(StudentProfileChangeLog(
                profile_id=profile_id,
                field_name=field,
                old_value=json.dumps(old_value, ensure_ascii=False) if isinstance(old_value, (list, dict)) else (None if old_value is None else str(old_value)),
                new_value=json.dumps(new_value, ensure_ascii=False) if isinstance(new_value, (list, dict)) else (None if new_value is None else str(new_value)),
                reason=f"profile updated via {source}",
                source_type=source,
                source_id=None,
            ))


def _merge_profile(profile: StudentProfile, extracted: dict, source: str = "dialogue", session: Session | None = None, trigger_text: str | None = None) -> StudentProfile:
    """Update profile fields from extracted dict (non-destructive merge)."""
    old_snapshot = _profile_snapshot(profile)
    changed = False
    for field in [
        "major", "learning_goal", "knowledge_level", "cognitive_style",
        "pace_preference", "learning_stage", "meta_learning_level", "motivation", "emotion_tendency",
    ]:
        val = extracted.get(field)
        if val is not None and getattr(profile, field) != val:
            setattr(profile, field, val)
            changed = True

    if extracted.get("weak_points"):
        new_wp = json.dumps(sorted(set(extracted["weak_points"])), ensure_ascii=False)
        if profile.weak_points != new_wp:
            profile.weak_points = new_wp
            changed = True
    if extracted.get("resource_preference"):
        new_rp = json.dumps(sorted(set(extracted["resource_preference"])), ensure_ascii=False)
        if profile.resource_preference != new_rp:
            profile.resource_preference = new_rp
            changed = True

    if extracted.get("raw_evidence"):
        profile.raw_evidence = extracted["raw_evidence"]

    profile.profile_source = source
    profile.profile_confidence = max(float(profile.profile_confidence or 0.0), float(extracted.get("confidence", 0.0) or 0.0))
    if changed:
        profile.profile_version = int(profile.profile_version or 1) + 1
    profile.updated_at = datetime.now(timezone.utc)
    profile.last_extracted_at = datetime.now(timezone.utc)

    if session is not None:
        new_snapshot = _profile_snapshot(profile)
        session.add(StudentProfileVersion(
            profile_id=int(profile.id) if profile.id else 0,
            version=int(profile.profile_version or 1),
            snapshot_json=json.dumps(new_snapshot, ensure_ascii=False),
            trigger_source=source,
            trigger_text=trigger_text,
            confidence=float(profile.profile_confidence or 0.0),
        ))
        _append_change_logs(int(profile.id) if profile.id else 0, old_snapshot, new_snapshot, source, trigger_text, session)

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
    source: str = "dialogue",
) -> dict:
    """Extract and save profile in one shot. Returns the extracted fields."""
    extracted = extract_profile(user, message, session)
    profile = get_or_create_profile(int(user.id) if user.id else 0, session)
    _merge_profile(profile, extracted, source=source, session=session, trigger_text=message)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    extracted["profile_source"] = profile.profile_source
    extracted["profile_version"] = profile.profile_version
    extracted["raw_evidence"] = profile.raw_evidence
    return extracted


def update_profile_from_behavior(
    user: User,
    session: Session,
    *,
    source: str,
    text: str,
    weak_points: list[str] | None = None,
    preferred_content: list[str] | None = None,
    learning_goal: str | None = None,
    knowledge_level: str | None = None,
    cognitive_style: str | None = None,
    learning_stage: str | None = None,
    learning_pace: str | None = None,
    motivation: str | None = None,
    confidence: float = 0.0,
) -> dict:
    """Incrementally update profile from behavior events (ask/quiz/bookmark/report)."""
    profile = get_or_create_profile(int(user.id) if user.id else 0, session)
    extracted = {
        "weak_points": weak_points or [],
        "resource_preference": preferred_content or [],
        "learning_goal": learning_goal,
        "knowledge_level": knowledge_level,
        "cognitive_style": cognitive_style,
        "pace_preference": learning_pace,
        "motivation": motivation,
        "confidence": confidence,
        "raw_evidence": text,
    }
    if learning_stage is not None:
        extracted["learning_stage"] = learning_stage
    _merge_profile(profile, extracted, source=source, session=session, trigger_text=text)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return {
        "profile_source": profile.profile_source,
        "profile_version": profile.profile_version,
        "profile_confidence": profile.profile_confidence,
    }
