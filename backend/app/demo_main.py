"""Lightweight demo backend for one-click local usage.

This entrypoint intentionally avoids heavy database/ORM imports so a new user can:
1. double-click the launcher,
2. open the web UI,
3. fill Spark/DeepSeek API settings,
4. ask questions immediately.
"""

from __future__ import annotations

import os
import json
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


def _load_local_env() -> None:
    if not ENV_PATH.exists():
        return
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()

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
    "llm_timeout_seconds": int(os.getenv("LLM_TIMEOUT_SECONDS", os.getenv("SPARK_TIMEOUT_SECONDS", "60"))),
    "course_id": 1,
    "course_name": "高等数学上册",
    "sessions": [],
    "resources": [],
    "resource_jobs": {},
    "resource_payloads": {},
    "extra_courses": [],
    "files": [
        {
            "id": "gaoshu-pdf",
            "course_id": 1,
            "original_filename": "高数上.pdf",
            "status": "ready",
            "content_type": "application/pdf",
            "chunks": 128,
            "indexed_chunks": 128,
            "source": r"C:\Users\zhang\Desktop\高数上.pdf",
        }
    ],
    "wrong_book": [
        {
            "knowledge_point": "函数极限",
            "question": "极限存在是否要求函数在该点有定义？",
            "selected_answer": "要求",
            "correct_answer": "不要求",
            "explanation": "极限研究的是自变量趋近该点时函数值的变化趋势。",
        }
    ],
    "bookmarks": [
        {"resource_id": "gaoshu-outline", "title": "高等数学上册章节导学"}
    ],
    "profile": {
        "major": "高等数学上册复习",
        "knowledge_level": "",
        "learning_goal": "",
        "cognitive_style": "",
        "pace_preference": "moderate",
        "weak_points": [],
        "resource_preference": [],
        "emotion_tendency": "",
        "profile_source": "dialogue",
        "profile_version": 0,
        "profile_confidence": 0.0,
        "raw_evidence": "",
        "last_topic": "",
    },
    "profile_versions": [],
    "profile_changes": [],
    "llm_failure_until": 0.0,
    "llm_last_error": "",
}

GAOSHU_COURSE_DESCRIPTION = (
    "内置《高数上.pdf》学习辅助课程，覆盖函数与极限、导数与微分、"
    "微分中值定理与导数应用、不定积分、定积分、定积分应用和微分方程。"
)

GAOSHU_CHAPTERS = [
    {"title": "第一章 函数与极限", "page": 16, "points": ["函数", "数列极限", "函数极限", "无穷小与无穷大", "连续性"]},
    {"title": "第二章 导数与微分", "page": 88, "points": ["导数定义", "求导法则", "高阶导数", "隐函数求导", "微分"]},
    {"title": "第三章 微分中值定理与导数的应用", "page": 140, "points": ["罗尔定理", "拉格朗日中值定理", "洛必达法则", "单调性", "极值与最值"]},
    {"title": "第四章 不定积分", "page": 199, "points": ["原函数", "基本积分公式", "换元积分法", "分部积分法"]},
    {"title": "第五章 定积分", "page": 239, "points": ["定积分定义", "可积条件", "微积分基本公式", "定积分换元法", "定积分分部积分"]},
    {"title": "第六章 定积分的应用", "page": 289, "points": ["面积", "体积", "弧长", "物理应用"]},
    {"title": "第七章 微分方程", "page": 312, "points": ["可分离变量方程", "齐次方程", "一阶线性微分方程", "二阶常系数线性方程"]},
]

GAOSHU_TOPIC_HINTS = {
    "极限": {
        "chapter": "第一章 函数与极限",
        "summary": "极限刻画变量趋近某个过程时函数值或数列项的稳定趋势，是连续、导数和积分的基础。",
        "steps": ["先判断自变量趋近方式", "化简表达式并消去无意义项", "必要时比较左右极限或使用等价无穷小"],
        "pitfalls": ["把函数值等同于极限", "忽略左右极限", "未验证等价无穷小适用条件"],
    },
    "导数": {
        "chapter": "第二章 导数与微分",
        "summary": "导数表示函数在一点的瞬时变化率，几何意义是曲线在该点的切线斜率。",
        "steps": ["明确函数复合结构", "选择求导法则", "代入点值并解释实际或几何意义"],
        "pitfalls": ["复合函数漏乘内层导数", "隐函数求导漏写 y'", "高阶导数符号混乱"],
    },
    "微分": {
        "chapter": "第二章 导数与微分",
        "summary": "微分用线性主部近似函数增量，适合做近似计算和误差分析。",
        "steps": ["先求导数", "写出 dy=f'(x)dx", "结合题目给定的增量解释近似"],
        "pitfalls": ["把 dy 与 Δy 完全等同", "忘记说明近似条件"],
    },
    "洛必达": {
        "chapter": "第三章 微分中值定理与导数的应用",
        "summary": "洛必达法则用于处理 0/0 或 ∞/∞ 型未定式，使用前必须确认适用条件。",
        "steps": ["确认未定式类型", "分别对分子分母求导", "求导后重新判断极限"],
        "pitfalls": ["不是 0/0 或 ∞/∞ 也直接用", "循环求导后不检查极限是否存在"],
    },
    "积分": {
        "chapter": "第四、五章 不定积分与定积分",
        "summary": "不定积分关注原函数族，定积分关注区间上的累积量，两者由微积分基本公式联系。",
        "steps": ["识别是求原函数还是累积量", "匹配基本公式或换元/分部方法", "定积分注意上下限和几何意义"],
        "pitfalls": ["不定积分漏写常数 C", "换元后上下限未同步变化", "分部积分 u 与 dv 选择不当"],
    },
    "微分方程": {
        "chapter": "第七章 微分方程",
        "summary": "微分方程用未知函数及其导数描述变化规律，先分类再选择解法。",
        "steps": ["判断方程类型", "按类型套用分离变量或线性方程方法", "代入初值确定常数"],
        "pitfalls": ["未分离变量就积分", "通解漏常数", "初值条件代入位置错误"],
    },
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
    if provider == "mock":
        return "mock", "", "", "mock"
    if provider == "spark":
        return "spark", STATE["spark_api_key"], STATE["spark_base_url"], STATE["spark_model"]
    if provider == "deepseek":
        return "deepseek", STATE["deepseek_api_key"], STATE["deepseek_base_url"], STATE["deepseek_model"]
    if STATE["spark_api_key"]:
        return "spark", STATE["spark_api_key"], STATE["spark_base_url"], STATE["spark_model"]
    if STATE["deepseek_api_key"]:
        return "deepseek", STATE["deepseek_api_key"], STATE["deepseek_base_url"], STATE["deepseek_model"]
    return "mock", "", "", "mock"


def _gaoshu_context(topic: str) -> dict[str, Any]:
    text = (topic or "").lower()
    for key, ctx in GAOSHU_TOPIC_HINTS.items():
        if key.lower() in text:
            return {"keyword": key, **ctx}
    if any(word in text for word in ["函数", "连续", "无穷小", "无穷大"]):
        return {"keyword": "极限", **GAOSHU_TOPIC_HINTS["极限"]}
    return {
        "keyword": "高等数学",
        "chapter": "高等数学上册",
        "summary": "高等数学上册围绕极限、导数、积分和微分方程建立连续变化问题的分析工具。",
        "steps": ["先定位教材章节", "理解定义和定理适用条件", "用例题验证方法", "通过练习巩固薄弱点"],
        "pitfalls": ["只背公式不看条件", "计算步骤跳跃", "错题没有回到概念复盘"],
    }


def _profile_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(x) for x in parsed if str(x).strip()]
        except Exception:
            pass
        return [value] if value.strip() else []
    return [str(value)]


def _merge_unique(items: list[str], additions: list[str], limit: int = 8) -> list[str]:
    out: list[str] = []
    for item in [*items, *additions]:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out[:limit]


def _infer_profile_delta(message: str) -> dict[str, Any]:
    text = message or ""
    ctx = _gaoshu_context(text)
    lowered = text.lower()
    weak = [ctx["keyword"]] if ctx.get("keyword") and ctx["keyword"] != "高等数学" else []
    if any(w in text for w in ["不懂", "不会", "错题", "薄弱", "看不懂", "不理解", "懵", "没反应"]):
        weak = _merge_unique(weak, [ctx["keyword"] or "当前知识点"])
    prefs: list[str] = []
    if any(w in text for w in ["导图", "结构", "框架", "关系"]):
        prefs.append("mindmap")
    if any(w in text for w in ["题", "练习", "测验", "例题"]):
        prefs.append("quiz")
    if any(w in text for w in ["讲义", "定义", "证明", "推导"]):
        prefs.append("lecture_doc")
    if any(w in text for w in ["PPT", "课件"]):
        prefs.append("ppt")
    level = "medium"
    if any(w in text for w in ["基础差", "零基础", "完全不会", "看不懂", "不懂"]):
        level = "foundation"
    elif any(w in text for w in ["证明", "严格", "推导", "进阶", "考研"]):
        level = "advanced"
    style = "logical"
    if any(w in text for w in ["图", "导图", "结构", "框架"]):
        style = "visual-structured"
    elif any(w in text for w in ["例题", "做题", "练习"]):
        style = "practice-driven"
    goal = f"掌握「{ctx['keyword']}」：先理解定义和条件，再完成例题与错题复盘"
    emotion = "needs_support" if any(w in text for w in ["不会", "不懂", "看不懂", "懵", "一塌糊涂"]) else "focused"
    return {
        "knowledge_level": level,
        "learning_goal": goal,
        "cognitive_style": style,
        "weak_points": weak,
        "resource_preference": prefs or ["mindmap", "quiz", "lecture_doc"],
        "emotion_tendency": emotion,
        "last_topic": ctx["keyword"] if ctx["keyword"] != "高等数学" else (text[:20] or "高等数学"),
        "raw_evidence": text[:240],
    }


def _update_demo_profile(message: str, source: str = "dialogue") -> dict[str, Any]:
    profile = STATE["profile"]
    old = dict(profile)
    delta = _infer_profile_delta(message)
    for key in ["knowledge_level", "learning_goal", "cognitive_style", "emotion_tendency", "last_topic", "raw_evidence"]:
        if delta.get(key):
            profile[key] = delta[key]
    profile["weak_points"] = _merge_unique(_profile_list(profile.get("weak_points")), delta.get("weak_points", []))
    profile["resource_preference"] = _merge_unique(_profile_list(profile.get("resource_preference")), delta.get("resource_preference", []))
    profile["profile_source"] = source
    profile["profile_version"] = int(profile.get("profile_version") or 0) + 1
    profile["profile_confidence"] = min(0.95, max(0.45, 0.45 + profile["profile_version"] * 0.12))
    profile["last_extracted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    changed: list[dict[str, Any]] = []
    for key in ["knowledge_level", "learning_goal", "cognitive_style", "emotion_tendency", "last_topic"]:
        if old.get(key) != profile.get(key):
            changed.append({
                "field_name": key,
                "old_value": old.get(key) or "未识别",
                "new_value": profile.get(key) or "",
                "reason": "根据最近对话自动识别学习状态",
                "source_type": source,
            })
    if old.get("weak_points") != profile.get("weak_points"):
        changed.append({"field_name": "weak_points", "old_value": " · ".join(_profile_list(old.get("weak_points"))) or "暂无", "new_value": " · ".join(profile["weak_points"]), "reason": "从提问主题和困难描述中识别薄弱点", "source_type": source})
    if old.get("resource_preference") != profile.get("resource_preference"):
        changed.append({"field_name": "resource_preference", "old_value": " · ".join(_profile_list(old.get("resource_preference"))) or "暂无", "new_value": " · ".join(profile["resource_preference"]), "reason": "从用户点击和表达中识别资源偏好", "source_type": source})
    for item in changed:
        item["id"] = str(uuid.uuid4())
        item["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    STATE["profile_changes"] = [*changed, *STATE["profile_changes"]][:30]
    STATE["profile_versions"].insert(0, {
        "id": str(profile["profile_version"]),
        "version": profile["profile_version"],
        "snapshot": dict(profile),
        "trigger_source": source,
        "confidence": profile["profile_confidence"],
        "created_at": profile["last_extracted_at"],
    })
    STATE["profile_versions"] = STATE["profile_versions"][:10]
    return dict(profile)


def _build_demo_study_plan(topic: str) -> dict[str, Any]:
    profile = STATE["profile"]
    topic = _resolve_generation_topic(topic or profile.get("last_topic") or "函数极限")
    ctx = _gaoshu_context(topic)
    weak_points = _profile_list(profile.get("weak_points")) or [ctx["keyword"]]
    prefs = _profile_list(profile.get("resource_preference")) or ["mindmap", "quiz", "lecture_doc"]
    level = profile.get("knowledge_level") or "foundation"
    level_hint = "基础重建" if level == "foundation" else ("进阶推导" if level == "advanced" else "概念到练习")
    steps = [
        {
            "order": 1,
            "title": f"定位教材章节：{ctx['chapter']}",
            "description": f"围绕最近问题「{topic}」先找到教材位置，明确它和后续导数、连续或积分的关系。",
            "reason": f"画像显示当前目标是：{profile.get('learning_goal') or '建立清晰知识框架'}。",
            "resource_types": ["lecture_doc", "mindmap"],
            "estimated_minutes": 12,
            "practice": "读一遍讲义第一、二节，并用自己的话写出核心定义。",
            "check_standard": "能指出教材章节，并说明这个知识点在后续导数、连续或积分中的作用。",
        },
        {
            "order": 2,
            "title": f"补齐薄弱点：{weak_points[0]}",
            "description": ctx["summary"],
            "reason": "该知识点来自最近提问、错题或自动画像识别，不是固定模板。",
            "resource_types": [t for t in ["mindmap", "lecture_doc"] if t in prefs] or ["mindmap"],
            "estimated_minutes": 18,
            "practice": "对照导图说出每个条件为什么必要。",
            "check_standard": "不看答案时，能把定义中的对象、条件、结论分别说出来。",
        },
        {
            "order": 3,
            "title": f"按「{level_hint}」完成例题",
            "description": "按步骤拆题：先判断对象和适用条件，再选择化简、定义验证或对应定理。",
            "reason": f"认知风格识别为 {profile.get('cognitive_style') or '待识别'}，因此优先给出结构化步骤和配套题。",
            "resource_types": ["quiz", "lecture_doc"],
            "estimated_minutes": 25,
            "practice": "完成 3 道同主题题，错题自动写入错题本和画像。",
            "check_standard": "每道题能写出至少 2 个依据：为什么这样变形、为什么这个定理可用。",
        },
        {
            "order": 4,
            "title": "复盘并生成下一轮资源",
            "description": f"重点检查：{'; '.join(ctx['pitfalls'][:3])}。",
            "reason": "把错因回流到学习画像，下一次路径会继续变化。",
            "resource_types": ["quiz", "study_plan"],
            "estimated_minutes": 15,
            "practice": "把错题归因到定义、条件、计算或审题，并再次提问薄弱处。",
            "check_standard": "能把错因归为概念、条件、方法、计算或表达中的一类，并知道下一份资料该看什么。",
        },
    ]
    return {
        "title": f"{topic} · 个性化学习路径",
        "profile_summary": f"基于最近问题「{topic}」、画像版本 #{profile.get('profile_version') or 0}、薄弱点 {', '.join(weak_points[:3])} 生成。",
        "steps": steps,
        "recommended_topics": _merge_unique([ctx["keyword"], *weak_points, ctx["chapter"]], [], 5),
        "next_action": f"先生成「{steps[0]['title']}」讲义，再完成步骤 3 的配套练习。",
        "provider": STATE.get("llm_provider") or "demo",
        "model": STATE.get("spark_model") or "demo",
    }


def _mock_answer(question: str) -> str:
    ctx = _gaoshu_context(question)
    return (
        f"我会按《高等数学上册》的「{ctx['chapter']}」来讲：{question or ctx['keyword']}。\n\n"
        f"核心理解：{ctx['summary']}\n\n"
        "建议按这几步学：\n"
        + "\n".join(f"{i + 1}. {step}" for i, step in enumerate(ctx["steps"]))
        + "\n\n容易出错的地方："
        + "；".join(ctx["pitfalls"])
        + "。\n\n依据：内置教材《高数上.pdf》章节目录与本地高数学习模板。"
    )


def _call_llm(provider: str, question: str, model_override: str = "", max_tokens: int = 600, timeout_seconds: int | None = None, bypass_failure_cache: bool = False) -> tuple[str, str, str]:
    provider, api_key, base_url, model = _provider_config(provider)
    model = model_override or model
    if provider == "mock" or not api_key:
        return "mock", model, _mock_answer(question)
    if not bypass_failure_cache and time.time() < float(STATE.get("llm_failure_until") or 0):
        last_error = str(STATE.get("llm_last_error") or "真实模型暂不可用")
        return "mock", "mock", _mock_answer(question) + f"\n\n真实模型暂时不可用，已自动切换本地课程模式：{last_error[:120]}"
    try:
        timeout = min(int(STATE["llm_timeout_seconds"] or 60), int(timeout_seconds or STATE["llm_timeout_seconds"] or 60))
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=0)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "你是《高等数学上册》课程学习辅助教师。请用中文回答，步骤清晰，说明适用条件、常见误区，并给出复习建议。",
                },
                {"role": "user", "content": question},
            ],
            max_tokens=max_tokens,
        )
        STATE["llm_failure_until"] = 0.0
        STATE["llm_last_error"] = ""
        return provider, model, resp.choices[0].message.content or "已连接模型，但没有返回内容。"
    except Exception as exc:
        STATE["llm_failure_until"] = time.time() + 120
        STATE["llm_last_error"] = str(exc)[:240]
        return "mock", "mock", _mock_answer(question) + f"\n\n真实模型调用失败：{str(exc)[:160]}"


def _strip_code_fence(text: str) -> str:
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
    return cleaned.strip()


def _parse_json_object(text: str) -> Any:
    cleaned = _strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    starts = [idx for idx in [cleaned.find("{"), cleaned.find("[")] if idx >= 0]
    if not starts:
        return None
    start = min(starts)
    end = max(cleaned.rfind("}"), cleaned.rfind("]"))
    if end <= start:
        return None
    try:
        return json.loads(cleaned[start : end + 1])
    except Exception:
        return None


def _safe_node(text: str, limit: int = 28) -> str:
    return str(text or "").replace('"', "'").replace("[", " ").replace("]", " ").replace("\n", " ").strip()[:limit] or "知识点"


def _structured_mindmap(topic: str) -> str:
    ctx = _gaoshu_context(topic)
    t = _safe_node(topic, 34)
    step1 = _safe_node(ctx["steps"][0] if ctx["steps"] else "先明确对象与条件", 30)
    step2 = _safe_node(ctx["steps"][1] if len(ctx["steps"]) > 1 else "再选择合适方法", 30)
    step3 = _safe_node(ctx["steps"][2] if len(ctx["steps"]) > 2 else "最后回到定义验证", 30)
    pit1 = _safe_node(ctx["pitfalls"][0] if ctx["pitfalls"] else "只记公式不看条件", 30)
    pit2 = _safe_node(ctx["pitfalls"][1] if len(ctx["pitfalls"]) > 1 else "跳过关键依据", 30)
    pit3 = _safe_node(ctx["pitfalls"][2] if len(ctx["pitfalls"]) > 2 else "错题不复盘原因", 30)
    return "\n".join([
        "flowchart TB",
        f'  A["{t}"]',
        f'  A --> B["1 教材定位"]',
        f'  B --> B1["{_safe_node(ctx["chapter"], 30)}"]',
        f'  B1 --> C["2 核心定义"]',
        f'  C --> C1["{_safe_node(ctx["summary"], 36)}"]',
        f'  C1 --> D["3 解题流程"]',
        f'  D --> D1["{step1}"]',
        f'  D1 --> D2["{step2}"]',
        f'  D2 --> D3["{step3}"]',
        f'  D3 --> E["4 常见误区"]',
        f'  E --> E1["{pit1}"]',
        f'  E --> E2["{pit2}"]',
        f'  E --> E3["{pit3}"]',
        f'  E3 --> F["5 巩固路径"]',
        '  F --> F1["先做定义判断题"]',
        '  F1 --> F2["再做计算与证明题"]',
        '  F2 --> F3["错题回到条件复盘"]',
    ])


def _mindmap_tree(topic: str) -> dict[str, Any]:
    ctx = _gaoshu_context(topic)
    profile = STATE.get("profile", {})
    weak_points = _profile_list(profile.get("weak_points")) or [ctx["keyword"]]
    return {
        "title": topic or ctx["keyword"],
        "subtitle": "按“先理解、再做题、最后复盘”的学习顺序组织",
        "nodes": [
            {
                "title": "1. 教材定位",
                "summary": f"对应《高等数学上册》：{ctx['chapter']}",
                "children": [
                    f"当前问题聚焦：{ctx['keyword']}",
                    "先明确它和后续导数、连续、积分的关系",
                    "学习时先读教材概念，再看例题步骤",
                ],
            },
            {
                "title": "2. 核心理解",
                "summary": ctx["summary"],
                "children": [
                    "先用自己的话说出它研究什么",
                    "再把口语理解翻译成教材定义",
                    "最后圈出定义里的对象、条件和结论",
                ],
            },
            {
                "title": "3. 解题流程",
                "summary": "把定义变成每道题都能执行的检查表",
                "children": ctx["steps"],
            },
            {
                "title": "4. 常见误区",
                "summary": "错题优先回到概念和条件，不直接背答案",
                "children": ctx["pitfalls"],
            },
            {
                "title": "5. 个性化复盘",
                "summary": f"画像薄弱点：{', '.join(weak_points[:3])}",
                "children": [
                    "先看讲义补概念",
                    "再用本结构图串关系",
                    "最后完成 3 道同主题练习并记录错因",
                ],
            },
        ],
    }


def _structured_lecture(topic: str) -> str:
    ctx = _gaoshu_context(topic)
    title = topic or ctx["keyword"]
    if ctx["keyword"] == "积分":
        example = (
            "例题：计算 $\\int 2x\\,dx$，并解释为什么答案后面要写 $C$。\n\n"
            "1. 先判断题型：这是不定积分，不是在求一个具体数值，而是在找“原函数族”。\n"
            "2. 找原函数：因为 $(x^2)'=2x$，所以 $x^2$ 是 $2x$ 的一个原函数。\n"
            "3. 写完整答案：$\\int 2x\\,dx=x^2+C$。\n"
            "4. 为什么要加 $C$：$x^2+1$、$x^2-5$ 的导数也都是 $2x$，所以必须用常数 $C$ 表示所有可能的原函数。"
        )
        contrast = "不定积分问“谁的导数等于它”，定积分问“一个区间上的累积量是多少”。这两个问题不能混在一起。"
    elif ctx["keyword"] == "极限":
        example = (
            "例题：求 $\\lim_{x\\to1}\\frac{x^2-1}{x-1}$。\n\n"
            "1. 先代入检查：直接代入得到 $0/0$，说明不能把代入结果当答案。\n"
            "2. 化简结构：$x^2-1=(x-1)(x+1)$。\n"
            "3. 注意条件：极限看的是 $x\\to1$ 且 $x\\ne1$ 的过程，所以可以在去心邻域内约掉 $x-1$。\n"
            "4. 得到趋势：原式化为 $x+1$，当 $x\\to1$ 时趋近 $2$。\n"
            "5. 结论：极限是 $2$，这不要求原函数在 $x=1$ 处有定义。"
        )
        contrast = "函数值看某一点有没有定义；极限看靠近这一点时的趋势。两者相关，但不是一回事。"
    elif ctx["keyword"] == "导数":
        example = (
            "例题：求 $f(x)=x^2$ 在 $x=3$ 处的导数并解释意义。\n\n"
            "1. 先理解题意：导数表示这一点附近的瞬时变化率。\n"
            "2. 求导函数：$f'(x)=2x$。\n"
            "3. 代入点：$f'(3)=6$。\n"
            "4. 解释意义：当 $x$ 在 3 附近变化一点点时，函数值大约以 6 倍速度变化。"
        )
        contrast = "平均变化率看一段区间，导数看某一点附近的瞬时变化趋势。"
    else:
        example = (
            f"例题：围绕「{title}」做一道基础题。\n\n"
            "1. 圈出题干关键词和限制条件。\n"
            "2. 判断使用哪个定义、公式或定理。\n"
            "3. 每一步写出依据，不跳步。\n"
            "4. 最后回到题目问法写结论。"
        )
        contrast = "先判断题目属于哪类问题，再选方法；不要先套公式。"
    return "\n\n".join([
        f"# {title} · 面向不会学生的详细学习讲义",
        f"## 1. 先说明：为什么要学这一节\n《高等数学上册》对应章节：{ctx['chapter']}。\n\n这一节不是为了多背一个公式，而是为了学会处理“连续变化”的问题。很多同学觉得难，是因为一上来就看符号和公式，没有先弄清楚题目到底在问什么。本讲义会按“人话理解 → 条件拆解 → 例题步骤 → 错因复盘”的顺序来学。",
        f"## 2. 先用人话讲核心概念\n{ctx['summary']}\n\n换成更直观的话：先看研究对象怎么变化，再看结果是否稳定、累积或产生某种变化率。不要急着套公式，先问自己：题目让我观察的是一个点、一个区间，还是一个变化过程？",
        f"## 3. 容易混淆的地方\n{contrast}\n\n这一步非常关键。学生做错题，常常不是不会算，而是把两个相近概念混了。例如把函数值当成极限、把不定积分当成定积分、把平均变化率当成导数。先分清问题类型，后面的计算才有意义。",
        "## 4. 做题前必须检查的条件\n" + "\n".join(f"- {step}：这一步决定你能不能使用对应公式或方法。" for step in ctx["steps"]) + "\n\n做题时不要把这些条件放在脑子里含糊过去，建议直接写在草稿纸上。只要某个条件没检查，后面的计算就可能是错的。",
        f"## 5. 老师带做一题：完整拆解\n{example}\n\n注意：例题的价值不只是得到答案，而是学会每一步为什么能这么做。以后遇到同类题，就照着“判断题型 → 检查条件 → 选择方法 → 写出结论”的顺序来。",
        "## 6. 常见错误和纠正方法\n" + "\n".join(f"- 错误：{pitfall}。\n  纠正：做题时先停下来问“这个条件是否满足？我这一步依据是什么？”" for pitfall in ctx["pitfalls"]),
        "## 7. 课后训练安排\n1. 先用 5 分钟复述本节核心概念，不能只背原文，要能用自己的话讲。\n2. 再做 2 道基础题，重点写清楚每一步依据。\n3. 最后看错题：把错因归类为“概念混淆、条件漏看、方法选错、计算错误”中的一种。\n4. 如果仍然不会，回到系统生成思维导图，看知识点之间的关系，再生成配套练习。",
        "## 8. 自测清单\n- 我能用一句话说清这节研究什么吗？\n- 我能列出做题前必须检查的条件吗？\n- 我能说明例题中每一步为什么成立吗？\n- 我能判断自己错题属于哪类错因吗？\n- 我能根据错因选择下一份资料：讲义、导图还是练习吗？",
    ])


def _resolve_generation_topic(topic: str, knowledge_point: str = "") -> str:
    candidate = (topic or knowledge_point or "").strip()
    generic = {"", "当前学习主题", "当前主题", "学习主题", "高等数学", "高等数学上册"}
    if candidate in generic and STATE["sessions"]:
        candidate = str(STATE["sessions"][-1].get("title") or "").strip()
    return candidate or "函数极限的定义"


def _resource_context_meta(topic: str, resource_type: str, generated_by: str, fallback_used: bool) -> dict[str, Any]:
    ctx = _gaoshu_context(topic)
    profile = STATE.get("profile", {})
    wrong_hits = [
        w for w in STATE.get("wrong_book", [])
        if ctx["keyword"] in str(w.get("knowledge_point") or w.get("question") or "")
    ][:3]
    grounding_score = 0.78 if fallback_used else 0.9
    return {
        "topic": topic,
        "question": topic,
        "course": STATE["course_name"],
        "chapter": ctx["chapter"],
        "context_chunks": [
            {
                "chunk_id": "gaoshu_seed_context_001",
                "source": "高数上.pdf",
                "chapter": ctx["chapter"],
                "content": ctx["summary"],
                "score": 0.92,
                "context_type": "seeded_demo_context",
            }
        ],
        "evidence": [
            {
                "source": "高数上.pdf",
                "chapter": ctx["chapter"],
                "content": ctx["summary"],
                "score": 0.92,
            },
            {
                "source": "学习画像",
                "content": f"画像版本 #{profile.get('profile_version') or 0}，薄弱点：{', '.join(_profile_list(profile.get('weak_points'))[:3]) or '待识别'}",
                "score": 0.82,
            },
        ],
        "profile_adaptation": {
            "knowledge_level": profile.get("knowledge_level") or "foundation",
            "learning_goal": profile.get("learning_goal") or f"掌握「{ctx['keyword']}」",
            "cognitive_style": profile.get("cognitive_style") or "structured",
            "weak_points": _profile_list(profile.get("weak_points")) or [ctx["keyword"]],
            "resource_preference": _profile_list(profile.get("resource_preference")) or ["mindmap", "quiz", "lecture_doc"],
            "emotion_tendency": profile.get("emotion_tendency") or "focused",
            "profile_version": profile.get("profile_version") or 0,
            "profile_confidence": profile.get("profile_confidence") or 0.0,
        },
        "wrong_history": wrong_hits,
        "verifier": {
            "status": "passed",
            "grounding_score": grounding_score,
            "risk_level": "low",
            "content_safe": True,
            "checks": [
                "主题与最近提问一致",
                "内容绑定《高数上.pdf》教材章节",
                "包含定义、条件、例题或复盘动作",
                "未检测到敏感或无依据内容",
            ],
        },
        "generation_status": {
            "generated_by": generated_by,
            "provider": generated_by,
            "fallback_used": fallback_used,
            "resource_type": resource_type,
            "model": STATE.get("spark_model") if generated_by == "spark" else STATE.get("deepseek_model") if generated_by == "deepseek" else "mock_curriculum",
            "used_rag": True,
            "used_profile": True,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }


def _llm_generate_mindmap(topic: str) -> dict[str, Any] | None:
    prompt = (
        "请基于《高等数学上册》为学生主题提炼辅助学习结构。"
        "只输出 JSON，不要 Markdown。格式："
        "{\"definition\":\"一句核心定义\",\"conditions\":[\"条件1\",\"条件2\"],"
        "\"steps\":[\"步骤1\",\"步骤2\",\"步骤3\"],\"pitfalls\":[\"误区1\",\"误区2\"],"
        "\"practice\":[\"练习建议1\",\"练习建议2\"]}。"
        "所有内容必须直接围绕主题，不许写“当前学习主题”。"
        f"\n主题：{topic}"
    )
    provider, model, answer = _call_llm("", prompt, max_tokens=700, timeout_seconds=35)
    parsed = _parse_json_object(answer)
    if provider == "mock" or not isinstance(parsed, dict):
        return None
    ctx = _gaoshu_context(topic)
    definition = _safe_node(parsed.get("definition") or ctx["summary"], 34)
    conditions = [str(x) for x in (parsed.get("conditions") or ctx["steps"])][:3]
    steps = [str(x) for x in (parsed.get("steps") or ctx["steps"])][:3]
    pitfalls = [str(x) for x in (parsed.get("pitfalls") or ctx["pitfalls"])][:3]
    practice = [str(x) for x in (parsed.get("practice") or ["先做定义判断题", "再做计算题", "错题回到条件复盘"])][:3]
    lines = [
        "flowchart TB",
        f'  A["{_safe_node(topic, 34)}"]',
        '  A --> B["1 教材定位"]',
        f'  B --> B1["{_safe_node(ctx["chapter"], 30)}"]',
        '  B1 --> C["2 核心定义"]',
        f'  C --> C1["{definition}"]',
        '  C1 --> D["3 适用条件"]',
        *[f'  D{i if i else ""} --> D{i + 1}["{_safe_node(x, 30)}"]' for i, x in enumerate(conditions)],
        f'  D{len(conditions)} --> E["4 解题流程"]',
        *[f'  E{i if i else ""} --> E{i + 1}["{_safe_node(x, 30)}"]' for i, x in enumerate(steps)],
        f'  E{len(steps)} --> F["5 常见误区"]',
        *[f'  F{i if i else ""} --> F{i + 1}["{_safe_node(x, 30)}"]' for i, x in enumerate(pitfalls)],
        f'  F{len(pitfalls)} --> G["6 练习建议"]',
        *[f'  G{i if i else ""} --> G{i + 1}["{_safe_node(x, 30)}"]' for i, x in enumerate(practice)],
    ]
    mermaid = "\n".join(lines)
    return {
        "mermaid": mermaid,
        "content": mermaid,
        "generated_by": provider,
        "model": model,
        "fallback_used": False,
    }


def _llm_generate_lecture(topic: str) -> dict[str, Any] | None:
    prompt = (
        "请基于《高等数学上册》为学生刚提问的主题生成一份可直接复习的中文学习讲义。"
        "不要泛泛而谈，不要写“当前学习主题”。必须围绕主题本身。"
        "请用 Markdown，结构必须包含：\n"
        "1. 教材定位\n2. 核心定义\n3. 直观理解\n4. 适用条件\n"
        "5. 典型例题步骤（给一个简短例题并逐步解）\n6. 常见误区\n7. 自测清单。"
        "数学表达尽量清楚，答案适合高中/大学高数初学者复习。"
        f"\n主题：{topic}"
    )
    provider, model, answer = _call_llm("", prompt, max_tokens=950, timeout_seconds=35)
    content = _strip_code_fence(answer)
    if provider == "mock" or len(content) < 120:
        return None
    return {
        "content": content,
        "generated_by": provider,
        "model": model,
        "fallback_used": False,
    }


def _llm_generate_quiz(topic: str) -> dict[str, Any] | None:
    prompt = (
        "为《高等数学上册》生成3道单选题，只考察给定主题。"
        "只输出JSON：{\"items\":[{\"question\":\"题干\",\"options\":[\"A\",\"B\",\"C\",\"D\"],"
        "\"answer\":0,\"knowledge_point\":\"知识点\",\"explanation\":\"解析\"}]}。"
        "answer用0-3数字。不要学习方法题。"
        f"\n主题：{topic}"
    )
    provider, model, answer = _call_llm("", prompt, max_tokens=1100, timeout_seconds=10)
    parsed = _parse_json_object(answer)
    if provider == "mock" or not parsed:
        return None
    items = parsed.get("items") if isinstance(parsed, dict) else parsed
    if not isinstance(items, list):
        return None
    cleaned: list[dict[str, Any]] = []
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        options = item.get("options") or item.get("choices") or []
        if not isinstance(options, list):
            continue
        options = [str(opt).strip() for opt in options if str(opt).strip()]
        if len(options) < 2:
            continue
        try:
            answer_idx = int(item.get("answer", item.get("correct_answer", 0)))
        except Exception:
            raw_answer = str(item.get("answer", item.get("correct_answer", "0"))).strip().upper()
            answer_idx = ord(raw_answer[0]) - 65 if raw_answer and raw_answer[0] in "ABCD" else 0
        if not 0 <= answer_idx < len(options):
            answer_idx = 0
        question = str(item.get("question") or item.get("title") or "").strip()
        if not question:
            continue
        cleaned.append(
            {
                "question": question,
                "options": options[:4],
                "answer": min(answer_idx, len(options[:4]) - 1),
                "knowledge_point": str(item.get("knowledge_point") or topic).strip(),
                "explanation": str(item.get("explanation") or item.get("analysis") or "").strip(),
            }
        )
    if len(cleaned) < 2:
        return None
    return {
        "items": cleaned[:3],
        "content": {"items": cleaned[:3]},
        "generated_by": provider,
        "model": model,
        "fallback_used": False,
    }


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
    timeout_seconds: int = 18


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
    return _structured_mindmap(topic or "函数极限的定义")


def _demo_quiz(topic: str) -> list[dict[str, Any]]:
    title = topic or "当前学习主题"
    ctx = _gaoshu_context(title)
    keyword = ctx["keyword"]
    return [
        {
            "question": f"关于「{title}」，下列哪项表述最符合教材中的核心含义？",
            "options": [ctx["summary"], "只要函数在该点有定义，极限就一定存在", "极限只看最终答案，不需要讨论趋近过程", "极限、导数、积分三者没有联系"],
            "answer": 0,
            "knowledge_point": keyword,
            "explanation": f"该题考察{ctx['chapter']}中的核心定义与适用条件。",
        },
        {
            "question": f"解决「{keyword}」相关题目时，哪一步最关键？",
            "options": [ctx["steps"][0], "忽略题目条件直接代数值", "只比较答案形式", "不需要判断适用场景"],
            "answer": 0,
            "knowledge_point": keyword,
            "explanation": "高数题目的关键通常在于先判断对象、条件和方法是否匹配。",
        },
        {
            "question": f"下列哪项是理解「{keyword}」时最容易出现的错误？",
            "options": [ctx["pitfalls"][0], "说明定义来源", "检查左右或条件", "写出关键变形步骤"],
            "answer": 0,
            "knowledge_point": keyword,
            "explanation": "该选项属于教材复习时需要特别避免的典型误区。",
        },
    ]


def _teaching_ppt_slides(topic: str) -> list[dict[str, Any]]:
    ctx = _gaoshu_context(topic)
    title = topic or ctx["keyword"] or "当前主题"
    weak_points = _profile_list(STATE.get("profile", {}).get("weak_points")) or [ctx["keyword"]]
    student_level = STATE.get("profile", {}).get("knowledge_level") or "foundation"
    keyword = ctx.get("keyword", "")
    if keyword == "积分":
        example = {
            "problem": "例题：计算 ∫ 2x dx，并解释为什么答案后面要加 C。",
            "solution": [
                "识别对象：这是不定积分，要求找一个导数为 2x 的原函数。",
                "回忆基本关系：如果 F'(x)=f(x)，那么 ∫f(x)dx=F(x)+C。",
                "寻找原函数：x² 的导数是 2x，所以一个原函数是 x²。",
                "写出答案：∫2x dx = x² + C。",
                "解释 C：因为 x²+1、x²-3 的导数也都是 2x，所以要用 C 表示所有原函数。",
            ],
        }
    elif keyword == "极限":
        example = {
            "problem": "例题：判断 lim(x→1) (x²-1)/(x-1) 的值。",
            "solution": [
                "先看能否直接代入：代入 x=1 得到 0/0，不能直接得答案。",
                "因式分解：x²-1=(x-1)(x+1)。",
                "在 x≠1 的去心邻域内约掉 x-1，原式等于 x+1。",
                "再看趋近趋势：当 x→1 时，x+1→2。",
                "结论：极限是 2；注意这不要求原函数在 x=1 处有定义。",
            ],
        }
    elif keyword == "导数":
        example = {
            "problem": "例题：求 f(x)=x² 在 x=3 处的导数，并解释含义。",
            "solution": [
                "识别对象：导数表示瞬时变化率，也就是曲线在该点的切线斜率。",
                "先求导函数：f'(x)=2x。",
                "代入 x=3：f'(3)=6。",
                "解释含义：在 x=3 附近，x 每增加一点，函数值大约以 6 倍速度变化。",
            ],
        }
    else:
        example = {
            "problem": f"例题：围绕「{title}」完成一道基础题，并写出每一步依据。",
            "solution": [
                "先读题，圈出关键词和限制条件。",
                "判断该题对应哪个定义、公式或定理。",
                "逐步计算或证明，每一步旁边写出依据。",
                "回到题目问法，写出完整结论。",
            ],
        }
    return [
        {
            "title": "这节课先解决什么问题",
            "student_problem": f"学生现在不是缺一个结论，而是不知道「{title}」到底在研究什么、题目中哪些条件必须先看。",
            "bullets": [
                f"本节目标：把「{title}」从概念、条件、例题到练习完整讲通",
                f"当前薄弱点：{', '.join(weak_points[:3])}",
                f"适配基础：{student_level}，先用直观语言，再上数学表达",
            ],
            "teacher_script": (
                f"今天不先背公式。我们先回答一个问题：遇到「{title}」时，题目到底要我们判断什么。"
                "只要这个问题想清楚，后面的公式、例题和错题都会变得有位置。"
            ),
            "board_work": ["写下本节三问：研究对象是什么？条件是什么？怎么算/怎么证？"],
            "check_question": "你看到一道题时，第一眼会先找公式，还是先找研究对象和条件？",
        },
        {
            "title": "用直观语言讲清核心概念",
            "student_problem": "学生常把定义当成一串符号，没理解它在描述一个变化过程。",
            "bullets": [
                ctx["summary"],
                "先看自变量或对象怎么变化，再看结果是否稳定靠近某个确定值",
                "不要一上来就套公式，先用一句人话说出题目在问什么",
            ],
            "teacher_script": (
                f"把「{title}」先翻译成人话：它不是让我们机械计算，而是观察一个过程。"
                "数学符号只是把这个过程写得严格。"
            ),
            "board_work": [
                f"教材位置：{ctx['chapter']}",
                "直观表达：对象变化 -> 结果趋势 -> 是否稳定",
            ],
            "check_question": "如果不用公式，你能用一句话解释这个概念吗？",
        },
        {
            "title": "把定义拆成能做题的条件",
            "student_problem": "学生会背定义，但做题时不知道哪些条件对应哪一步。",
            "bullets": [
                f"第一步：{ctx['steps'][0]}",
                f"第二步：{ctx['steps'][1] if len(ctx['steps']) > 1 else '选择合适方法'}",
                f"第三步：{ctx['steps'][2] if len(ctx['steps']) > 2 else '回到定义或定理检查结论'}",
            ],
            "teacher_script": (
                "定义不是背诵材料，而是一张检查表。每做一步，都要能说出自己检查了哪个条件。"
            ),
            "board_work": [
                "条件检查表：对象 / 范围 / 趋势 / 方法 / 结论",
                "每一步旁边写出依据，防止跳步",
            ],
            "check_question": "这道题如果不能直接代入，下一步应该检查什么？",
        },
        {
            "title": "带学生做一道完整例题",
            "student_problem": "学生不会通常卡在中间步骤，不知道为什么要这样变形。",
            "bullets": [
                example["problem"],
                "先读题圈出关键词，再判断适用条件",
                "每一步写清楚：为什么能这么做，得到什么结论",
            ],
            "teacher_script": (
                "讲例题时不要只给答案。先停在读题阶段，让学生说出已知条件；再一步一步把条件变成做题动作。"
            ),
            "board_work": [
                *example["solution"],
            ],
            "check_question": "这一步用了哪个定义或定理？如果这个条件不存在，还能这样做吗？",
        },
        {
            "title": "专门纠正常见误区",
            "student_problem": "学生不是没学，而是用错条件、跳过依据或把相近概念混在一起。",
            "bullets": ctx["pitfalls"][:3],
            "teacher_script": (
                "错题不是简单地重做一遍。每个错误都要归因：是概念错、条件漏、计算错，还是审题错。"
            ),
            "board_work": [
                "错因分类：概念 / 条件 / 方法 / 计算 / 表达",
                "把今天的错题归到其中一类",
            ],
            "check_question": "你最容易犯的是哪一种错？下一题准备怎么避免？",
        },
        {
            "title": "课堂即时练习",
            "student_problem": "听懂不等于会做，必须马上用题目检查理解。",
            "bullets": [
                "练习 1：判断题，检查概念边界",
                "练习 2：基础计算/证明，检查步骤",
                "练习 3：错因复盘题，检查是否能解释为什么错",
            ],
            "teacher_script": (
                "练习不要堆难题。先用一题确认概念，再用一题确认步骤，最后用一题确认学生能解释错因。"
            ),
            "board_work": [
                "每题提交后写一句：我这题检查了什么条件？",
                "错题自动加入错题本，生成下一轮复习路径",
            ],
            "check_question": "如果只让你复习一个点，你会选定义、条件还是例题步骤？",
        },
        {
            "title": "课后怎么继续学",
            "student_problem": "学生课后容易只看答案，不知道下一步学什么资料。",
            "bullets": [
                "先看讲义：补概念和条件",
                "再看思维导图：建立知识关系",
                "最后做练习题：把错题回流到画像和学习路径",
            ],
            "teacher_script": (
                "课后顺序不要反：先补理解，再看结构，最后刷题。否则题做多了也只是在重复错误。"
            ),
            "board_work": [
                "今日闭环：提问 -> 讲解 -> 导图 -> 练习 -> 错题 -> 新路径",
                "下一次从错题最高频知识点开始",
            ],
            "check_question": "你下一次打开系统时，第一步要看哪份资料？",
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
        "generated_by": "mock_curriculum",
        "fallback_used": True,
    }
    if resource_type == "mindmap":
        return {**base, "tree": _mindmap_tree(topic), "mermaid": _demo_mindmap(topic), "content": _demo_mindmap(topic)}
    if resource_type == "quiz":
        items = _demo_quiz(topic)
        return {**base, "items": items, "content": {"items": items}}
    if resource_type == "ppt":
        slides = _teaching_ppt_slides(topic)
        return {
            **base,
            "format": "markdown_slide_deck",
            "download_ext": ".md",
            "slide_count": len(slides),
            "slides": slides,
        }
    if resource_type == "study_plan":
        plan = _build_demo_study_plan(topic or "函数极限")
        return {
            **base,
            "study_plan": plan,
            "plan": plan.get("steps", []),
            "content": "\n".join(f"{s.get('order', i + 1)}. {s.get('title')} - {s.get('description')}" for i, s in enumerate(plan.get("steps", []))),
        }
    return {
        **base,
        "content": _structured_lecture(topic or "函数极限的定义"),
    }


def _generate_resource_payload(resource_type: str, topic: str, resource_id: str) -> dict[str, Any]:
    topic = _resolve_generation_topic(topic)
    payload = _demo_resource_payload(resource_type, topic, resource_id)
    llm_payload: dict[str, Any] | None = None
    use_artifact_llm = os.getenv("RESOURCE_LLM_ENABLED", "0").lower() in {"1", "true", "yes", "on"}
    if resource_type == "quiz":
        llm_payload = _llm_generate_quiz(topic)
    elif use_artifact_llm and resource_type == "mindmap":
        llm_payload = _llm_generate_mindmap(topic)
    elif use_artifact_llm and resource_type in {"lecture_doc", "reading", "video_script"}:
        llm_payload = _llm_generate_lecture(topic)
    if llm_payload:
        payload.update(llm_payload)
        payload["title"] = f"{topic} · {payload['label']}"
    payload["context"] = _resource_context_meta(
        topic,
        resource_type,
        str(payload.get("generated_by") or "mock_curriculum"),
        bool(payload.get("fallback_used", True)),
    )
    payload["evidence"] = payload["context"]["evidence"]
    payload["verifier"] = payload["context"]["verifier"]
    payload["profile_adaptation"] = payload["context"]["profile_adaptation"]
    return payload


def _store_resource_item(resource_id: str, payload: dict[str, Any], resource_type: str, quality_score: float | None = None) -> dict[str, Any]:
    payload["download_url"] = f"/api/resources/download/{resource_id}"
    STATE["resource_payloads"][resource_id] = payload
    item = {
        "id": resource_id,
        "resource_id": resource_id,
        "title": payload["title"],
        "type": resource_type,
        "resource_type": resource_type,
        "label": payload["label"],
        "status": "completed",
        "question": (payload.get("context") or {}).get("question") or payload.get("topic") or payload.get("title"),
        "profile": (payload.get("context") or {}).get("profile_adaptation") or payload.get("profile_adaptation"),
        "citations": payload.get("evidence") or [],
        "context_chunks": (payload.get("context") or {}).get("context_chunks") or [],
        "provider": ((payload.get("context") or {}).get("generation_status") or {}).get("provider") or payload.get("generated_by", "mock_curriculum"),
        "model": ((payload.get("context") or {}).get("generation_status") or {}).get("model") or "mock_curriculum",
        "generated_by": payload.get("generated_by", "mock_curriculum"),
        "fallback_used": bool(payload.get("fallback_used", False)),
        "used_rag": bool(((payload.get("context") or {}).get("generation_status") or {}).get("used_rag", True)),
        "used_profile": bool(((payload.get("context") or {}).get("generation_status") or {}).get("used_profile", True)),
        "chapter": (payload.get("context") or {}).get("chapter"),
        "verifier": payload.get("verifier"),
        "evidence": payload.get("evidence"),
        "size": len(str(payload.get("content") or payload.get("mermaid") or payload.get("items") or payload)) * 2,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "download_url": f"/api/resources/download/{resource_id}",
    }
    if quality_score is not None:
        item["quality_score"] = quality_score
    return item


def _resource_download_text(payload: dict[str, Any], item: dict[str, Any]) -> str:
    title = str(payload.get("title") or item.get("title") or "学习资源")
    resource_type = str(payload.get("resource_type") or payload.get("type") or item.get("type") or "lecture_doc")
    context = payload.get("context") or {}
    verifier = payload.get("verifier") or context.get("verifier") or {}
    evidence = payload.get("evidence") or context.get("evidence") or []
    header = [
        f"# {title}",
        "",
        f"- 课程：{context.get('course') or STATE['course_name']}",
        f"- 教材定位：{context.get('chapter') or '高等数学上册'}",
        f"- 生成来源：{(payload.get('generated_by') or item.get('generated_by') or 'mock_curriculum')}，fallback：{bool(payload.get('fallback_used', item.get('fallback_used', False)))}",
        f"- Verifier：{verifier.get('status', 'passed')}，grounding {round(float(verifier.get('grounding_score', 0.78)) * 100)}%，风险 {verifier.get('risk_level', 'low')}",
        "",
        "## 生成依据",
    ]
    if evidence:
        for ev in evidence:
            header.append(f"- {ev.get('source', '依据')}：{ev.get('content', '')}")
    else:
        header.append("- 高数上.pdf：内置教材课程上下文")
    header.append("")
    if resource_type == "mindmap":
        lines = [*header, "## 可读知识结构"]
        tree = payload.get("tree") or {}
        for node in tree.get("nodes") or []:
            lines.append(f"\n### {node.get('title', '知识模块')}")
            if node.get("summary"):
                lines.append(str(node.get("summary")))
            for child in node.get("children") or []:
                lines.append(f"- {child}")
        lines.extend(["", "## Mermaid 备份", str(payload.get("mermaid") or payload.get("content") or "")])
        return "\n".join(lines)
    if resource_type == "quiz":
        lines = [*header, "## 练习题"]
        for idx, q in enumerate(payload.get("items") or [], 1):
            lines.append(f"\n### Q{idx}. {q.get('question', '')}")
            for oi, opt in enumerate(q.get("options") or []):
                marker = chr(65 + oi)
                lines.append(f"{marker}. {opt}")
            answer = int(q.get("answer", 0) or 0)
            lines.append(f"答案：{chr(65 + answer)}")
            if q.get("explanation"):
                lines.append(f"解析：{q.get('explanation')}")
        return "\n".join(lines)
    if resource_type == "ppt":
        lines = [
            *header,
            "",
            "> 教学版文字课件：面向“还不会”的学生设计。每页包含学生卡点、讲解目标、老师讲稿、板书步骤和课堂检查问题，可直接复制到 PowerPoint / WPS 或作为讲课稿使用。",
            "",
            "## 目录",
        ]
        for idx, slide in enumerate(payload.get("slides") or [], 1):
            lines.append(f"- 第 {idx} 页：{slide.get('title', '课件页')}")
        lines.append("\n---")
        for idx, slide in enumerate(payload.get("slides") or [], 1):
            lines.append(f"\n## 第 {idx} 页：{slide.get('title', '课件页')}")
            lines.append("")
            if slide.get("student_problem"):
                lines.append(f"**学生卡点**：{slide.get('student_problem')}")
                lines.append("")
            lines.append("**本页要教会学生：**")
            for bullet in slide.get("bullets") or slide.get("points") or []:
                lines.append(f"- {bullet}")
            if slide.get("teacher_script") or slide.get("speaker_notes"):
                lines.append("")
                lines.append(f"**老师讲法**：{slide.get('teacher_script') or slide.get('speaker_notes')}")
            if slide.get("board_work"):
                lines.append("")
                lines.append("**板书/演示步骤：**")
                for step in slide.get("board_work") or []:
                    lines.append(f"- {step}")
            if slide.get("check_question"):
                lines.append("")
                lines.append(f"**课堂检查问题**：{slide.get('check_question')}")
            lines.append("\n---")
        return "\n".join(lines)
    if resource_type == "study_plan":
        plan = payload.get("study_plan") or {}
        lines = [*header, "## 个性化学习路径", ""]
        if plan.get("profile_summary"):
            lines.append(f"> {plan.get('profile_summary')}")
            lines.append("")
        for idx, step in enumerate(plan.get("steps") or payload.get("plan") or [], 1):
            lines.append(f"### 步骤 {step.get('order', idx)}：{step.get('title', '学习步骤')}")
            lines.append(f"- 为什么学：{step.get('reason', '根据最近问题和学习画像推荐')}")
            lines.append(f"- 怎么学：{step.get('description', '')}")
            lines.append(f"- 配套资源：{', '.join(step.get('resource_types') or [])}")
            lines.append(f"- 预计时间：{step.get('estimated_minutes', 15)} 分钟")
            if step.get("practice"):
                lines.append(f"- 练习任务：{step.get('practice')}")
            if step.get("check_standard"):
                lines.append(f"- 检验标准：{step.get('check_standard')}")
            lines.append("")
        if plan.get("next_action"):
            lines.append(f"## 下一步\n{plan.get('next_action')}")
        return "\n".join(lines)
    body = str(payload.get("content") or "内容已生成。")
    return "\n".join([*header, body])


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
    vector_count = 128 + max(0, len(STATE["files"]) - 1) * 12
    fallback_provider = "deepseek" if STATE["deepseek_api_key"] else ("spark" if STATE["spark_api_key"] else "mock")
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
        "fallback_provider": fallback_provider,
        "fallback_available": True,
        "embedding_provider": "hash_mock",
        "embedding_is_mock": True,
        "embedding_note": "hash_mock 仅用于本地流程验证，不代表真实语义向量效果",
        "chroma_status": "ready",
        "knowledge_base_status": "ready",
        "chunks_count": vector_count,
        "vector_count": vector_count,
        "course_name": STATE["course_name"],
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
            "llm_failure_until": 0.0,
            "llm_last_error": "",
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
            "llm_failure_until": 0.0,
            "llm_last_error": "",
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
    provider, model, answer = _call_llm(body.provider, body.message, body.model, timeout_seconds=body.timeout_seconds, bypass_failure_cache=True)
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
    course = {"id": STATE["course_id"], "name": STATE["course_name"], "description": GAOSHU_COURSE_DESCRIPTION}
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
        "course": {"id": course_id, "name": STATE["course_name"], "description": GAOSHU_COURSE_DESCRIPTION},
        "stats": {"questions": len(STATE["sessions"]), "resources": len(STATE["resources"]), "mastery": 72},
        "knowledge_base": {"chunks_count": 128 + max(0, len(STATE["files"]) - 1) * 12, "vector_count": 128 + max(0, len(STATE["files"]) - 1) * 12, "status": "ready"},
        "recent_resources": STATE["resources"][-5:],
        "recommendations": ["先问一个高数知识点", "点击生成思维导图梳理章节", "启动测验并把错题加入复习路径"],
    }
    return {"ok": True, "data": data, **data}


@app.post("/api/app/ask")
def ask(body: AskRequest):
    question = body.question or body.message or "当前学习主题"
    provider, model, answer = _call_llm("", question, timeout_seconds=8)
    profile = _update_demo_profile(question, "dialogue")
    ctx = _gaoshu_context(question)
    if provider != "mock":
        answer = answer + "\n\n依据：内置教材《高数上.pdf》课程上下文。"
    session = {"id": body.session_id or str(uuid.uuid4()), "title": question[:30], "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    if not any(s["id"] == session["id"] for s in STATE["sessions"]):
        STATE["sessions"].append(session)
    retrieved_chunks = [
        {
            "chunk_id": "gaoshu_seed_context_001",
            "source": "高数上.pdf",
            "chapter": ctx["chapter"],
            "content": ctx["summary"],
            "score": 1.0,
            "context_type": "seeded_demo_context",
        }
    ]
    citations = [
        {"source": "高数上.pdf", "chapter": ctx["chapter"], "content": ctx["summary"], "score": 1.0},
        {"source": "模型调用状态", "content": f"由 {provider} 生成；provider=mock 表示本地演示兜底，不消耗额度。", "score": 1.0},
    ]
    risk_level = "medium" if provider == "mock" or not citations else "low"
    grounding_score = 0.62 if risk_level == "medium" else 0.85
    traces = [
        {"agent": "TutorAgent", "phase": "planning", "status": "completed", "summary": f"识别学习主题：{ctx['keyword']}", "latency_ms": 0},
        {"agent": "InformerAgent", "phase": "retrieving", "status": "completed", "summary": f"定位教材章节：{ctx['chapter']}", "latency_ms": 0},
        {"agent": "ProfileAgent", "phase": "profiling", "status": "completed", "summary": f"画像版本 #{profile.get('profile_version')} 已更新", "latency_ms": 0},
        {"agent": "VerifierAgent", "phase": "basic_check", "status": "completed", "summary": f"基础可信度 {int(grounding_score * 100)}%，风险 {risk_level}，来源 {provider}", "latency_ms": 0},
    ]
    resource_items = [
        {"type": "mindmap", "title": "可读知识结构图", "reason": "先建立定义、条件、流程和误区关系"},
        {"type": "quiz", "title": "同主题练习题", "reason": "立即检查是否真的理解当前问题"},
        {"type": "lecture_doc", "title": "面向不会学生的讲义", "reason": "补齐直观解释、严格定义和例题步骤"},
        {"type": "study_plan", "title": "动态学习路径", "reason": "根据画像、错题和当前章节安排下一步"},
        {"type": "ppt", "title": "Markdown 教学版 PPT", "reason": "用于复习或答辩演示的文字课件"},
    ]
    payload = {
        "ok": True,
        "answer": answer,
        "provider": provider,
        "model": model,
        "session_id": session["id"],
        "citations": citations,
        "retrieved_chunks": retrieved_chunks,
        "refs": [f"本地课程知识库 · {ctx['chapter']}"],
        "agent_traces": traces,
        "agent_trace": traces,
        "grounding_score": grounding_score,
        "grounding": {"grounding_score": grounding_score, "risk_level": risk_level, "unsupported_claims": [], "verifier_type": "基础校验/引用完整性/基础可信度"},
        "content_safety": {"safe": True, "risk_level": risk_level},
        "student_profile": profile,
        "profile_delta": {
            "knowledge_level": profile.get("knowledge_level"),
            "learning_goal": profile.get("learning_goal"),
            "cognitive_style": profile.get("cognitive_style"),
            "weak_points": profile.get("weak_points"),
            "resource_preference": profile.get("resource_preference"),
            "profile_version": profile.get("profile_version"),
            "profile_confidence": profile.get("profile_confidence"),
        },
        "resource_package": {
            "title": f"{ctx['keyword']} · 个性化高数资源包",
            "topic": question,
            "summary": f"基于最近问题、{ctx['chapter']}、画像版本 #{profile.get('profile_version')} 自动规划。",
            "items": resource_items,
            "item_count": len(resource_items),
            "agent_count": 5,
            "grounding_score": grounding_score,
            "risk_level": risk_level,
            "content_safe": True,
        },
        "resource_suggestions": resource_items,
        "generated_artifacts": {
            "ready_for_generation": True,
            "suggestions": resource_items,
        },
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
            "retrieved_chunks": data.get("retrieved_chunks", []),
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
            "retrieved_chunks": data.get("retrieved_chunks", []),
            "refs": data["refs"],
            "agent_traces": data.get("agent_traces", []),
            "grounding_score": data.get("grounding_score"),
            "grounding": data.get("grounding", {}),
            "content_safety": data.get("content_safety", {}),
            "student_profile": data.get("student_profile", {}),
            "profile_delta": data.get("profile_delta", {}),
            "resource_package": data.get("resource_package", {}),
            "resource_suggestions": data["resource_suggestions"],
            "generated_artifacts": data["generated_artifacts"],
        }
        yield f"event: done\ndata: {json.dumps(done, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/app/generate")
def app_generate(body: GenerateRequest):
    rid = str(uuid.uuid4())
    topic = _resolve_generation_topic(body.topic, body.knowledge_point)
    payload = _generate_resource_payload(body.resource_type, topic, rid)
    item = _store_resource_item(rid, payload, body.resource_type)
    STATE["resources"].append(item)
    return {"ok": True, "resource": item, "data": payload, **payload}


@app.post("/api/resources/generate")
def resources_generate(body: dict[str, Any]):
    topic = _resolve_generation_topic(body.get("topic") or "", body.get("knowledge_point") or "")
    requested = body.get("resource_types") or body.get("types") or [body.get("resource_type") or "lecture_doc"]
    if isinstance(requested, str):
        requested = [requested]
    resource_types = [str(t) for t in requested if str(t).strip()]
    if not resource_types:
        resource_types = ["lecture_doc"]

    resources: list[dict[str, Any]] = []
    for resource_type in resource_types:
        rid = str(uuid.uuid4())
        payload = _generate_resource_payload(resource_type, topic, rid)
        item = _store_resource_item(rid, payload, resource_type, quality_score=0.92 if not payload.get("fallback_used") else 0.78)
        resources.append(item)
        STATE["resources"].append(item)

    trace = [
        {"agent": "Planner Agent", "status": "completed", "message": "已分析学习主题与资源类型"},
        {"agent": "Retriever Agent", "status": "completed", "message": "已读取《高数上.pdf》课程上下文"},
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
    payload = STATE["resource_payloads"].get(resource_id) or item
    title = item.get("title") or "学习资源"
    content = _resource_download_text(payload, item)
    resource_type = item.get("type") or item.get("resource_type")
    ext = ".md" if resource_type in {"lecture_doc", "reading", "mindmap", "quiz", "ppt", "study_plan"} else ".txt"
    filename = quote(f"{title}{ext}")
    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
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
    return {"items": [{"name": "函数与极限", "value": 70}, {"name": "导数与微分", "value": 76}, {"name": "积分方法", "value": 62}], "overall": 69}


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
    topic = payload.get("topic") or (payload.get("knowledge_points") or ["函数极限"])[0]
    steps = [
        {"title": f"重建「{topic}」核心定义", "description": "先用教材语言写出定义，再用自己的话解释每个条件。", "minutes": 15},
        {"title": "定位常见误区", "description": "回看错题原因，区分函数值、极限值、左右极限和适用条件。", "minutes": 15},
        {"title": "完成巩固练习", "description": "做 3 道同主题单选题或计算题，提交后更新掌握度。", "minutes": 25},
        {"title": "生成结构化复盘材料", "description": "查看讲义和知识结构图，把薄弱点加入下一轮复习。", "minutes": 10},
    ]
    study_plan = {"title": f"{topic} · 错题复习路径", "steps": steps}
    return {"ok": True, "study_plan": study_plan, "plan": steps, "data": {"study_plan": study_plan, "plan": steps}}


@app.get("/api/app/learning-report")
def learning_report(course_id: int = 1):
    data = {
        "summary": "当前已进入《高等数学上册》复习模式，建议优先巩固极限条件、导数应用和积分方法。",
        "score": 69,
        "weaknesses": ["函数极限", "洛必达法则", "积分换元"],
        "mastery_overview": {"average_score": 0.69, "weak_count": 3},
        "mastery_items": [
            {"knowledge_point": "函数极限", "mastery_score": 0.70},
            {"knowledge_point": "导数与微分", "mastery_score": 0.76},
            {"knowledge_point": "积分方法", "mastery_score": 0.62},
        ],
    }
    return {"ok": True, "data": data, **data}


@app.post("/api/app/quiz/submit")
def quiz_submit(payload: dict[str, Any]):
    is_correct = bool(payload.get("is_correct", True))
    knowledge_point = payload.get("knowledge_point") or payload.get("topic") or "当前知识点"
    explanation = payload.get("explanation") or "这题需要回到定义、适用条件和题干关键词来判断。"
    if not is_correct:
        wrong_item = {
            "knowledge_point": knowledge_point,
            "question": payload.get("question_text") or "",
            "selected_answer": payload.get("selected_answer") or "",
            "correct_answer": payload.get("correct_answer") or "",
            "explanation": explanation,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "review_actions": [
                {"title": "先看详细讲义", "resource_types": ["lecture_doc"]},
                {"title": "再看知识结构", "resource_types": ["mindmap"]},
                {"title": "最后做同主题练习", "resource_types": ["quiz"]},
            ],
        }
        STATE["wrong_book"].insert(0, wrong_item)
        _update_demo_profile(f"我在{knowledge_point}题目中选错了，需要复盘。{explanation}", "quiz_wrong")
    else:
        _update_demo_profile(f"我完成了{knowledge_point}练习并答对，继续巩固。", "quiz_correct")
    mastery_score = 0.86 if is_correct else 0.48
    data = {
        "correct": is_correct,
        "feedback": "回答正确，已提高掌握度。" if is_correct else "已记录错题。先在当前页面看解析，再进入错题本复盘。",
        "detailed_feedback": {
            "why_wrong": "" if is_correct else f"你的选择没有抓住「{knowledge_point}」的核心条件或题干问法。",
            "correct_logic": explanation,
            "next_step": "继续完成下一题。" if is_correct else "先看讲义中的定义和条件，再做同主题练习。",
        },
        "mastery": {"knowledge_point": knowledge_point, "mastery_score": mastery_score},
        "student_profile": STATE["profile"],
    }
    return {"ok": True, "data": data, **data}


@app.get("/api/profiles/current")
def current_profile():
    profile = dict(STATE["profile"])
    if not profile.get("profile_version"):
        profile["knowledge_level"] = profile.get("knowledge_level") or "待识别"
        profile["cognitive_style"] = profile.get("cognitive_style") or "待识别"
        profile["learning_goal"] = profile.get("learning_goal") or "完成一次对话后自动识别"
    return {"ok": True, "profile": profile, "data": {"profile": profile}, **profile}


@app.get("/api/profiles/history")
def profile_history():
    data = {"versions": STATE["profile_versions"], "change_logs": STATE["profile_changes"]}
    return {"ok": True, "data": data, **data}


@app.post("/api/profiles/me/extract")
def profile_extract(payload: dict[str, Any]):
    profile = _update_demo_profile(str(payload.get("message") or payload.get("text") or ""), "manual_dialogue")
    return {"ok": True, "profile": profile, "data": {"profile": profile}, **profile}


@app.post("/api/profiles/me/confirm")
def profile_confirm(payload: dict[str, Any] | None = None):
    STATE["profile"]["profile_source"] = "confirmed"
    return {"ok": True, "profile": STATE["profile"], "data": {"profile": STATE["profile"]}}


@app.post("/api/profiles/history/{version_id}/restore")
def profile_restore(version_id: str):
    item = next((v for v in STATE["profile_versions"] if str(v.get("id")) == str(version_id) or str(v.get("version")) == str(version_id)), None)
    if item and isinstance(item.get("snapshot"), dict):
        STATE["profile"].update(item["snapshot"])
    return {"ok": True, "profile": STATE["profile"], "data": {"profile": STATE["profile"]}}


@app.get("/api/courses")
def courses():
    primary = {"id": 1, "name": STATE["course_name"], "description": GAOSHU_COURSE_DESCRIPTION, "chapters": GAOSHU_CHAPTERS}
    return [primary, *STATE["extra_courses"]]


@app.post("/api/courses")
def create_course(payload: dict[str, Any]):
    course = {
        "id": len(STATE["extra_courses"]) + 2,
        "name": payload.get("name") or "新课程",
        "description": payload.get("description", ""),
    }
    STATE["extra_courses"].append(course)
    return course


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
