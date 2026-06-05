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
