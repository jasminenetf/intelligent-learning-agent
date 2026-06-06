"""Profile-aware learning recommendations."""

import json
import re
from typing import Any, Optional


def _parse_json_list(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    try:
        data = json.loads(raw)
        return [str(x) for x in data] if isinstance(data, list) else []
    except Exception:
        return []


def suggest_resources_from_question(question: str, profile: Any = None) -> list[dict]:
    """Suggest resource types after a Q&A turn."""
    q = (question or "").strip()
    suggestions: list[dict] = []

    def add(rtype: str, title: str, reason: str):
        if not any(s["type"] == rtype for s in suggestions):
            suggestions.append({"type": rtype, "title": title, "reason": reason})

    if re.search(r"导图|脑图|结构|关系|框架", q):
        add("mindmap", f"{_topic_hint(q)}知识结构图", "问题涉及知识结构与关系梳理")
    if re.search(r"练习|测验|题目|做题|测试", q):
        add("quiz", f"{_topic_hint(q)}专项练习", "问题适合通过练习巩固")
    if re.search(r"讲义|讲解|笔记|总结", q):
        add("lecture_doc", f"{_topic_hint(q)}讲解讲义", "问题适合系统化讲解")
    if re.search(r"PPT|课件|幻灯片", q):
        add("ppt", f"{_topic_hint(q)}课件", "问题适合课件化学习")
    if re.search(r"阅读|拓展|延伸|背景", q):
        add("reading", f"{_topic_hint(q)}拓展阅读", "问题涉及背景与延伸知识")
    if re.search(r"视频|动画|讲解视频|分镜", q):
        add("video_script", f"{_topic_hint(q)}教学脚本", "问题适合视频化讲解")

    prefs = _parse_json_list(getattr(profile, "resource_preference", None) if profile else None)
    for pref in prefs:
        mapping = {
            "mindmap": ("mindmap", "思维导图", "符合你的内容偏好"),
            "quiz": ("quiz", "练习题库", "符合你的练习偏好"),
            "lecture_doc": ("lecture_doc", "讲解讲义", "符合你的讲义偏好"),
            "ppt": ("ppt", "PPT课件", "符合你的课件偏好"),
            "reading": ("reading", "拓展阅读", "符合你的阅读偏好"),
            "video_script": ("video_script", "教学脚本", "符合你的视频学习偏好"),
        }
        if pref in mapping:
            rtype, title, reason = mapping[pref]
            add(rtype, title, reason)

    weak_points = _parse_json_list(getattr(profile, "weak_points", None) if profile else None)
    if weak_points:
        add("quiz", f"{weak_points[0]}巩固练习", f"结合薄弱点「{weak_points[0]}」推荐")

    if not suggestions:
        topic = _topic_hint(q)
        suggestions = [
            {"type": "lecture_doc", "title": f"{topic}讲解讲义", "reason": "先建立概念理解"},
            {"type": "mindmap", "title": f"{topic}知识结构图", "reason": "可视化知识关系"},
            {"type": "quiz", "title": f"{topic}巩固练习", "reason": "检验掌握程度"},
        ]

    return suggestions[:5]


def build_profile_next_actions(profile: Any, weak_points: list[str], accuracy: float = 0.0) -> list[dict]:
    """Build actionable next steps from profile + learning state."""
    actions: list[dict] = []
    goal = getattr(profile, "learning_goal", None) or "课程掌握"
    level = getattr(profile, "knowledge_level", None) or "intermediate"
    prefs = _parse_json_list(getattr(profile, "resource_preference", None))

    if accuracy < 0.5 and weak_points:
        actions.append({
            "action": "review_weak_points",
            "title": f"优先复盘：{weak_points[0]}",
            "detail": "正确率偏低，建议先针对薄弱点生成讲义和练习",
            "resource_types": ["lecture_doc", "quiz"],
        })
    elif accuracy < 0.8:
        actions.append({
            "action": "practice_more",
            "title": "加强练习与复盘",
            "detail": "建议生成练习题并进入错题本复盘",
            "resource_types": ["quiz", "mindmap"],
        })
    else:
        actions.append({
            "action": "advance",
            "title": "进入进阶学习",
            "detail": "掌握较好，可生成拓展阅读或学习路径",
            "resource_types": ["reading", "study_plan"],
        })

    if "mindmap" in prefs:
        actions.append({
            "action": "preferred_mindmap",
            "title": "生成思维导图",
            "detail": "结合你的图解偏好，建议先做知识结构梳理",
            "resource_types": ["mindmap"],
        })
    elif "quiz" in prefs:
        actions.append({
            "action": "preferred_quiz",
            "title": "生成专项练习",
            "detail": "结合你的练习偏好，建议先做题目巩固",
            "resource_types": ["quiz"],
        })

    actions.append({
        "action": "align_goal",
        "title": f"围绕目标：{goal}",
        "detail": f"当前基础水平：{level}，建议按目标持续学习",
        "resource_types": ["lecture_doc", "reading"],
    })
    return actions[:4]


def build_wrong_book_review_actions(
    knowledge_point: str,
    topic: str = "",
    profile: Any = None,
) -> list[dict]:
    """Build review loop actions: wrong-book → study plan → resources."""
    kp = (knowledge_point or topic or "薄弱知识点").strip()
    actions: list[dict] = [
        {
            "action": "generate_lecture",
            "title": f"{kp}复盘讲义",
            "detail": "先通过讲义重新理解概念",
            "resource_types": ["lecture_doc"],
        },
        {
            "action": "generate_quiz",
            "title": f"{kp}巩固练习",
            "detail": "通过专项练习检验是否掌握",
            "resource_types": ["quiz"],
        },
        {
            "action": "generate_mindmap",
            "title": f"{kp}知识结构图",
            "detail": "用思维导图梳理知识关系",
            "resource_types": ["mindmap"],
        },
        {
            "action": "study_plan",
            "title": f"{kp}复习路径",
            "detail": "生成个性化复习步骤",
            "resource_types": ["study_plan"],
        },
    ]
    prefs = _parse_json_list(getattr(profile, "resource_preference", None) if profile else None)
    if "mindmap" in prefs:
        actions.insert(0, actions.pop(2))
    elif "quiz" in prefs:
        actions.insert(0, actions.pop(1))
    return actions[:4]


def _topic_hint(question: str) -> str:
    q = (question or "").strip()
    if len(q) <= 18:
        return q or "当前主题"
    return q[:18] + "…"
