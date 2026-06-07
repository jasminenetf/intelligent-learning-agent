<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platform">
</p>

<h1 align="center">智学·多智能体</h1>
<h3 align="center">Intelligent Learning Agent</h3>
<p align="center">课程级 AI 学习工作台：资料理解、问答辅导、资源生成、错题复盘与学习路径推荐</p>

---

## 产品定位

智学·多智能体是一个可部署、可扩展、面向真实使用的智能学习产品。系统围绕“画像构建 → 学习路径规划 → 资源生成 → 问答辅导 → 错题复盘 → 学习报告”的闭环，帮助学生和教师在课程学习中持续提升效率。

### 核心能力

| 能力 | 说明 |
|------|------|
| 课程与资料管理 | 创建课程、上传资料、自动解析、构建知识库 |
| 对话式画像构建 | 通过自然语言对话提取学习特征，动态更新学习画像 |
| 多智能体资源生成 | 协同生成讲义、导图、题库、PPT、拓展阅读等资源 |
| 个性化学习路径 | 基于画像、进度和错题，自动生成学习步骤与推荐 |
| 学习闭环 | 提问、练习、复盘、报告、资源推送形成完整链路 |

### 技术栈

`FastAPI` `SQLModel` `ChromaDB` `LangGraph` `DeepSeek` `sentence-transformers` `python-pptx`

### 推荐升级方向

- 后端主干：`FastAPI` + `PostgreSQL` + `pgvector`
- 异步任务：`Redis` + `Celery/RQ`
- 检索增强：混合检索 + rerank
- 前端工作台：`Next.js` + `React` + `TypeScript` + `shadcn/ui`
- 存储与文件：`MinIO` / `S3`
- 观测与评测：`OpenTelemetry` + tracing / eval

---

## 快速开始

### 1. 安装依赖

#### Windows
双击 `install.bat`

#### macOS / Linux / WSL

```bash
bash install.sh
```

### 2. 配置环境变量

复制 `backend/.env.example` 为 `backend/.env`，并配置模型与数据库相关参数。

```ini
# 答辩推荐：科大讯飞 Spark 为主引擎
LLM_PROVIDER=spark
SPARK_ENABLED=true
SPARK_API_PASSWORD=你的APIPassword

# 或开发备用 DeepSeek
DEEPSEEK_API_KEY=sk-你的APIKey
DEEPSEEK_MODEL=deepseek-v4-pro
```

### 3 分钟答辩演示脚本

1. **设置页**：配置 Spark → 测试连接成功（顶部栏显示 `Spark`）
2. **课程资料库**：上传 PDF/Word（教师账户）→ 确认知识片段数量 > 0
3. **会话中心**：点击「一键演示」→ 观察流式回答 + 右侧五 Agent 协作轨迹 + 课程引用
4. **右侧预览**：自动/手动生成思维导图（Mermaid 渲染）
5. **错题本 → 复习路径**：完成测验错题后演示闭环
6. **学习报告**：展示画像驱动建议

### 3. 启动服务

#### Windows
双击 `启动智能学习Agent.bat`

#### macOS / Linux

```bash
bash scripts/start_app.sh
```

前端默认访问地址：`http://127.0.0.1:5173`
后端默认访问地址：`http://127.0.0.1:8000`

### 4. 停止服务

#### Windows
双击 `停止智能学习Agent.bat`

#### macOS / Linux

```bash
bash scripts/stop_app.sh
```

---

## 使用流程

```text
登录/注册 → 创建课程 → 上传资料 → 构建知识库 → 对话提问 → 生成资源 → 做题复盘 → 查看报告
```

### 主要页面

| 页面 | 功能 |
|------|------|
| 工作台 | 课程状态、学习进度、任务与推荐 |
| 会话中心 | 课程问答、上下文会话、历史记录 |
| 课程中心 | 创建课程、切换课程、课程上下文管理 |
| 资料库 | 课程文件、知识块、解析状态 |
| 资源中心 | 讲义、导图、题库、PPT、拓展阅读等资产管理 |
| 错题本 | 错题记录、复习计划、薄弱点追踪 |
| 学习报告 | 学习进度、行为记录、推荐建议 |
| 账户与设置 | 登录、注册、配置与系统状态 |

---

## API 概览

后端启动在 `http://127.0.0.1:8000`

| 端点 | 说明 |
|------|------|
| `GET /api/app/bootstrap` | 启动自检与课程概览 |
| `POST /api/auth/login` | 用户登录 |
| `POST /api/auth/register` | 用户注册 |
| `GET /api/courses` | 课程列表 |
| `POST /api/courses` | 创建课程 |
| `POST /api/courses/{course_id}/files` | 上传课程资料 |
| `GET /api/courses/{course_id}/files` | 查询课程文件 |
| `GET /api/courses/{course_id}/chunks` | 查询课程知识块 |
| `POST /api/app/ask` | 课程问答（RAG） |
| `POST /api/app/generate` | 资源生成 |
| `GET /api/sessions` | 学习会话列表 |
| `GET /api/analytics/progress` | 学习进度 |
| `GET /api/analytics/wrong-book` | 错题本 |
| `GET /api/analytics/bookmarks` | 收藏资源 |
| `GET /api/settings/status` | 系统状态 |

完整 API 文档：`http://127.0.0.1:8000/docs`

---

## 部署说明

### 本地开发
- 后端：FastAPI
- 前端：静态页面 + 前端脚本
- 数据库：SQLite / SQLModel（按当前配置）

### 生产建议
- 使用 Docker 容器化部署
- 使用独立数据库与对象存储
- 通过环境变量管理模型、数据库、日志与密钥
- 开启健康检查、日志收集与监控告警

---

## 项目结构

```text
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/              # API 路由
│   │   ├── core/             # 配置、数据库、安全
│   │   ├── models/           # 数据模型
│   │   ├── schemas/          # 请求与响应结构
│   │   └── services/         # 业务服务与多智能体编排
│   ├── .env.example          # 环境变量模板
│   └── requirements.txt      # Python 依赖
├── frontend-demo/            # 前端工作台
├── seed/                     # 种子数据
├── scripts/                  # 启停与初始化脚本
├── install.sh                # Linux/macOS/WSL 安装脚本
├── install.bat               # Windows 安装脚本
├── 启动智能学习Agent.bat      # Windows 启动器
└── 停止智能学习Agent.bat      # Windows 停止器
```

---

## 常见问题

**Q: 启动后浏览器显示“未连接”？**  
A: 检查后端是否启动、端口是否占用、`.env` 配置是否正确。

**Q: 问答或资源生成返回错误？**  
A: 检查模型 API Key 和网络连接，确保课程已上传资料并完成知识库构建。

**Q: 为什么 GitHub 上没有 API Key？**  
A: 这是正常的。密钥保存在本机 `backend/.env` 中，不应提交到仓库。

**Q: 知识库为空？**  
A: 请先创建课程并上传资料，系统会自动解析并生成知识块。

---

## 许可证

MIT License

## 作者

jasminenetf

---

<p align="center"><sub>Built with FastAPI + LangGraph + DeepSeek</sub></p>