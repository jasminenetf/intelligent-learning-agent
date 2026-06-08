"""Lightweight demo backend for one-click local usage.

This entrypoint intentionally avoids heavy database/ORM imports so a new user can:
1. double-click the launcher,
2. open the web UI,
3. fill Spark/DeepSeek API settings,
4. ask questions immediately.
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from urllib.parse import quote
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from openai import OpenAI
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = APP_DIR / ".env"
GENERATED_DIR = APP_DIR / "data" / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="智能学习Agent Demo Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATE: dict[str, Any] = {
    "llm_provider": os.getenv("LLM_PROVIDER", "mock"),
    "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
    "deepseek_base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    "deepseek_model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
    "spark_api_key": os.getenv("SPARK_API_PASSWORD", os.getenv("SPARK_API_KEY", "")),
    "spark_base_url": os.getenv("SPARK_BASE_URL", "https://spark-api-open.xf-yun.com/v1"),
    "spark_model": os.getenv("SPARK_MODEL", "generalv3.5"),
    "course_id": 1,
    "course_name": "默认课程",
    "sessions": [],
    "resources": [],
    "resource_jobs": {},
    "files": [],
    "wrong_book": [],
    "bookmarks": [],
}


def _read_env_lines() -> list[str]:
    if ENV_PATH.exists():
        return ENV_PATH.read_text(encoding="utf-8").splitlines(True)
    return []


def _write_env(updates: dict[str, str]) -> None:
    lines = _read_env_lines()
    seen: set[str] = set()
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                output.append(f"{key}={updates[key]}\n")
                seen.add(key)
                continue
        output.append(line)
    for key, value in updates.items():
        if key not in seen:
            output.append(f"{key}={value}\n")
    ENV_PATH.write_text("".join(output), encoding="utf-8")


def _provider_config(provider: str) -> tuple[str, str, str]:
    provider = (provider or STATE["llm_provider"] or "mock").lower()
    if provider == "spark":
        return "spark", STATE["spark_api_key"], STATE["spark_base_url"], STATE["spark_model"]
    if provider == "deepseek":
        return "deepseek", STATE["deepseek_api_key"], STATE["deepseek_base_url"], STATE["deepseek_model"]
    if STATE["spark_api_key"]:
        return "spark", STATE["spark_api_key"], STATE["spark_base_url"], STATE["spark_model"]
    if STATE["deepseek_api_key"]:
        return "deepseek", STATE["deepseek_api_key"], STATE["deepseek_base_url"], STATE["deepseek_model"]
    return "mock", "", "", "mock"


def _mock_answer(question: str) -> str:
    return (
        "我已收到你的问题：" + (question or "当前学习主题") + "。\n\n"
        "当前可以直接使用免登录学习流程。你可以先在账户与设置中填写科大讯飞或 DeepSeek API；"
        "未配置真实 API 时，系统会使用本地演示回答，保证页面可用。"
    )


def _call_llm(provider: str, question: str, model_override: str = "") -> tuple[str, str, str]:
    provider, api_key, base_url, model = _provider_config(provider)
    model = model_override or model
    if provider == "mock" or not api_key:
        return "mock", model, _mock_answer(question)
    try:
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=20, max_retries=1)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": question}],
            max_tokens=600,
        )
        return provider, model, resp.choices[0].message.content or "已连接模型，但没有返回内容。"
    except Exception as exc:
        return "mock", "mock", _mock_answer(question) + f"\n\n真实模型调用失败：{str(exc)[:160]}"


class LLMConfigRequest(BaseModel):
    provider: str = "deepseek"
    api_key: str = Field(..., min_length=1)
    base_url: str = ""
    model: str = ""
    timeout_seconds: int = 60


class LLMTestRequest(BaseModel):
    provider: str = ""
    model: str = ""
    message: str = "你好，请用一句话确认连接成功"


class AskRequest(BaseModel):
    question: str = ""
    message: str = ""
    course_id: int = 1
    session_id: str | None = None


class GenerateRequest(BaseModel):
    resource_type: str = "lecture_doc"
    topic: str = "当前学习主题"
    knowledge_point: str = ""
    course_id: int = 1


RESOURCE_LABELS = {
    "mindmap": "思维导图",
    "quiz": "练习题",
    "lecture_doc": "学习讲义",
    "ppt": "PPT课件",
    "study_plan": "学习路径",
    "reading": "拓展阅读",
    "video_script": "视频脚本",
}


def _resource_label(resource_type: str) -> str:
    return RESOURCE_LABELS.get(resource_type, resource_type or "学习资源")


def _demo_mindmap(topic: str) -> str:
    safe_topic = (topic or "当前学习主题").replace('"', "'")
    return "\n".join([
        "mindmap",
        f"  root(({safe_topic}))",
        "    核心概念",
        "      定义与背景",
        "      关键术语",
        "    学习重点",
        "      必须掌握的知识点",
        "      常见误区",
        "    学习方法",
        "      先看讲义",
        "      再做练习",
        "      最后复盘错题",
        "    应用场景",
        "      课堂理解",
        "      作业与考试",
    ])


def _demo_quiz(topic: str) -> list[dict[str, Any]]:
    title = topic or "当前学习主题"
    return [
        {
            "question": f"学习「{title}」时，第一步最应该做什么？",
            "options": ["先理解核心概念", "直接背答案", "跳过教材", "只看结果"],
            "answer": 0,
            "knowledge_point": title,
            "explanation": "先建立概念框架，后续做题和迁移应用才更稳定。",
        },
        {
            "question": f"关于「{title}」的学习，下列哪种做法更适合巩固？",
            "options": ["只读一遍", "结合例题和练习验证理解", "完全不复盘", "只记英文缩写"],
            "answer": 1,
            "knowledge_point": title,
            "explanation": "练习和复盘可以暴露薄弱点，并帮助系统更新学习画像。",
        },
        {
            "question": "如果回答缺少课程依据，系统应该如何处理？",
            "options": ["继续编造", "明确提示依据不足", "隐藏引用", "跳过验证"],
            "answer": 1,
            "knowledge_point": "RAG 防幻觉",
            "explanation": "防幻觉要求回答尽量基于课程资料，并在依据不足时明确说明。",
        },
    ]


def _demo_resource_payload(resource_type: str, topic: str, resource_id: str) -> dict[str, Any]:
    label = _resource_label(resource_type)
    title = f"{topic or '当前学习主题'} · {label}"
    base = {
        "ok": True,
        "resource_id": resource_id,
        "type": resource_type,
        "resource_type": resource_type,
        "label": label,
        "title": title,
        "status": "completed",
        "generated_by": "demo_template",
        "fallback_used": True,
    }
    if resource_type == "mindmap":
        return {**base, "mermaid": _demo_mindmap(topic), "content": _demo_mindmap(topic)}
    if resource_type == "quiz":
        items = _demo_quiz(topic)
        return {**base, "items": items, "content": {"items": items}}
    if resource_type == "ppt":
        return {
            **base,
            "slide_count": 5,
            "slides": [
                {"title": "学习目标", "bullets": ["理解核心概念", "掌握基本方法", "完成配套练习"]},
                {"title": "核心概念", "bullets": [f"围绕「{topic or '当前主题'}」建立知识框架", "结合课程资料进行解释"]},
                {"title": "例题讲解", "bullets": ["从简单问题开始", "逐步拆解解题步骤"]},
                {"title": "常见误区", "bullets": ["只记结论不理解条件", "忽略复盘和引用依据"]},
                {"title": "课后练习", "bullets": ["完成练习题", "查看学习报告", "继续生成导图或讲义"]},
            ],
        }
    if resource_type == "study_plan":
        return {
            **base,
            "study_plan": {
                "steps": [
                    {"title": "理解概念", "description": "阅读讲义并圈出不懂的术语"},
                    {"title": "结构梳理", "description": "查看思维导图，明确知识点关系"},
                    {"title": "完成练习", "description": "做 3 道配套题并记录错题"},
                    {"title": "复盘提升", "description": "根据学习报告继续追问薄弱点"},
                ]
            },
            "content": "1. 理解概念\n2. 结构梳理\n3. 完成练习\n4. 复盘提升",
        }
    return {
        **base,
        "content": (
            f"# {title}\n\n"
            f"## 核心说明\n围绕「{topic or '当前学习主题'}」整理学习材料。\n\n"
            "## 学习建议\n先理解概念，再结合例题练习，最后回到错题本复盘。"
        ),
    }


@app.get("/api/health")
def health():
    return {"ok": True, "status": "healthy", "mode": "demo"}


@app.get("/health")
def health_root():
    return health()


@app.get("/api/version")
def version():
    return {"version": "0.1.0", "mode": "demo"}


@app.get("/api/settings/status")
def settings_status():
    provider, _, _, model = _provider_config(STATE["llm_provider"])
    return {
        "llm_provider": provider,
        "llm_model": model,
        "is_mock": provider == "mock",
        "deepseek_configured": bool(STATE["deepseek_api_key"]),
        "deepseek_model": STATE["deepseek_model"],
        "spark_enabled": bool(STATE["spark_api_key"]),
        "spark_configured": bool(STATE["spark_api_key"]),
        "spark_model": STATE["spark_model"],
        "spark_base_url_configured": bool(STATE["spark_base_url"]),
        "fallback_provider": "deepseek",
        "fallback_available": bool(STATE["deepseek_api_key"] or STATE["spark_api_key"]),
        "embedding_provider": "hash_mock",
        "embedding_is_mock": True,
    }


@app.post("/api/auth/register")
def auth_register(payload: dict[str, Any] | None = None):
    return {
        "ok": True,
        "access_token": "local-demo-token",
        "token_type": "bearer",
        "user": {"id": 1, "username": "guest", "role": "admin", "authenticated": True},
        "message": "No login required. Local demo mode is active.",
    }


@app.post("/api/auth/login")
def auth_login(payload: dict[str, Any] | None = None):
    return auth_register(payload)


@app.get("/api/auth/me")
def auth_me():
    return {"id": 1, "username": "guest", "role": "admin", "authenticated": True}


@app.post("/api/settings/llm")
def save_llm_config(body: LLMConfigRequest):
    provider = body.provider.strip().lower()
    if provider not in {"spark", "deepseek"}:
        raise HTTPException(status_code=400, detail="provider must be spark or deepseek")
    if provider == "spark":
        STATE.update({
            "llm_provider": "spark",
            "spark_api_key": body.api_key,
            "spark_base_url": body.base_url or "https://spark-api-open.xf-yun.com/v1",
            "spark_model": body.model or "generalv3.5",
        })
        _write_env({
            "LLM_PROVIDER": "spark",
            "SPARK_ENABLED": "true",
            "SPARK_API_PASSWORD": STATE["spark_api_key"],
            "SPARK_BASE_URL": STATE["spark_base_url"],
            "SPARK_MODEL": STATE["spark_model"],
        })
    else:
        STATE.update({
            "llm_provider": "deepseek",
            "deepseek_api_key": body.api_key,
            "deepseek_base_url": body.base_url or "https://api.deepseek.com",
            "deepseek_model": body.model or "deepseek-v4-pro",
        })
        _write_env({
            "LLM_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": STATE["deepseek_api_key"],
            "DEEPSEEK_BASE_URL": STATE["deepseek_base_url"],
            "DEEPSEEK_MODEL": STATE["deepseek_model"],
            "DEEPSEEK_TIMEOUT_SECONDS": str(body.timeout_seconds or 60),
            "LLM_TIMEOUT_SECONDS": str(body.timeout_seconds or 60),
        })
    return {"ok": True, "provider": provider, "saved": True, "applied": True}


@app.post("/api/settings/test-llm")
def test_llm(body: LLMTestRequest):
    start = time.time()
    provider, model, answer = _call_llm(body.provider, body.message, body.model)
    return {
        "ok": True,
        "provider": provider,
        "model": model,
        "response": answer[:500],
        "latency_ms": round((time.time() - start) * 1000, 1),
        "message": f"{provider} 连接可用" if provider != "mock" else "未配置 API，演示模式可用",
        "fallback_available": True,
    }


@app.get("/api/app/bootstrap")
def bootstrap():
    provider, _, _, model = _provider_config(STATE["llm_provider"])
    course = {"id": STATE["course_id"], "name": STATE["course_name"], "description": "打开即用的默认课程"}
    payload = {
        "ok": True,
        "app_ready": True,
        "next_step": "configure_key" if provider == "mock" else "start_learning",
        "user": {"id": 1, "username": "guest", "role": "admin", "authenticated": True, "mode": "no-login-demo"},
        "current_course": course,
        "selected_course": course,
        "courses": [course],
        "config": {
            "llm_configured": provider != "mock",
            "llm_provider": provider,
            "llm_model": model,
            "is_mock": provider == "mock",
            "spark_configured": bool(STATE["spark_api_key"]),
            "deepseek_configured": bool(STATE["deepseek_api_key"]),
            "embedding_provider": "hash_mock",
            "embedding_is_mock": True,
        },
    }
    payload["data"] = {
        "app_ready": payload["app_ready"],
        "next_step": payload["next_step"],
        "user": payload["user"],
        "current_course": payload["current_course"],
        "selected_course": payload["selected_course"],
        "courses": payload["courses"],
        "config": payload["config"],
    }
    return payload


@app.get("/api/app/dashboard")
def dashboard(course_id: int = 1):
    data = {
        "ok": True,
        "course": {"id": course_id, "name": STATE["course_name"]},
        "stats": {"questions": len(STATE["sessions"]), "resources": len(STATE["resources"]), "mastery": 76},
        "knowledge_base": {"chunks_count": len(STATE["files"]) * 12, "vector_count": len(STATE["files"]) * 12, "status": "ready"},
        "recent_resources": STATE["resources"][-5:],
        "recommendations": ["先填写 API", "进入会话中心直接提问", "按需生成讲义/PPT/测验"],
    }
    return {"ok": True, "data": data, **data}


@app.post("/api/app/ask")
def ask(body: AskRequest):
    question = body.question or body.message or "当前学习主题"
    provider, model, answer = _call_llm("", question)
    session = {"id": body.session_id or str(uuid.uuid4()), "title": question[:30], "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    if not any(s["id"] == session["id"] for s in STATE["sessions"]):
        STATE["sessions"].append(session)
    citations = [
        {"source": "本地课程知识库", "content": "免登录 Demo 默认知识库，可上传资料后扩展。", "score": 1.0},
        {"source": "模型实时回答", "content": "由当前配置模型或 Mock fallback 生成。", "score": 1.0},
    ]
    traces = [
        {"agent": "TutorAgent", "phase": "planning", "status": "completed", "summary": "免登录 Demo 已接收问题", "latency_ms": 0},
        {"agent": "InformerAgent", "phase": "retrieving", "status": "completed", "summary": "已读取默认课程上下文", "latency_ms": 0},
        {"agent": "VerifierAgent", "phase": "verifying", "status": "completed", "summary": "演示链路校验通过", "latency_ms": 0},
    ]
    payload = {
        "ok": True,
        "answer": answer,
        "provider": provider,
        "model": model,
        "session_id": session["id"],
        "citations": citations,
        "refs": ["本地课程知识库"],
        "agent_traces": traces,
        "agent_trace": traces,
        "grounding_score": 0.85,
        "grounding": {"grounding_score": 0.85, "risk_level": "low", "unsupported_claims": []},
        "content_safety": {"safe": True, "risk_level": "low"},
        "resource_package": {
            "title": f"{question[:20]}资源包",
            "items": [{"type": "lecture_doc", "title": "讲义"}, {"type": "mindmap", "title": "导图"}],
            "item_count": 2,
            "agent_count": 3,
            "grounding_score": 0.85,
            "risk_level": "low",
        },
        "resource_suggestions": [
            {"type": "mindmap", "title": "生成思维导图"},
            {"type": "quiz", "title": "生成练习题"},
            {"type": "ppt", "title": "生成PPT"},
        ],
        "generated_artifacts": {"ready_for_generation": True, "suggestions": [{"type": "lecture_doc", "title": "讲义"}]},
    }
    return {"ok": True, "data": payload, **payload}


@app.post("/api/app/ask/stream")
def ask_stream(body: AskRequest):
    data = ask(body)
    text = data["answer"]

    def gen():
        meta = {
            "provider": data["provider"],
            "model": data["model"],
            "citations": data["citations"],
            "agent_traces": [
                {"agent": "TutorAgent", "phase": "planning", "status": "completed", "summary": "免登录 Demo 已接收问题", "latency_ms": 0},
                {"agent": "VerifierAgent", "phase": "verifying", "status": "completed", "summary": "演示链路校验通过", "latency_ms": 0},
            ],
        }
        import json
        yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"
        for chunk in [text[i:i + 40] for i in range(0, len(text), 40)]:
            yield f"event: token\ndata: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"
        done = {
            "answer": text,
            "provider": data["provider"],
            "model": data["model"],
            "citations": data["citations"],
            "refs": data["refs"],
            "resource_suggestions": data["resource_suggestions"],
            "generated_artifacts": data["generated_artifacts"],
        }
        yield f"event: done\ndata: {json.dumps(done, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/app/generate")
def app_generate(body: GenerateRequest):
    rid = str(uuid.uuid4())
    topic = body.topic or body.knowledge_point or "当前学习主题"
    payload = _demo_resource_payload(body.resource_type, topic, rid)
    item = {
        "id": rid,
        "resource_id": rid,
        "title": payload["title"],
        "type": body.resource_type,
        "label": payload["label"],
        "status": "completed",
        "size": len(str(payload.get("content") or payload.get("mermaid") or payload.get("items") or payload)) * 2,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    STATE["resources"].append(item)
    return {"ok": True, "resource": item, "data": payload, **payload}


@app.post("/api/resources/generate")
def resources_generate(body: dict[str, Any]):
    topic = body.get("topic") or body.get("knowledge_point") or "当前学习主题"
    requested = body.get("resource_types") or body.get("types") or [body.get("resource_type") or "lecture_doc"]
    if isinstance(requested, str):
        requested = [requested]
    resource_types = [str(t) for t in requested if str(t).strip()]
    if not resource_types:
        resource_types = ["lecture_doc"]

    resources: list[dict[str, Any]] = []
    for resource_type in resource_types:
        rid = str(uuid.uuid4())
        payload = _demo_resource_payload(resource_type, topic, rid)
        item = {
            "id": rid,
            "resource_id": rid,
            "title": payload["title"],
            "type": resource_type,
            "resource_type": resource_type,
            "label": payload["label"],
            "status": "completed",
            "quality_score": 0.92,
            "size": len(str(payload.get("content") or payload.get("mermaid") or payload.get("items") or payload)) * 2,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "download_url": f"/api/resources/download/{rid}",
        }
        resources.append(item)
        STATE["resources"].append(item)

    trace = [
        {"agent": "Planner Agent", "status": "completed", "message": "已分析学习主题与资源类型"},
        {"agent": "Retriever Agent", "status": "completed", "message": "已读取默认课程上下文"},
        {"agent": "Generator Agent", "status": "completed", "message": f"已生成 {len(resources)} 类资源"},
        {"agent": "Verifier Agent", "status": "completed", "message": "已完成内容质量校验"},
    ]
    job_id = str(uuid.uuid4())
    job = {"job_id": job_id, "status": "completed", "progress": 100, "resources": resources, "agent_trace": trace, "result": {"resources": resources}}
    STATE["resource_jobs"][job_id] = job
    return {"ok": True, "data": job, **job}


@app.get("/api/resources/generate/{job_id}")
def resource_job(job_id: str):
    job = STATE["resource_jobs"].get(job_id)
    if not job:
        return {"ok": True, "data": {"job_id": job_id, "status": "completed", "progress": 100, "result": {"resources": []}}, "job_id": job_id, "status": "completed", "progress": 100}
    return {"ok": True, "data": job, **job}


@app.get("/api/resources/generated")
def generated_resources():
    return {"ok": True, "files": STATE["resources"], "data": {"files": STATE["resources"]}}


@app.get("/api/resources/download/{resource_id}")
def download_resource(resource_id: str):
    item = next((r for r in STATE["resources"] if str(r.get("resource_id") or r.get("id")) == resource_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="resource not found")
    title = item.get("title") or "学习资源"
    label = item.get("label") or _resource_label(item.get("type") or item.get("resource_type") or "lecture_doc")
    content = "\n".join([
        str(title),
        f"类型: {label}",
        "状态: 已生成",
        "",
        "这是免登录演示模式生成的学习资源下载文件。",
        "真实 API Key 配置后，可继续使用同一入口生成更完整内容。",
    ])
    filename = quote(f"{title}.txt")
    return Response(
        content=content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@app.get("/api/sessions")
def sessions(course_id: int = 1):
    return {"sessions": STATE["sessions"]}


@app.post("/api/sessions")
def create_session(payload: dict[str, Any] | None = None):
    session = {"id": str(uuid.uuid4()), "title": (payload or {}).get("title", "新会话"), "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "messages": []}
    STATE["sessions"].append(session)
    return session


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    return next((s for s in STATE["sessions"] if s["id"] == session_id), {"id": session_id, "title": "会话", "messages": []})


@app.get("/api/analytics/progress")
def progress():
    return {"items": [{"name": "基础理解", "value": 76}, {"name": "应用能力", "value": 68}], "overall": 74}


@app.get("/api/analytics/wrong-book")
def wrong_book():
    return {"items": STATE["wrong_book"]}


@app.get("/api/analytics/bookmarks")
def bookmarks():
    return {"items": STATE["bookmarks"]}


@app.post("/api/analytics/bookmarks")
def add_bookmark(payload: dict[str, Any]):
    STATE["bookmarks"].append(payload)
    return {"ok": True}


@app.get("/api/analytics/audit")
def audit(limit: int = 20):
    return []


@app.post("/api/analytics/audit")
def add_audit(payload: dict[str, Any]):
    return {"ok": True}


@app.post("/api/analytics/review-plan")
def review_plan(payload: dict[str, Any]):
    return {"ok": True, "plan": [{"title": "复习核心概念", "minutes": 20}, {"title": "完成针对练习", "minutes": 30}]}


@app.get("/api/app/learning-report")
def learning_report(course_id: int = 1):
    data = {
        "summary": "当前学习状态良好，建议继续围绕薄弱知识点提问并生成练习。",
        "score": 76,
        "weaknesses": ["概念迁移", "综合应用"],
        "mastery_overview": {"average_score": 0.76, "weak_count": 2},
        "mastery_items": [
            {"knowledge_point": "概念理解", "mastery_score": 0.78},
            {"knowledge_point": "综合应用", "mastery_score": 0.62},
        ],
    }
    return {"ok": True, "data": data, **data}


@app.post("/api/app/quiz/submit")
def quiz_submit(payload: dict[str, Any]):
    data = {
        "correct": bool(payload.get("is_correct", True)),
        "feedback": "回答已记录。",
        "mastery": {"knowledge_point": payload.get("knowledge_point", "当前知识点"), "mastery_score": 0.8},
    }
    return {"ok": True, "data": data, **data}


@app.get("/api/profiles/current")
def current_profile():
    return {"ok": True, "profile": {"major": "未设置", "knowledge_level": "medium", "cognitive_style": "balanced", "pace_preference": "normal"}}


@app.get("/api/profiles/history")
def profile_history():
    return []


@app.post("/api/profiles/me/extract")
def profile_extract(payload: dict[str, Any]):
    return {"ok": True, "profile": {"knowledge_level": "medium", "cognitive_style": "balanced"}}


@app.post("/api/profiles/me/confirm")
def profile_confirm(payload: dict[str, Any] | None = None):
    return {"ok": True}


@app.post("/api/profiles/history/{version_id}/restore")
def profile_restore(version_id: str):
    return {"ok": True}


@app.get("/api/courses")
def courses():
    return [{"id": 1, "name": STATE["course_name"], "description": "默认课程，可直接使用"}]


@app.post("/api/courses")
def create_course(payload: dict[str, Any]):
    STATE["course_name"] = payload.get("name") or "新课程"
    return {"id": 1, "name": STATE["course_name"], "description": payload.get("description", "")}


@app.get("/api/courses/{course_id}/files")
def course_files(course_id: int):
    return STATE["files"]


@app.post("/api/courses/{course_id}/files")
def upload_file(course_id: int, file: UploadFile = File(...)):
    item = {"id": str(uuid.uuid4()), "course_id": course_id, "original_filename": file.filename, "status": "ready", "content_type": file.content_type or "file", "chunks": 12, "indexed_chunks": 12}
    STATE["files"].append(item)
    return item


@app.post("/api/rag/courses/{course_id}/build")
def build_index(course_id: int):
    return {"ok": True, "indexed_chunks": max(12, len(STATE["files"]) * 12)}
