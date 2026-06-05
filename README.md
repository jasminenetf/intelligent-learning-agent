<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platform">
</p>

<h1 align="center">智学·多智能体</h1>
<h3 align="center">Intelligent Learning Agent</h3>
<p align="center">高等教育个性化学习资源多智能体系统</p>

---

## 项目简介

智学·多智能体是一个面向高校的个性化学习资源生成与辅导系统。基于 **LangGraph 多智能体架构** 和 **Agentic RAG** 技术，为每门课程自动构建知识库，并生成个性化学习资源。

### 核心功能

| 功能 | 说明 |
|------|------|
| 知识库构建 | 上传课程资料（PDF/DOCX/TXT）→ 自动解析 → 语义检索 |
| 智能问答 | 基于课程知识库的 RAG Q&A，带文献引用溯源 |
| 资源生成 | 思维导图、讲义文档、练习题、PPT课件、学习计划 |
| 学生画像 | 8维学习特征分析，个性化推荐 |
| 多智能体 | Supervisor → Profile → RAG → Lecture → Verifier |

### 技术栈

`FastAPI` `SQLModel` `ChromaDB` `LangGraph` `DeepSeek` `sentence-transformers` `python-pptx`

---

## 一键安装

### Windows

```bash
# 1. 安装 WSL（如已安装可跳过）
wsl --install

# 2. 下载项目
#    点击 GitHub 页面右上角绿色 "Code" 按钮 → Download ZIP
#    解压到任意目录

# 3. 双击 install.bat 自动安装
```

### macOS / Linux

```bash
# 1. 下载项目
git clone https://github.com/jasminenetf/intelligent-learning-agent-backend.git
cd intelligent-learning-agent-backend

# 2. 一键安装
bash install.sh
```

### 配置 API Key（推荐：前端设置页）

启动后端和前端后，打开浏览器进入 **系统设置** 页面，在 **DeepSeek 模型配置** 卡片中：

1. 填写自己的 **DeepSeek API Key**
2. 模型选择 **deepseek-v4-pro**（推荐）
3. 点击 **保存配置** → **测试连接**
4. 确认显示 "连接成功" 后即可使用

> 详细步骤见 [朋友下载运行说明](docs/final/朋友下载运行说明.md)

**备选：直接编辑 .env**

也可复制 `backend/.env.example` 为 `backend/.env` 并填写：

```ini
DEEPSEEK_API_KEY=sk-你的APIKey
DEEPSEEK_MODEL=deepseek-v4-pro
```

> 获取 API Key: [https://platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys)
>
> **注意**：`backend/.env` 不会提交到 GitHub（已加入 `.gitignore`）。GitHub 上不包含任何 API Key 是**正常的**，每个人需要自己配置。

---

## 启动

### Windows
双击 `启动智能学习Agent.bat`

### macOS / Linux
```bash
bash scripts/start_app.sh
```

浏览器自动打开 → http://127.0.0.1:5173

### 停止
- Windows: 双击 `停止智能学习Agent.bat`
- macOS / Linux: `bash scripts/stop_app.sh`

---

## 使用流程

```
打开页面 → 演示账号登录 → 数据看板 → 学习助手提问 → 资源生成
```

| 页面 | 功能 |
|------|------|
| 数据看板 | 课程状态、画像摘要、一键演示 |
| 学习助手 | 三栏布局：聊天 + Artifacts + 文献溯源 |
| 资源生成 | 5类资源卡片选择、生成进度、结果展示 |
| 课程管理 | 课程列表、创建课程、上传资料 |
| 知识库 | 知识块管理、ChromaDB状态、RAG检索测试 |
| 学习路径 | 个性化学习步骤时间线 |
| 设置 | API Key配置、连接测试、系统状态 |

---

## 项目结构

```
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/              # 14 个 API 路由
│   │   ├── core/             # 配置、数据库、安全
│   │   ├── models/           # SQLModel 数据模型
│   │   ├── services/         # RAG、LLM、Agent 等服务
│   │   └── main.py           # 应用入口
│   ├── .env.example          # 环境变量模板
│   └── requirements.txt      # Python 依赖
├── frontend-demo/            # 前端（纯 HTML+CSS+JS）
│   ├── index.html
│   ├── app.css
│   └── app.js
├── seed/                     # 演示数据
│   ├── demo_knowledge.txt    # 高等数学上知识文本
│   └── seed_demo.py          # 数据库种子脚本
├── scripts/
│   ├── start_app.sh          # 启动脚本
│   └── stop_app.sh           # 停止脚本
├── install.sh                # 一键安装（Linux/macOS/WSL）
├── install.bat               # 一键安装（Windows）
├── 启动智能学习Agent.bat      # Windows 启动器
└── 停止智能学习Agent.bat      # Windows 停止器
```

---

## API 端点

后端启动在 `http://127.0.0.1:8000`

| 端点 | 说明 |
|------|------|
| `GET /api/app/bootstrap` | 启动自检（无需认证） |
| `POST /api/app/demo-init` | 一键演示环境初始化 |
| `GET /api/app/dashboard` | 数据看板 |
| `POST /api/app/ask` | 课程问答（RAG） |
| `POST /api/app/generate` | 资源生成 |
| `GET /api/settings/status` | 系统配置状态 |
| `POST /api/settings/llm` | 配置 LLM API Key |
| `POST /api/settings/test-llm` | 测试 LLM 连接 |

完整 API 文档: `http://127.0.0.1:8000/docs`

---

## 常见问题

**Q: 启动后浏览器显示"未连接"？**
A: 确认后端已启动。检查 `backend/.env` 是否存在，端口 8000 是否被占用。

**Q: 问答/资源生成返回错误？**
A: 确认已配置 DeepSeek API Key（可在系统设置页面填写并测试连接）。

**Q: deepseek-v4-pro 连接失败？**
A: 可能是 API 权限不足。可在设置页切换为 `deepseek-v4-flash` 或旧兼容模型 `deepseek-chat`。详见 [模型与配置说明](docs/final/模型与配置说明.md)。

**Q: 知识库为空？**
A: 首次安装会自动导入演示知识库（高等数学上，约 16 个知识点）。如需添加更多课程，在"课程管理"上传资料。

**Q: GitHub 上为什么没有 API Key？**
A: 这是**正常的**。API Key 保存在本机 `backend/.env` 文件中，该文件已加入 `.gitignore`，不会被提交。每个人需要自己在设置页填写。

**Q: 讯飞星火需要配置吗？**
A: 不需要。星火是可选的备用模型，默认不启用。DeepSeek 已足够完成所有功能。

**Q: Windows 下 WSL 报错？**
A: 确保 WSL 已安装并设置默认发行版：`wsl --install`，然后 `wsl --set-default Ubuntu`。

---

## 许可证

MIT License

## 作者

jasminenetf

---

<p align="center"><sub>Built with FastAPI + LangGraph + DeepSeek</sub></p>
