# 技术实现说明

## 1. 技术栈

### 前端

- 原生 HTML / CSS / JavaScript
- 页面目录：`frontend-demo`
- 主要文件：`frontend-demo/index.html`、`frontend-demo/app.js`、`frontend-demo/styles.css`
- 主要能力：学习工作台、课程问答、资源生成、资源中心、错题本、学习报告、画像中心、设置页

### 后端

- FastAPI
- SQLModel / SQLAlchemy
- SQLite 默认数据库，预留 PostgreSQL 扩展
- ChromaDB 用于课程资料向量检索
- LangGraph 用于多智能体编排
- DeepSeek / Spark / fallback provider 用于大模型生成

### 测试与验证

- P0 smoke 脚本：`scripts/verify_p0_smoke.py`
- 支持自定义后端地址：`P0_SMOKE_BASE`
- 已覆盖登录、权限、资源中心、学习报告、掌握度、问答可信字段等核心链路

## 2. 目录结构

```text
backend/
  app/
    api/                 # FastAPI 路由
    core/                # 配置、数据库、安全等基础能力
    models/              # SQLModel 数据模型
    schemas/             # 请求和响应 schema
    services/            # 业务服务层
frontend-demo/
  index.html             # 前端页面骨架
  app.js                 # 前端业务逻辑
  styles.css             # 样式
scripts/
  verify_p0_smoke.py     # P0 回归验证脚本
docs/
  system-design.md       # 系统设计说明
  technical-implementation.md
```

## 3. 核心后端模块

### 3.1 问答服务

主要文件：

- `backend/app/services/app_ask_service.py`
- `backend/app/services/app_stream_service.py`
- `backend/app/services/qa_service.py`
- `backend/app/services/agent_graph.py`

职责：

1. 接收课程问题；
2. 调用课程资料检索；
3. 组织 RAG prompt；
4. 运行多智能体流程；
5. 返回回答、引用、防幻觉结果、资源建议和资源包。

### 3.2 多智能体编排

主要文件：

- `backend/app/services/agent_graph.py`

核心智能体：

- TutorAgent / Planner：拆解学习任务；
- ProfileAgent：识别学习画像；
- InformerAgent / Retriever：检索课程资料；
- LectureAgent / Generator：生成回答；
- VerifierAgent：校验回答质量和引用支撑；
- PracticeAgent / ResourceBuilder：准备资源建议和资源包。

Trace 标准字段：

```text
agent
agent_name
phase
status
summary
message
latency_ms
output
timestamp
```

### 3.3 RAG 与防幻觉

主要文件：

- `backend/app/services/rag_service.py`
- `backend/app/services/grounding_service.py`
- `backend/app/services/content_safety_service.py`

核心能力：

- 基于课程资料检索相关切片；
- 为回答提供 citation；
- 计算 grounding_score；
- 识别 unsupported_claims；
- 输出 risk_level；
- 执行内容安全检查。

### 3.4 学习画像

主要文件：

- `backend/app/services/profile_service.py`
- `backend/app/models/student_profile.py`

画像维度：

- 知识基础；
- 学习目标；
- 认知风格；
- 内容偏好；
- 薄弱点；
- 学习节奏；
- 学习历史；
- 情绪/信心状态。

画像来源包括：

- 对话文本；
- 学习行为；
- 测验结果；
- 错题复盘。

### 3.5 资源生成和资源包

主要文件：

- `backend/app/services/app_resource_service.py`
- `backend/app/services/resource_generator.py`
- `backend/app/services/resource_package_service.py`

资源类型：

- 讲义：`lecture_doc`
- 思维导图：`mindmap`
- 练习题：`quiz`
- PPT：`ppt`
- 拓展阅读：`reading`
- 视频脚本：`video_script`
- 学习路径：`study_plan`

资源包包含：

- 标题；
- 主题；
- 资源项；
- 资源数量；
- 智能体数量；
- grounding 分数；
- 风险等级；
- 内容安全状态；
- 摘要和推荐学习顺序。

### 3.6 掌握度和学习报告

主要文件：

- `backend/app/services/mastery_service.py`
- `backend/app/services/quiz_service.py`
- `backend/app/services/learning_report_service.py`

核心链路：

```text
练习题提交
→ 判断正确/错误
→ 更新 KnowledgeMastery
→ 错题进入错题本
→ 学习报告展示掌握度
→ 推荐下一步资源和复习动作
```

学习报告字段：

- total_attempts；
- correct_count；
- accuracy；
- weak_points；
- mastery_overview；
- mastery_items；
- next_actions；
- profile_summary。

## 4. 核心前端页面

### 4.1 学习工作台

文件：`frontend-demo/app.js` 中的 `loadDashboard()`。

展示：

- 项目定位；
- 当前课程；
- 学习闭环流程；
- 课程进度；
- 薄弱点提醒；
- 本周学习摘要；
- 今日任务；
- 智能推荐；
- 最近资源包。

### 4.2 课程问答页

展示：

- 聊天问答；
- 引用来源；
- 防幻觉卡片；
- 多智能体 trace；
- 学习画像摘要；
- 个性化资源包；
- 多模态资源预览。

### 4.3 资源中心

展示：

- 资源统计；
- 资源包概览；
- 资源包详情；
- 资源列表；
- 收藏资源；
- 最近会话。

### 4.4 学习报告

展示：

- 完成率；
- 错题数；
- 收藏数；
- 测验正确率；
- 平均掌握度；
- 学习效果趋势；
- 掌握度分布；
- 错题分布；
- 本周学习摘要；
- 知识点掌握度。

### 4.5 画像中心

展示：

- 八维学习画像；
- 画像如何参与问答/资源包/路径；
- 对话式画像更新；
- 画像变更日志；
- 历史版本。

## 5. 主要 API

| API | 方法 | 说明 |
| --- | --- | --- |
| `/health` | GET | 健康检查 |
| `/api/app/bootstrap` | GET | 应用初始化 |
| `/api/app/dashboard` | GET | 学习工作台数据 |
| `/api/app/ask` | POST | 课程问答 |
| `/api/app/ask/stream` | POST/SSE | 流式问答 |
| `/api/app/generate` | POST | 单资源生成 |
| `/api/resources/generate` | POST | 多资源生成 |
| `/api/resources/generated` | GET | 已生成资源列表 |
| `/api/app/quiz/submit` | POST | 提交练习题并更新掌握度 |
| `/api/app/learning-report` | GET | 学习报告 |
| `/api/analytics/wrong-book` | GET | 错题本 |
| `/api/profiles/current` | GET | 当前学习画像 |
| `/api/profiles/me/extract` | POST | 从自然语言提取画像 |

## 6. 数据模型概览

核心模型包括：

- User：用户；
- Course：课程；
- StudentProfile：学习画像；
- LearningSession：学习会话；
- KnowledgeMastery：知识点掌握度；
- AuditLog：学习行为记录；
- Resource：生成资源；
- Bookmark：收藏资源。

## 7. 防幻觉策略

系统采用多层可信控制：

1. 课程资料检索作为回答依据；
2. 回答展示 citation；
3. grounding_service 计算引用覆盖率；
4. content_safety_service 判断安全风险；
5. VerifierAgent 输出校验结果；
6. 前端展示风险等级、无依据提示和内容安全状态；
7. smoke 验证 ask 返回可信字段。

## 8. 测试和回归

运行方式：

```bash
python scripts/verify_p0_smoke.py
```

指定后端地址：

```bash
P0_SMOKE_BASE=http://127.0.0.1:8010 python scripts/verify_p0_smoke.py
```

Windows PowerShell：

```powershell
$env:P0_SMOKE_BASE='http://127.0.0.1:8010'
python scripts/verify_p0_smoke.py
```

当前已验证通过：

```text
=== ALL CHECKS PASSED ===
```

## 9. 部署说明

默认本地运行：

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

前端可直接打开 `frontend-demo/index.html`，或使用本地静态服务运行。

## 10. 后续架构升级方向

- 混合检索：keyword + vector + rerank；
- 长任务 Job API：资源生成任务持久化、重试、取消；
- 文件存储抽象：local / MinIO / S3；
- Docker Compose：PostgreSQL、Redis、MinIO；
- 更完整的 API 自动化测试；
- 教师端、班级端、多租户 SaaS 扩展。
