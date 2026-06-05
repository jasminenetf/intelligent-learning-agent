# 开源项目来源与协议清单

本项目使用了以下开源项目。按赛题要求，标注来源、用途和协议。

| 名称 | 用途 | 来源 | 协议 | 使用位置 |
|------|------|------|------|---------|
| FastAPI | Web 框架 | https://github.com/fastapi/fastapi | MIT | backend/app/main.py |
| Uvicorn | ASGI 服务器 | https://github.com/encode/uvicorn | BSD-3 | 启动入口 |
| Pydantic | 数据校验 | https://github.com/pydantic/pydantic | MIT | schemas/* |
| SQLModel | ORM 框架 | https://github.com/fastapi/sqlmodel | MIT | models/*, database.py |
| SQLite | 嵌入式数据库 | https://sqlite.org | Public Domain | data/app.db |
| PyJWT | JWT 认证 | https://github.com/jpadilla/pyjwt | MIT | core/security.py |
| pwdlib | 密码哈希 | https://github.com/frankie567/pwdlib | MIT | core/security.py |
| ChromaDB | 向量数据库 | https://github.com/chroma-core/chroma | Apache 2.0 | services/vector_store.py |
| LangGraph | Agent 编排 | https://github.com/langchain-ai/langgraph | MIT | services/agent_graph.py |
| sentence-transformers | 语义嵌入 | https://github.com/UKPLab/sentence-transformers | Apache 2.0 | services/embedding_service.py |
| HuggingFace Transformers | 模型加载 | https://github.com/huggingface/transformers | Apache 2.0 | 间接依赖 |
| PyMuPDF | PDF 解析 | https://github.com/pymupdf/PyMuPDF | AGPL-3.0 | services/document_parser.py, services/ocr_service.py |
| python-docx | DOCX 解析 | https://github.com/python-openxml/python-docx | MIT | services/document_parser.py |
| python-pptx | PPTX 生成 | https://github.com/scanny/python-pptx | MIT | services/ppt_service.py |
| OpenAI Python SDK | LLM API 调用 | https://github.com/openai/openai-python | Apache 2.0 | services/llm_provider.py |
| SQLAdmin | 管理后台 | https://github.com/aminalaee/sqladmin | BSD-3 | app/admin.py |
| Mermaid.js | 思维导图格式 | https://github.com/mermaid-js/mermaid | MIT | 输出格式 |
| LobeChat | 前端兼容 | https://github.com/lobehub/lobe-chat | Apache 2.0 | /v1 接口兼容 |
| NumPy | 数值计算 | https://github.com/numpy/numpy | BSD-3 | embedding 计算 |

## 外部模型服务

| 服务 | 用途 | 说明 |
|------|------|------|
| DeepSeek API | LLM 推理 | 外部商业 API，非开源项目 |
| 科大讯飞 Spark API | LLM 推理（备选）| 外部商业 API，非开源项目 |
