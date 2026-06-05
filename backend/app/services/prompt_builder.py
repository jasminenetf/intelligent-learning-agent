"""Prompt builder for RAG-based course Q&A."""


def build_rag_prompt(
    question: str,
    chunks: list[dict],
    course_name: str | None = None,
) -> list[dict]:
    """Build a messages list for the LLM using retrieved chunks as context."""

    course_label = course_name or "当前课程"

    # Build context from chunks
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        src = chunk.get("source", "未知来源")
        page = chunk.get("page_number", "")
        cid = chunk.get("chunk_id", i)
        content = chunk.get("content", "").strip()
        header = f"[引用{i}] source={src}"
        if page:
            header += f", page={page}"
        header += f", chunk_id={cid}"
        context_parts.append(f"{header}\n内容：{content}")

    context_text = "\n\n".join(context_parts)

    system_prompt = (
        "你是高校课程学习助手。你必须基于下面提供的课程资料来回答问题。\n"
        "要求：\n"
        "1. 如果资料中有直接答案，直接引用并解释。\n"
        "2. 如果资料不足，明确说“当前课程资料不足以回答这个问题”。\n"
        "3. 不要编造不存在的概念或引用来源。\n"
        "4. 回答结构清晰，先给结论，再解释概念，最后给学习建议。\n"
        "5. 回答必须适合大学生学习，避免过于口语化或过于学术化。\n"
        "6. 资料来自课程知识库，不要声称来自“教材原文”或“扫描版 PDF”。"
    )

    user_prompt = (
        f"课程：{course_label}\n\n"
        f"学生问题：{question}\n\n"
        "以下是检索到的课程知识库资料：\n\n"
        f"{context_text}\n\n"
        "请基于以上资料回答学生的问题。在你的回答末尾，必须列出引用的资料编号（如 [引用1]、[引用2] 等）。"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
