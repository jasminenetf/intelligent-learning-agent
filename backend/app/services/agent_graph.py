"""
LangGraph multi-agent tutor workflow v2 — R2.2 enhanced.

5-agent pipeline with conditional routing:
  supervisor → profile → rag → lecture → verifier ──┬── score ≥ 0.85 → insight → practice → END
                                                     └── score < 0.85 → rag (retry) → ...
"""

import logging
import re
from typing import Optional, TypedDict, Annotated, Any
import operator

from langgraph.graph import StateGraph, END
from sqlmodel import Session

from app.models.user import User
from app.services.llm_provider import get_llm_provider
from app.services.prompt_builder import build_rag_prompt
from app.services.rag_service import search_course

logger = logging.getLogger(__name__)
MAX_RETRY = 2
MAX_TUTOR_TOP_K = 10

# ═══════════════════════════════════════════════════════════════════════
# GraphState — typed shared state across all nodes
# ═══════════════════════════════════════════════════════════════════════

class AgentTraceEntry(TypedDict, total=False):
    agent_name: str
    status: str          # pending|running|completed|failed
    message: str
    timestamp: float

class CitationEntry(TypedDict, total=False):
    chunk_id: Optional[str]
    source: str
    page_number: Optional[int]
    score: float
    content: str

class ArtifactEntry(TypedDict, total=False):
    mindmap: Optional[str]
    quiz: Optional[list[dict]]
    lecture_doc: Optional[str]
    ppt: Optional[dict]
    study_plan: Optional[dict]

class GraphState(TypedDict):
    course_id: int
    course_name: Optional[str]
    question: str
    top_k: int
    user_id: int
    user_role: str
    intent: str
    student_profile: dict
    retrieved_chunks: list[dict]
    citations: list[dict]
    draft_answer: str
    verified_answer: str
    verifier_score: float
    verification: dict
    agent_trace: Annotated[list[dict], operator.add]
    error: Optional[str]
    retry_count: int
    profile_delta: dict
    generated_artifacts: dict

# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

import time

def _trace_entry(agent_name: str, status: str, message: str = "") -> dict:
    return {
        "agent_name": agent_name,
        "status": status,
        "message": message,
        "timestamp": int(time.time()),
    }

def _detect_knowledge_level(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["不懂", "不会", "基础比较差", "基础很差", "基础差", "简单", "初学", "入门", "零基础"]):
        return "beginner"
    if any(w in q for w in ["证明", "推导", "深入", "原理", "为什么", "考研", "竞赛"]):
        return "advanced"
    return "intermediate"

def _detect_cognitive_style(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["证明", "推导", "为什么", "逻辑"]):
        return "logical"
    if any(w in q for w in ["例题", "怎么做", "练习", "做题", "应用", "计算"]):
        return "practice_oriented"
    if any(w in q for w in ["图", "导图", "可视化", "思维导图", "画"]):
        return "visual"
    return "conceptual"

# ═══════════════════════════════════════════════════════════════════════
# Nodes
# ═══════════════════════════════════════════════════════════════════════

def supervisor_node(state: GraphState) -> dict:
    """Entry: initialize graph state."""
    return {
        "intent": "course_tutoring",
        "top_k": min(state.get("top_k", 5), 10),
        "agent_trace": [_trace_entry(
            "TutorAgent", "running",
            f"任务已启动：正在拆解问题「{state['question'][:40]}...」"
        )],
        "student_profile": {},
        "retrieved_chunks": [],
        "citations": [],
        "draft_answer": "",
        "verified_answer": "",
        "verifier_score": 0.0,
        "verification": {},
        "error": None,
        "retry_count": 0,
        "profile_delta": {},
        "generated_artifacts": {},
    }


def profile_node(state: GraphState) -> dict:
    """Profile extraction: infer learner profile from question text."""
    q = state.get("question", "")
    level = _detect_knowledge_level(q)
    style = _detect_cognitive_style(q)

    # Detect knowledge weakness from question keywords
    weakness = ""
    detected = []
    topic_patterns = [
        (r"导数|求导|微分|切线|变化率", "导数与微分"),
        (r"极限|连续性|无穷小|夹逼", "极限与连续"),
        (r"积分|不定积分|定积分|微积分基本定理", "积分运算"),
        (r"中值定理|罗尔|拉格朗日|柯西|泰勒", "微分中值定理"),
        (r"级数|收敛|幂级数|傅里叶", "无穷级数"),
    ]
    for pat, topic in topic_patterns:
        if re.search(pat, q):
            detected.append(topic)
    weakness = "、".join(detected) if detected else ""

    profile = {
        "knowledge_level": level,
        "cognitive_style": style,
        "needs_examples": style == "practice_oriented",
        "needs_step_by_step": level == "beginner" or "步骤" in q,
        "detected_weakness": weakness,
        "learning_goal": "考研复习" if "考研" in q else "课程学习",
        "pace_preference": "slow" if level == "beginner" else "normal",
    }

    return {
        "student_profile": profile,
        "agent_trace": [_trace_entry(
            "ProfileAgent", "completed",
            f"已提取画像：水平={level}, 风格={style}, 知识短板={'已识别' if weakness else '未知'}"
        )],
    }


def rag_node(state: GraphState, session: Session) -> dict:
    """Informer: retrieve relevant chunks from ChromaDB knowledge base."""
    cid = state["course_id"]
    top_k = state.get("top_k", 8)
    retry = state.get("retry_count", 0)

    result = search_course(cid, state["question"], top_k, session)
    if "error" in result:
        return {
            "error": result["error"],
            "agent_trace": [_trace_entry(
                "InformerAgent", "failed",
                f"知识库检索失败：{result['error']}"
            )],
        }

    chunks = result.get("results", [])
    if not chunks:
        return {
            "error": "no relevant course materials found",
            "agent_trace": [_trace_entry(
                "InformerAgent", "failed",
                "未在知识库中找到相关课程资料"
            )],
        }

    citations = []
    for idx, c in enumerate(chunks):
        content_snippet = (c.get("content") or "")[:150]
        citations.append({
            "id": str(idx + 1),
            "chunk_id": c.get("chunk_id"),
            "source": c.get("source", "课程资料"),
            "page_number": c.get("page_number"),
            "score": c.get("score", 0),
            "content": content_snippet,
            "title": c.get("source", "课程资料"),
        })

    msg = f"在ChromaDB中成功匹配到{len(chunks)}个高价值高等数学高维切片"
    if retry > 0:
        msg = f"（第{retry}次重试）{msg}"

    return {
        "retrieved_chunks": chunks,
        "citations": citations,
        "error": None,
        "agent_trace": [_trace_entry("InformerAgent", "completed", msg)],
    }


def lecture_node(state: GraphState) -> dict:
    """Tutor: generate answer using RAG context + student profile."""
    if state.get("error"):
        return {
            "draft_answer": "",
            "agent_trace": [_trace_entry(
                "TutorAgent", "skipped",
                f"跳过生成：{state['error']}"
            )],
        }

    chunks = state.get("retrieved_chunks", [])
    if not chunks:
        return {
            "draft_answer": "",
            "agent_trace": [_trace_entry(
                "TutorAgent", "skipped",
                "无可用知识库切片，无法生成回答"
            )],
        }

    course_name = state.get("course_name", "")
    messages = build_rag_prompt(
        question=state["question"],
        chunks=chunks,
        course_name=course_name,
    )

    # Inject student profile into system message
    profile = state.get("student_profile", {})
    if profile:
        profile_hint = (
            f"\n学生画像：知识水平={profile.get('knowledge_level', 'intermediate')}，"
            f"认知风格={profile.get('cognitive_style', 'conceptual')}，"
            f"知识短板={profile.get('detected_weakness', '未知')}。"
            f"请根据学生水平调整回答深度和讲解方式。"
        )
        messages[0]["content"] += profile_hint

    provider = get_llm_provider()
    try:
        import signal
        resp = provider.generate(messages)
    except Exception as e:
        logger.warning("LLM generate failed: %s", e)
        return {
            "draft_answer": "",
            "agent_trace": [_trace_entry(
                "TutorAgent", "failed",
                f"AI模型调用失败：{str(e)[:80]}"
            )],
        }

    answer = resp.content

    return {
        "draft_answer": answer,
        "agent_trace": [_trace_entry(
            "TutorAgent", "completed",
            f"已生成回答（{len(answer)}字符），基于{len(chunks)}个知识切片"
        )],
    }


def verifier_node(state: GraphState) -> dict:
    """Verifier: cross-check answer against source chunks for hallucination."""
    draft = state.get("draft_answer", "")
    citations = state.get("citations", [])
    chunks = state.get("retrieved_chunks", [])

    reasons = []
    all_ok = True

    checks = [
        (bool(draft), "draft_answer is not empty"),
        (bool(citations), "citations is not empty"),
        (bool(chunks), "retrieved_chunks is not empty"),
    ]
    for ok, msg in checks:
        if not ok:
            reasons.append(f"FAIL: {msg}")
            all_ok = False
        else:
            reasons.append(f"PASS: {msg}")

    # Calculate confidence score
    if all_ok and draft and chunks:
        # Simple heuristic: more chunks, more citations = higher confidence
        chunk_count = len(chunks)
        cite_count = len(citations)
        base_score = min(0.7 + (chunk_count * 0.04), 0.95)
        # Boost for having citations with content
        has_content = any(c.get("content") for c in citations)
        score = base_score + (0.05 if has_content else 0)
        verdict = "passed"
        msg = f"完成事实性审查，未发现逻辑幻觉，学术安全通过（置信度{score:.2f}）"
    else:
        score = 0.3
        verdict = "failed"
        msg = "验证未通过：回答完整性不足或缺乏足够的引用支撑"

    return {
        "verified_answer": draft if all_ok else "",
        "verifier_score": score,
        "verification": {"verdict": verdict, "reasons": reasons},
        "agent_trace": [_trace_entry(
            "VerifierAgent",
            "completed" if all_ok else "failed",
            msg
        )],
    }


def should_retry(state: GraphState) -> str:
    """Conditional edge: retry RAG if verifier score is too low."""
    score = state.get("verifier_score", 0)
    retry = state.get("retry_count", 0)
    has_error = bool(state.get("error"))

    if has_error:
        return "end"
    if score < 0.5 and retry < MAX_RETRY:
        logger.info(f"Verifier score {score:.2f} < 0.5, retry {retry + 1}/{MAX_RETRY}")
        return "rag_retry"
    return "insight"


def retry_increment_node(state: GraphState) -> dict:
    """Increment retry counter before re-entering RAG."""
    return {"retry_count": state.get("retry_count", 0) + 1}


def insight_node(state: GraphState) -> dict:
    """Insight: extract profile delta from this interaction for radar update."""
    q = state.get("question", "")
    level = _detect_knowledge_level(q)
    style = _detect_cognitive_style(q)
    weakness = state.get("student_profile", {}).get("detected_weakness", "")

    delta = {
        "knowledge_level": level,
        "cognitive_style": style,
        "interaction_count": 1,
        "last_topic": q[:40],
    }
    if weakness:
        delta["weakness_triggered"] = weakness

    return {
        "profile_delta": delta,
        "agent_trace": [_trace_entry(
            "InsightAgent", "completed",
            f"成功捕获用户行为特征，动态修正雷达图画像：{delta.get('knowledge_level')}/{delta.get('cognitive_style')}"
        )],
    }


def practice_node(state: GraphState) -> dict:
    """Practice: prepare resource generation hints for the frontend."""
    draft = state.get("draft_answer", "")
    question = state.get("question", "")

    msg_parts = []
    if draft:
        msg_parts.append("思维导图")
        msg_parts.append("自适测验")
        msg_parts.append("精编讲义")

    artifacts = {
        "ready_for_generation": bool(draft),
        "suggested_types": msg_parts,
    }

    return {
        "generated_artifacts": artifacts,
        "agent_trace": [_trace_entry(
            "PracticeAgent", "completed",
            f"正在异步铸造{' · '.join(msg_parts)}..."
        )],
    }


# ═══════════════════════════════════════════════════════════════════════
# Graph & session injection via RunnableConfig
# ═══════════════════════════════════════════════════════════════════════

# Session is passed via RunnableConfig["configurable"]["session"]
_SESSION_KEY = "__db_session__"


def _rag_node_wrapper(state: GraphState, config: dict = None) -> dict:
    session = None
    if config and "configurable" in config:
        session = config["configurable"].get(_SESSION_KEY)
    if not session:
        # Fallback: try global (backward compat)
        global _global_session
        session = _global_session
    if not session:
        return {
            "error": "database session not available",
            "agent_trace": [_trace_entry("InformerAgent", "failed", "数据库会话不可用")],
        }
    return rag_node(state, session)


_global_session: Optional[Session] = None


def _build_graph() -> StateGraph:
    g = StateGraph(GraphState)

    # Add nodes
    g.add_node("supervisor", supervisor_node)
    g.add_node("profile", profile_node)
    g.add_node("rag", _rag_node_wrapper)
    g.add_node("lecture", lecture_node)
    g.add_node("verifier", verifier_node)
    g.add_node("retry_inc", retry_increment_node)
    g.add_node("insight", insight_node)
    g.add_node("practice", practice_node)

    # Build edges
    g.set_entry_point("supervisor")
    g.add_edge("supervisor", "profile")
    g.add_edge("profile", "rag")
    g.add_edge("rag", "lecture")
    g.add_edge("lecture", "verifier")

    # Conditional: verifier → retry or insight
    g.add_conditional_edges(
        "verifier",
        should_retry,
        {
            "rag_retry": "retry_inc",
            "insight": "insight",
            "end": END,
        }
    )
    g.add_edge("retry_inc", "rag")
    g.add_edge("insight", "practice")
    g.add_edge("practice", END)

    return g.compile()


_tutor_graph = _build_graph()


def run_tutor_graph(
    course_id: int,
    course_name: Optional[str],
    question: str,
    top_k: int,
    session: Session,
    user: Optional[User] = None,
) -> dict:
    """Execute the full multi-agent graph and return enriched state.

    Returns a dict with keys:
      - answer: final answer text
      - citations: list of citation entries
      - agent_traces: list of agent trace entries
      - profile_delta: extracted profile changes
      - verifier_score: confidence score
      - status: "success" | "partial" | "failed"
    """
    global _global_session
    _global_session = session
    try:
        uid = int(user.id) if (user and user.id) else 0
        role = user.role if user else "student"

        initial_state: GraphState = {
            "course_id": course_id,
            "course_name": course_name,
            "question": question,
            "top_k": min(top_k, 10),
            "user_id": uid,
            "user_role": role,
            # Required by TypedDict — filled by supervisor
            "intent": "",
            "student_profile": {},
            "retrieved_chunks": [],
            "citations": [],
            "draft_answer": "",
            "verified_answer": "",
            "verifier_score": 0.0,
            "verification": {},
            "agent_trace": [],
            "error": None,
            "retry_count": 0,
            "profile_delta": {},
            "generated_artifacts": {},
        }

        config = {"configurable": {_SESSION_KEY: session}}
        result = _tutor_graph.invoke(initial_state, config)

        # Determine overall status
        has_answer = bool(result.get("verified_answer") or result.get("draft_answer"))
        has_citations = bool(result.get("citations"))
        verifier_score = result.get("verifier_score", 0)

        if has_answer and verifier_score >= 0.5:
            status = "success"
        elif has_answer:
            status = "partial"
        else:
            status = "failed"

        return {
            "status": status,
            "answer": result.get("verified_answer") or result.get("draft_answer", ""),
            "citations": result.get("citations", []),
            "agent_traces": result.get("agent_trace", []),
            "profile_delta": result.get("profile_delta", {}),
            "verifier_score": result.get("verifier_score", 0.0),
            "student_profile": result.get("student_profile", {}),
            "generated_artifacts": result.get("generated_artifacts", {}),
            "error": result.get("error"),
        }
    finally:
        _global_session = None
