# 项目简介 — 高等教育个性化学习资源多智能体系统

## 一句话定义
面向高校的个性化学习资源生成与辅导系统，多智能体架构 + Agentic RAG。
答辩版以科大讯飞星火大模型为主推理引擎，同时保留 DeepSeek / Mock 作为开发与演示 fallback，确保本地 Demo 可运行。

## 当前实现状态（2026-06-10 对齐）
- 当前前端为 `frontend-demo/` 静态学习工作台，不再使用 LobeChat 作为答辩 Demo 主界面。
- 当前答辩后端为 FastAPI 轻量 Demo 入口 `backend/app/demo_main.py`，聚合接口集中在 `/api/app/*`；完整后端 `backend/app/main.py` 保留为开发入口。
- 当前多智能体链路由 LangGraph 实现，核心文件 `backend/app/services/agent_graph.py`。
- 当前向量库为 ChromaDB 本地持久化目录 `data/chroma/`。
- 当前答辩 Demo 聚焦《高数上》真实学习辅助，提问后自动生成思维导图、练习题、学习讲义、学习路径和 Markdown 教学版 PPT。
- 当前 PPT 交付优先使用稳定可打开的 Markdown 教学稿，包含讲稿、板书、例题、自测和错因提醒；`.pptx` 作为后续可选增强，不作为当前答辩稳定链路。
- 当前 `docker-compose.yml` 主要编排 PostgreSQL / Redis / MinIO 基础设施；后端和前端推荐本地脚本启动。
- 当前答辩 Demo 支持免登录体验；正式注册/登录、角色权限作为 P1/P2 安全加固项继续跟进。

## MVP 范围（不可随意扩大）

### 必须实现
1. 对话式问答（Tutor Agent 入口）
2. 课程资料上传 → 自动构建向量知识库（ChromaDB）
3. Agentic RAG 防幻觉回答（Informer + Verifier）
4. 思维导图生成（默认可读知识树 + Mermaid 备份）
5. 学生画像构建（对话隐式提取，6维）
6. Markdown 教学版 PPT 生成（`.pptx` / Presenton 作为后续可选集成）
7. 答辩 Demo 免登录可用；正式用户注册/登录、角色管理进入安全加固项

### 明确不做（后期扩展）
- 高保真视频生成（Seedance 2.0）
- 复杂 3D 仿真
- 完整知识图谱自动构建（可用简单先决关系代替）
- 强化学习路径推荐（初赛用 A* 或简单规则）

## 技术栈（不可随意更换）
| 层 | 技术 | 原因 |
|----|------|------|
| 前端 | frontend-demo 静态工作台 | 答辩可控、无需构建、覆盖完整学习闭环 |
| 后端 | FastAPI (Python) | 异步、与 LangChain 生态兼容 |
| Agent 编排 | LangGraph | 图结构可控，适合教学流程 |
| 推理引擎 | 科大讯飞 Spark LLM + DeepSeek/Mock fallback | Spark 满足赛题要求，fallback 保证开发和演示稳定 |
| 向量库 | ChromaDB | 轻量、易部署 |
| 关系库 | PostgreSQL / SQLite | 用户、课程、记录 |
| 图库 | Neo4j（可选） | 知识图谱、画像关系 |
| 多模态 | 可读知识树 + Mermaid.js + Markdown PPT | 思维导图 + 教学课件下载闭环 |
| 部署 | 本地脚本 + Docker Compose 基础设施 | 答辩本地稳定运行，数据库/缓存/对象存储可容器化 |

## 核心约束
- 必须使用科大讯飞相关工具（Spark LLM、iFlyCode）
- 必须体现"多智能体"架构
- 开源项目使用需标注来源和协议
- 必须防幻觉：回答需带出处引用
- MVP 阶段不做高保真视频生成；教学脚本/浏览器语音朗读只作为 Demo 辅助，不等同于视频/语音产品能力

## 5 个核心 Agent
| Agent | 职责 |
|-------|------|
| Tutor Agent | 用户对话入口，意图解析，任务分发 |
| Informer Agent | 知识库检索，返回带出处文档片段 |
| Verifier Agent | 学术严谨性验证，防幻觉最后防线 |
| Practice Agent | 多模态资源生成（PPT/思维导图/测验） |
| Insight Agent | 后台画像提取，学习行为分析 |

## 验收标准
- 学生上传教材 → 提问 → 得到带引用的答案
- 提问后自动生成导图、练习题、讲义、学习路径和 Markdown PPT
- 思维导图默认以可读知识树渲染，并保留 Mermaid 备份
- 学生画像随对话和答题动态更新，至少展示知识基础、学习目标、认知风格、薄弱点、资源偏好、情绪/信心
- 选错题后原地显示详细讲解，再写入错题本和学习路径调整依据
