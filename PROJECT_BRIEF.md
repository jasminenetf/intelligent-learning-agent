# 项目简介 — 高等教育个性化学习资源多智能体系统

## 一句话定义
面向高校的个性化学习资源生成与辅导系统，多智能体架构 + Agentic RAG，
科大讯飞星火大模型为核心推理引擎。

## MVP 范围（不可随意扩大）

### 必须实现
1. 对话式问答（Tutor Agent 入口）
2. 课程资料上传 → 自动构建向量知识库（ChromaDB）
3. Agentic RAG 防幻觉回答（Informer + Verifier）
4. 思维导图生成（Mermaid.js）
5. 学生画像构建（对话隐式提取，6维）
6. PPT 生成（Presenton）
7. 用户注册/登录、角色管理

### 明确不做（后期扩展）
- 高保真视频生成（Seedance 2.0）
- 复杂 3D 仿真
- 完整知识图谱自动构建（可用简单先决关系代替）
- 强化学习路径推荐（初赛用 A* 或简单规则）

## 技术栈（不可随意更换）
| 层 | 技术 | 原因 |
|----|------|------|
| 前端 | LobeChat | 原生 Spark API 集成，零前端代码 |
| 后端 | FastAPI (Python) | 异步、与 LangChain 生态兼容 |
| Agent 编排 | LangGraph | 图结构可控，适合教学流程 |
| 推理引擎 | 科大讯飞 Spark LLM | 赛题强制要求 |
| 向量库 | ChromaDB | 轻量、易部署 |
| 关系库 | PostgreSQL / SQLite | 用户、课程、记录 |
| 图库 | Neo4j（可选） | 知识图谱、画像关系 |
| 多模态 | Mermaid.js + Presenton | 思维导图 + PPT |
| 部署 | Docker Compose | 一键启动 |

## 核心约束
- 必须使用科大讯飞相关工具（Spark LLM、iFlyCode）
- 必须体现"多智能体"架构
- 开源项目使用需标注来源和协议
- 必须防幻觉：回答需带出处引用
- MVP 阶段不做视频、不做语音

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
- 思维导图自动生成并在前端渲染
- PPT 可从大纲生成并提供下载
- 学生画像随对话动态更新
