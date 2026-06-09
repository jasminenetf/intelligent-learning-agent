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


def _call_llm(provider: str, question: str, model_override: str = "", max_tokens: int = 600, timeout_seconds: int | None = None) -> tuple[str, str, str]:
    provider, api_key, base_url, model = _provider_config(provider)
    model = model_override or model
    if provider == "mock" or not api_key:
        return "mock", model, _mock_answer(question)
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
        return provider, model, resp.choices[0].message.content or "已连接模型，但没有返回内容。"
    except Exception as exc:
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
    return "\n".join([
        "flowchart TD",
        f'  A["{t}"]',
        f'  A --> B["教材定位：{_safe_node(ctx["chapter"], 22)}"]',
        f'  A --> C["核心定义"]',
        f'  C --> C1["{_safe_node(ctx["summary"], 34)}"]',
        f'  A --> D["适用条件"]',
        f'  D --> D1["{_safe_node(ctx["steps"][0], 30)}"]',
        f'  D --> D2["先判断对象和趋近方式"]',
        f'  A --> E["解题流程"]',
        f'  E --> E1["{_safe_node(ctx["steps"][0], 30)}"]',
        f'  E --> E2["{_safe_node(ctx["steps"][1] if len(ctx["steps"]) > 1 else "写出关键变形", 30)}"]',
        f'  E --> E3["{_safe_node(ctx["steps"][2] if len(ctx["steps"]) > 2 else "回到定义验证", 30)}"]',
        f'  A --> F["常见误区"]',
        *[f'  F --> F{i + 1}["{_safe_node(p, 30)}"]' for i, p in enumerate(ctx["pitfalls"][:3])],
        f'  A --> G["练习建议"]',
        '  G --> G1["先做定义判断题"]',
        '  G --> G2["再做计算与证明题"]',
        '  G --> G3["错题回到条件复盘"]',
    ])


def _structured_lecture(topic: str) -> str:
    ctx = _gaoshu_context(topic)
    return "\n\n".join([
        f"# {topic} · 学习讲义",
        f"## 1. 教材定位\n《高等数学上册》：{ctx['chapter']}。本节用于建立后续导数、连续性、积分等内容的基础。",
        f"## 2. 核心定义\n{ctx['summary']}",
        "## 3. 直观理解\n先看自变量如何趋近，再看函数值是否稳定靠近某个确定值。重点不是某一点的函数值本身，而是趋近过程中的变化趋势。",
        "## 4. 适用条件\n" + "\n".join(f"- {step}" for step in ctx["steps"]),
        "## 5. 典型例题步骤\n例：判断或计算一个函数在某点的极限。\n1. 明确趋近点与趋近方向。\n2. 代入检查是否出现未定式或定义空缺。\n3. 选择化简、等价无穷小、左右极限或定义验证。\n4. 写出结论，并说明适用条件。",
        "## 6. 常见误区\n" + "\n".join(f"- {pitfall}" for pitfall in ctx["pitfalls"]),
        "## 7. 自测清单\n- 我能说清楚定义中的每个条件吗？\n- 我能区分函数值和极限值吗？\n- 我能判断什么时候需要看左右极限吗？\n- 我能把错题归因到定义、条件或计算步骤吗？",
    ])


def _resolve_generation_topic(topic: str, knowledge_point: str = "") -> str:
    candidate = (topic or knowledge_point or "").strip()
    generic = {"", "当前学习主题", "当前主题", "学习主题", "高等数学", "高等数学上册"}
    if candidate in generic and STATE["sessions"]:
        candidate = str(STATE["sessions"][-1].get("title") or "").strip()
    return candidate or "函数极限的定义"


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
        "flowchart TD",
        f'  A["{_safe_node(topic, 34)}"]',
        f'  A --> B["教材定位：{_safe_node(ctx["chapter"], 22)}"]',
        '  A --> C["核心定义"]',
        f'  C --> C1["{definition}"]',
        '  A --> D["适用条件"]',
        *[f'  D --> D{i + 1}["{_safe_node(x, 30)}"]' for i, x in enumerate(conditions)],
        '  A --> E["解题流程"]',
        *[f'  E --> E{i + 1}["{_safe_node(x, 30)}"]' for i, x in enumerate(steps)],
        '  A --> F["常见误区"]',
        *[f'  F --> F{i + 1}["{_safe_node(x, 30)}"]' for i, x in enumerate(pitfalls)],
        '  A --> G["练习建议"]',
        *[f'  G --> G{i + 1}["{_safe_node(x, 30)}"]' for i, x in enumerate(practice)],
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
    provider, model, answer = _call_llm("", prompt, max_tokens=1100, timeout_seconds=50)
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
        "generated_by": payload.get("generated_by", "demo_template"),
        "fallback_used": bool(payload.get("fallback_used", False)),
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
    if resource_type == "mindmap":
        return "\n\n".join([f"# {title}", "## Mermaid 思维导图", str(payload.get("mermaid") or payload.get("content") or "")])
    if resource_type == "quiz":
        lines = [f"# {title}", "## 练习题"]
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
        lines = [f"# {title}", "## PPT 大纲"]
        for idx, slide in enumerate(payload.get("slides") or [], 1):
            lines.append(f"\n### 第 {idx} 页：{slide.get('title', '课件页')}")
            for bullet in slide.get("bullets") or slide.get("points") or []:
                lines.append(f"- {bullet}")
        return "\n".join(lines)
    return str(payload.get("content") or f"# {title}\n\n内容已生成。")


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
    provider, model, answer = _call_llm("", question)
    if provider != "mock":
        answer = answer + "\n\n依据：内置教材《高数上.pdf》课程上下文。"
    session = {"id": body.session_id or str(uuid.uuid4()), "title": question[:30], "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    if not any(s["id"] == session["id"] for s in STATE["sessions"]):
        STATE["sessions"].append(session)
    citations = [
        {"source": "高数上.pdf", "content": "内置教材章节：函数与极限、导数与微分、微分中值定理与导数应用、不定积分、定积分、定积分应用、微分方程。", "score": 1.0},
        {"source": "模型实时回答", "content": "由当前配置模型或 Mock fallback 生成。", "score": 1.0},
    ]
    traces = [
        {"agent": "TutorAgent", "phase": "planning", "status": "completed", "summary": "免登录 Demo 已接收问题", "latency_ms": 0},
        {"agent": "InformerAgent", "phase": "retrieving", "status": "completed", "summary": "已读取《高数上.pdf》课程上下文", "latency_ms": 0},
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
            "title": f"{question[:20]}高数资源包",
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
    ext = ".md" if (item.get("type") or item.get("resource_type")) in {"lecture_doc", "reading", "mindmap", "quiz"} else ".txt"
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
    return {"ok": True, "plan": [{"title": "复习极限定义与左右极限", "minutes": 20}, {"title": "完成导数和积分针对练习", "minutes": 30}]}


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
    data = {
        "correct": bool(payload.get("is_correct", True)),
        "feedback": "回答已记录。",
        "mastery": {"knowledge_point": payload.get("knowledge_point", "当前知识点"), "mastery_score": 0.8},
    }
    return {"ok": True, "data": data, **data}


@app.get("/api/profiles/current")
def current_profile():
    return {"ok": True, "profile": {"major": "高等数学上册复习", "knowledge_level": "medium", "cognitive_style": "logical", "pace_preference": "moderate", "weak_points": ["函数极限", "洛必达法则", "积分换元"]}}


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
