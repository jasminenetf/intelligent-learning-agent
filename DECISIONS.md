# 技术决策记录

> 所有技术决策必须记录在此文件。变更需注明原因、影响范围和审批。

---

## 决策 001：核心推理引擎
- **日期**：2026-05-17
- **决策**：使用科大讯飞星火大模型（Spark LLM）
- **原因**：赛题强制要求；支持多智能体协作原生接口
- **替代方案**：无（不可替换）
- **影响**：所有 Agent 推理节点

## 决策 002：Agent 编排框架
- **日期**：2026-05-17
- **决策**：LangGraph
- **原因**：图结构状态机可控性强，支持检查点持久化，适合教学流程严格性要求
- **替代方案**：CrewAI（学习曲线低但控制力弱）、AutoGen（对话驱动不适合教学）
- **影响**：所有 Agent 节点定义

## 决策 003：前端框架
- **日期**：2026-05-17
- **决策**：LobeChat（Docker 部署，不写前端代码）
- **原因**：原生 Spark API 集成，Artifacts 渲染，多模态卡片支持
- **替代方案**：Open WebUI（功能类似）、自研 React（时间不够）
- **影响**：前端层零开发成本

## 决策 004：向量数据库
- **日期**：2026-05-17
- **决策**：ChromaDB
- **原因**：轻量级，Python 原生支持，适合 MVP 阶段教材切片存储
- **替代方案**：Milvus（功能强但部署重）、Weaviate（类似）
- **影响**：RAG 检索层

## 决策 005：关系型数据库
- **日期**：2026-05-17
- **决策**：PostgreSQL（生产）/ SQLite（本地开发）
- **原因**：SQLite 零配置适合快速开发；PostgreSQL 用于部署
- **影响**：用户、课程、记录存储

## 决策 006：图数据库
- **日期**：2026-05-17
- **决策**：暂不引入 Neo4j，用 PostgreSQL JSON 字段存储画像和先决关系
- **原因**：降低学习成本和部署复杂度；MVP 不强制图查询
- **降级**：MVP 后如需复杂图谱查询再引入
- **影响**：Insight Agent 画像存储

## 决策 007：异步任务
- **日期**：2026-05-17
- **决策**：Celery + Redis
- **原因**：PPT/测验生成为长任务，不可阻塞主对话线程
- **替代方案**：直接 HTTP 调用（不够稳定）
- **影响**：Practice Agent 资源生成

## 决策 008：多模态生成
- **日期**：2026-05-17
- **决策**：Mermaid.js（思维导图）+ Presenton（PPT）
- **原因**：两者均开源、Docker 化、API 成熟
- **替代方案**：pptxgenjs（PPT 备选，如 Presenton 部署失败）
- **影响**：Practice Agent

## 决策 009：部署方案
- **日期**：2026-05-17
- **决策**：Docker Compose 单机部署
- **原因**：团队规模小，K8s 过度设计
- **影响**：所有服务编排

## 决策 010：认证模块实现方案
- **日期**：2026-05-17
- **决策**：轻量实现 SQLModel + PyJWT + pwdlib[argon2] + FastAPI Depends
- **原因**：FastAPI Users 成熟但过度设计，MVP 不需要邮箱验证/OAuth；SQLModel 提供 ORM，PyJWT 标准库，pwdlib 封装 argon2
- **参考**：FastAPI 官方 Security 教程
- **替代方案**：FastAPI Users（放弃——太重）
- **影响**：auth.py, security.py, user model

## 决策 011：课程文件上传与文档解析复用策略
- **日期**：2026-05-17
- **决策**：FastAPI UploadFile + PyMuPDF (PDF) + python-docx (DOCX) + 原生 (TXT) + 纯 Python chunker
- **原因**：LangChain text-splitters 镜像不可用，改纯 Python 实现；Marker 太重不适合 MVP
- **替代方案**：LangChain splitter（放弃——镜像不可用）、Marker（放弃——本阶段不接入）
- **影响**：file_storage.py, document_parser.py, chunker.py, courses API

## 决策 012：ChromaDB 向量化与 RAG 检索复用策略
- **日期**：2026-05-17
- **决策**：ChromaDB 本地持久化 + hash_mock embedding（可插拔）+ 纯 Python chunker
- **原因**：hash_mock 保证无网络跑通工程链路；ChromaDB persistence 目录 data/chroma/；sentence-transformers 后续可选升级
- **替代方案**：Dify/FastGPT（放弃——过重）；sentence-transformers（保留为可选）
- **影响**：embedding_service.py, vector_store.py, rag_service.py, rag API

## 决策 013：LangGraph 多智能体编排框架
- **日期**：2026-05-17
- **决策**：LangGraph v1.2.0 StateGraph 五节点线性 DAG
- **原因**：StateGraph 节点通过共享 state 读写数据，适合教学流程严格性要求
- **不采用**：CrewAI（控制力弱）、AutoGen（对话驱动不适合教学）
- **影响**：agent_graph.py, agent API

## 决策 014：阶段 7A 资源生成层不新增依赖
- **日期**：2026-05-18
- **决策**：阶段 7A 资源生成最小闭环不引入 mermaid-py / mermaid / LangChain chain / Python-pptx / Presenton
- **原因**：JSON→Mermaid 是轻量格式转换，不需要 mermaid-py；Lecture Markdown 和 Quiz JSON 为纯文本拼接；RAG 和 LLM 复用已有 rag_service / llm_provider
- **保留**：PPT、Presenton、SQLAdmin、LobeChat 后续阶段按开源成品优先原则处理
- **影响**：resource_renderer.py, resource_generator.py, resources API

## 决策 015：答辩 Demo 前端
- **日期**：2026-06-08
- **决策**：当前答辩 Demo 主界面使用 `frontend-demo/` 静态 HTML/CSS/JS 工作台。
- **原因**：当前代码已形成完整学习闭环页面，启动成本低，演示可控；LobeChat 暂不作为答辩主界面。
- **保留**：LobeChat 可作为后续集成方向，不删除技术储备。
- **影响**：frontend-demo/, README.md, RUNBOOK.md

## 决策 016：推理引擎 fallback 策略
- **日期**：2026-06-08
- **决策**：Spark LLM 作为赛题主引擎；DeepSeek 作为开发/演示备用；Mock 作为离线兜底。
- **原因**：必须体现科大讯飞能力，同时保证本地演示在缺少密钥、网络波动或模型失败时仍可验证工程闭环。
- **约束**：答辩材料中应明确 Spark 是主推理引擎，fallback 仅用于工程稳定性。
- **影响**：llm_provider.py, settings API, README.md

## 决策 017：PPT 生成实现
- **日期**：2026-06-08
- **决策**：当前 PPT 生成使用后端 `python-pptx`，生成文件通过 `/api/resources/download/{resource_id}` 下载。
- **原因**：当前实现已可运行，避免引入 Presenton 容器复杂度。
- **保留**：Presenton 作为 P2/P3 可选升级。
- **影响**：ppt_service.py, generated_file_storage.py, resources API

## 决策 018：部署与启动方式
- **日期**：2026-06-08
- **决策**：答辩与本地开发优先使用 Windows 启停脚本；Docker Compose 当前只编排 PostgreSQL / Redis / MinIO 基础设施。
- **原因**：当前 `docker-compose.yml` 未编排后端和前端，完整容器化仍是后续项。
- **影响**：docker-compose.yml, RUNBOOK.md, README.md

## 决策 019：认证状态
- **日期**：2026-06-08
- **决策**：当前答辩 Demo 允许免登录体验，旧注册/登录接口仅保留兼容入口；正式认证和角色权限作为后续安全加固。
- **原因**：当前前端主流程以免登录演示为主，便于答辩稳定展示；真实用户体系需要单独验收。
- **影响**：auth.py, frontend-demo/app.js, TASKS.md

## 决策 020：一键启动与功能全开放 Demo 模式
- **日期**：2026-06-08
- **决策**：Windows 一键启动脚本默认启动轻量 Demo 后端 `app.demo_main:app` 到 8010，前端到 5173；启动前自动清理旧端口。完整后端认证依赖也统一返回本地 Demo 管理员用户。
- **原因**：当前交付目标是双击启动、填写 API Key 后立即使用，避免登录、角色、权限和端口残留影响演示。
- **约束**：该模式仅用于本地 Demo/答辩；生产环境需要重新启用正式认证、权限和密钥管理。
- **影响**：启动智能学习Agent.bat, 停止智能学习Agent.bat, auth.py, demo_main.py, frontend-demo/app.js

---

## 变更记录模板
```
## 变更 [序号]
- **日期**：YYYY-MM-DD
- **原决策**：[引用的决策编号]
- **新决策**：[内容]
- **原因**：[为什么改]
- **审批**：[谁批准的]
```
