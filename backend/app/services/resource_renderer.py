"""Resource renderer: JSON → final format.

Renders:
  - MindMapJSON → Mermaid.js mindmap
  - LectureDocJSON → Markdown
  - QuizJSON → dict (validated passthrough)
"""

import re
import uuid
from typing import Any

from app.schemas.resource import (
    LectureDocJSON,
    MindMapJSON,
    MindMapNode,
    QuizJSON,
)

MAX_MERMAID_DEPTH = 4
MAX_NODE_LABEL_LEN = 40

# ── MindMap → Mermaid ──────────────────────────────────────────────────────────

def render_mindmap_to_mermaid(mindmap: MindMapJSON) -> str:
    """Render a MindMapJSON to Mermaid.js mindmap markup.

    Raises ValueError on invalid structure.
    """
    # Validate we have nodes
    if not mindmap.nodes:
        raise ValueError("mindmap must have at least one root-level node")

    lines = ["mindmap"]
    root_label = _sanitize_mermaid_label(mindmap.title)
    lines.append(f"  root(({root_label}))")

    for node in mindmap.nodes:
        _render_node(node, lines, depth=1, parent_indent="    ")

    return "\n".join(lines)


def _render_node(node: MindMapNode, lines: list[str], depth: int, parent_indent: str) -> None:
    """Recursively append Mermaid mindmap lines for a node tree."""
    if depth > MAX_MERMAID_DEPTH:
        raise ValueError(f"mindmap depth exceeds max {MAX_MERMAID_DEPTH} at node '{node.id}'")

    label = _sanitize_mermaid_label(node.label)
    if not label:
        raise ValueError(f"mindmap node '{node.id}' has empty label after sanitization")

    indent = "  " * (depth + 1)
    # Mermaid mindmap uses indent for nesting
    lines.append(f"{indent}{label}")

    for child in node.children:
        _render_node(child, lines, depth + 1, parent_indent=indent)


def _sanitize_mermaid_label(label: str) -> str:
    """Clean a label for use in Mermaid mindmap.

    Mermaid mindmap labels should not contain:
    - Parentheses (used for special shapes)
    - HTML-like tags
    - Newlines
    """
    # Strip and truncate
    label = label.strip()[:MAX_NODE_LABEL_LEN]

    # Remove characters that break Mermaid mindmap
    label = re.sub(r"[()]", "", label)
    label = re.sub(r"[\n\r]", " ", label)
    label = re.sub(r"<[^>]+>", "", label)

    return label.strip()


# ── Lecture → Markdown ─────────────────────────────────────────────────────────

def render_lecture_to_markdown(lecture: LectureDocJSON) -> str:
    """Render a LectureDocJSON to Markdown text.

    Raises ValueError on missing sections.
    """
    if not lecture.sections:
        raise ValueError("lecture doc must have at least one section")

    lines = [
        f"# {lecture.title}",
        "",
        f"**难度等级**：{_difficulty_label(lecture.difficulty)}",
        "",
    ]

    for i, section in enumerate(lecture.sections, 1):
        heading = section.heading.strip()
        content = section.content.strip()

        if not heading or not content:
            raise ValueError(f"section {i} has empty heading or content")

        lines.append(f"## {heading}")
        lines.append("")
        lines.append(content)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _difficulty_label(d: str) -> str:
    """Convert difficulty code to Chinese label."""
    labels = {
        "beginner": "基础入门 🟢",
        "intermediate": "中级进阶 🟡",
        "advanced": "高级深入 🔴",
    }
    return labels.get(d, d)


# ── Quiz validation ────────────────────────────────────────────────────────────

def render_quiz(quiz: QuizJSON) -> dict[str, Any]:
    """Validate and render a QuizJSON to a dict for API response.

    Raises ValueError on structural issues.
    """
    if not quiz.items:
        raise ValueError("quiz must have at least one item")

    items = []
    for i, item in enumerate(quiz.items):
        if not item.question.strip():
            raise ValueError(f"quiz item {i} has empty question")
        if len(item.options) < 2:
            raise ValueError(f"quiz item {i} has fewer than 2 options")
        if item.answer < 0 or item.answer >= len(item.options):
            raise ValueError(
                f"quiz item {i} answer index {item.answer} out of range [0, {len(item.options) - 1}]"
            )
        if not item.explanation.strip():
            raise ValueError(f"quiz item {i} has empty explanation")

        items.append({
            "question": item.question.strip(),
            "options": item.options,
            "answer": item.answer,
            "explanation": item.explanation.strip(),
        })

    return {
        "title": quiz.title,
        "items": items,
    }


# ── Study Plan rendering ───────────────────────────────────────────────────

def render_study_plan(plan: dict) -> dict[str, Any]:
    """Render a study plan dict (pass-through with basic validation)."""
    required = ["title", "steps"]
    for key in required:
        if key not in plan:
            raise ValueError(f"study plan missing required field: {key}")
    if not plan["steps"] or not isinstance(plan["steps"], list):
        raise ValueError("study plan steps must be a non-empty list")
    return plan
