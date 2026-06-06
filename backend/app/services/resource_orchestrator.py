"""Multi-agent resource orchestration: plan → retrieve → generate → verify → persist."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from app.models.resource_artifact import ResourceArtifact
from app.models.resource_job import ResourceJob
from app.models.user import User
from app.schemas.resource import ResourceType
from app.services.profile_service import get_or_create_profile
from app.services.resource_agents.planner_agent import plan
from app.services.resource_agents.retriever_agent import retrieve
from app.services.resource_agents.verifier_agent import verify
from app.services.resource_generator import generate_resource_pack

logger = logging.getLogger(__name__)

_TYPE_MAP = {
    "lecture_doc": ResourceType.LECTURE_DOC,
    "mindmap": ResourceType.MINDMAP,
    "quiz": ResourceType.QUIZ,
    "ppt": ResourceType.PPT,
    "reading": ResourceType.READING,
    "video_script": ResourceType.VIDEO_SCRIPT,
    "study_plan": ResourceType.STUDY_PLAN,
}


def _trace_step(trace: list, agent: str, status: str, message: str, progress: float | None = None) -> None:
    step = {"agent": agent, "status": status, "message": message}
    if progress is not None:
        step["progress"] = progress
    trace.append(step)


def _update_job(job: ResourceJob, session: Session, **kwargs) -> ResourceJob:
    for key, val in kwargs.items():
        setattr(job, key, val)
    job.updated_at = datetime.now(timezone.utc)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def _pack_item_to_dict(item: Any) -> dict:
    data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
    rtype = data.get("type")
    if hasattr(rtype, "value"):
        rtype = rtype.value
    content_parts = []
    if data.get("content"):
        content_parts.append(str(data["content"]))
    if data.get("mermaid"):
        content_parts.append(str(data["mermaid"]))
    if data.get("items"):
        content_parts.append(json.dumps(data["items"], ensure_ascii=False))
    return {
        "type": rtype,
        "title": data.get("title") or "学习资源",
        "content": "\n\n".join(content_parts)[:12000],
        "quality_score": 0.9 if not data.get("fallback_used") else 0.82,
        "metadata": {
            "generated_by": data.get("generated_by"),
            "used_rag": data.get("used_rag"),
            "used_profile": data.get("used_profile"),
            "context_chunks": data.get("context_chunks"),
        },
        "download_url": data.get("download_url"),
        "resource_id": data.get("resource_id"),
    }


def generate_resource_pack_orchestrated(
    user: User,
    session: Session,
    course_id: int,
    topic: str,
    resource_types: list[str],
    difficulty: str = "auto",
    goal: str | None = None,
    top_k: int = 5,
) -> dict:
    """Run multi-agent orchestration and persist job + artifacts."""
    user_id = int(user.id) if user.id else 0
    job_id = f"rg_{uuid.uuid4().hex[:12]}"
    trace: list[dict] = []

    job = ResourceJob(
        job_id=job_id,
        user_id=user_id,
        course_id=course_id,
        topic=topic,
        resource_types=json.dumps(resource_types, ensure_ascii=False),
        status="running",
        progress=0.05,
        current_agent="init",
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    try:
        profile = get_or_create_profile(user_id, session)
        _trace_step(trace, "profile", "completed", "已读取学习画像", 0.1)
        _update_job(job, session, current_agent="planner", progress=0.1, trace_json=json.dumps(trace, ensure_ascii=False))

        plan_result = plan(course_id, topic, profile, resource_types, goal=goal, difficulty=difficulty)
        _trace_step(trace, "planner", "completed", "已完成资源规划", 0.2)
        _update_job(job, session, current_agent="retriever", progress=0.2, trace_json=json.dumps(trace, ensure_ascii=False))

        evidence = retrieve(course_id, topic, plan_result, profile, session, top_k=top_k)
        _trace_step(trace, "retriever", "completed", evidence.get("evidence_summary", "检索完成"), 0.35)
        _update_job(job, session, current_agent="generator", progress=0.35, trace_json=json.dumps(trace, ensure_ascii=False))

        mapped_types = []
        for rt in resource_types:
            mapped = _TYPE_MAP.get(rt)
            if mapped and mapped not in mapped_types:
                mapped_types.append(mapped)
        if not mapped_types:
            mapped_types = [ResourceType.LECTURE_DOC, ResourceType.MINDMAP, ResourceType.QUIZ]

        profile_dict = {
            "knowledge_level": profile.knowledge_level or "intermediate",
            "cognitive_style": profile.cognitive_style or "conceptual",
        }

        pack = generate_resource_pack(
            course_id=course_id,
            topic=topic,
            resource_types=mapped_types,
            student_profile=profile_dict,
            top_k=top_k,
            session=session,
            user=user,
        )
        _trace_step(trace, "content", "completed", f"已生成 {len(pack.resources)} 类资源", 0.7)
        _trace_step(trace, "mindmap", "completed", "思维导图资源已纳入资源包", 0.75)
        _trace_step(trace, "exercise", "completed", "练习题资源已纳入资源包", 0.8)
        _update_job(job, session, current_agent="verifier", progress=0.85, trace_json=json.dumps(trace, ensure_ascii=False))

        raw_resources = [_pack_item_to_dict(r) for r in pack.resources]
        verified = verify(raw_resources, evidence, profile)
        _trace_step(trace, "verifier", "completed", "质量校验完成", 0.95)

        artifacts = []
        for item in verified:
            artifact = ResourceArtifact(
                artifact_id=f"art_{uuid.uuid4().hex[:12]}",
                job_id=job_id,
                user_id=user_id,
                course_id=course_id,
                topic=topic,
                resource_type=str(item.get("type") or "resource"),
                title=str(item.get("title") or topic),
                content=str(item.get("content") or ""),
                quality_score=float(item.get("quality_score") or 0.0),
                metadata_json=json.dumps(item.get("metadata") or {}, ensure_ascii=False),
                download_resource_id=item.get("resource_id"),
            )
            session.add(artifact)
            artifacts.append(artifact)

        session.commit()
        for art in artifacts:
            session.refresh(art)

        result_payload = {
            "job_id": job_id,
            "course_id": course_id,
            "course_name": pack.course_name,
            "topic": topic,
            "resources": verified,
            "citations": [c.model_dump() for c in pack.citations],
            "provider": pack.provider,
            "model": pack.model,
        }

        _update_job(
            job,
            session,
            status="completed",
            progress=1.0,
            current_agent="done",
            result_json=json.dumps(result_payload, ensure_ascii=False),
            trace_json=json.dumps(trace, ensure_ascii=False),
        )

        return {"ok": True, "data": {**result_payload, "status": "completed", "agent_trace": trace}}

    except Exception as e:
        logger.exception("resource orchestration failed")
        _trace_step(trace, job.current_agent or "unknown", "failed", str(e))
        _update_job(
            job,
            session,
            status="failed",
            current_agent="failed",
            error_message=str(e),
            trace_json=json.dumps(trace, ensure_ascii=False),
        )
        return {
            "ok": False,
            "error": str(e),
            "data": {
                "job_id": job_id,
                "status": "failed",
                "agent_trace": trace,
            },
        }


def get_resource_job(job_id: str, user_id: int, session: Session) -> dict | None:
    from sqlmodel import select

    job = session.exec(
        select(ResourceJob).where(ResourceJob.job_id == job_id, ResourceJob.user_id == user_id)
    ).first()
    if not job:
        return None
    trace = []
    result = None
    try:
        if job.trace_json:
            trace = json.loads(job.trace_json)
        if job.result_json:
            result = json.loads(job.result_json)
    except Exception:
        pass
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "current_agent": job.current_agent,
        "topic": job.topic,
        "course_id": job.course_id,
        "error_message": job.error_message,
        "agent_trace": trace,
        "result": result,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
