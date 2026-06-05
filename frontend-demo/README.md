# 智学·多智能体 — 前端学习工作台

## 定位

产品级 AI 学习工作台。不是 API 调试面板，是围绕学生/教师真实使用流程设计的学习软件。

## 文件结构

```
frontend-demo/
├── index.html   — 应用入口（HTML 结构 + 7 页面布局）
├── app.css      — 产品级样式（侧边栏、三栏布局、卡片、进度等）
├── app.js       — 单页应用逻辑（API、导航、页面渲染）
└── README.md
```

## 启动方式

```bash
# 1. 启动后端
cd /home/zhang/projects/intelligent-learning-agent/backend
source ../.venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. 启动前端（新终端）
cd /home/zhang/projects/intelligent-learning-agent/frontend-demo
python -m http.server 5173

# 3. 浏览器打开
# http://127.0.0.1:5173
```

## 页面导航

| 页面 | 功能 |
|------|------|
| 数据看板 | 课程状态、画像摘要、建议操作、一键演示 |
| 学习助手 | 三栏：聊天对话 + Artifacts 展示 + 文献溯源 |
| 资源生成 | 资源卡片选择、生成进度、结果 Tab 展示 |
| 课程管理 | 课程列表、选择当前课程、创建课程 |
| 知识库 | 知识块状态、ChromaDB 状态、RAG 检索测试 |
| 学习路径 | 个性化学习步骤时间线 |
| 设置 | API Key 配置、连接测试、系统状态 |

## 用户流程

1. 打开页面 → 自动检测连接
2. 点击"演示账号登录" → 自动初始化
3. 数据看板查看状态
4. 学习助手：左侧提问 → 中间看资源 → 右侧看引用
5. 资源生成：选类型 → 看进度 → 下载 PPT

## 技术说明

- 纯 HTML+CSS+JS，零构建工具
- Mermaid 通过 CDN 加载（jsdelivr）
- 使用 `/api/app/*` 聚合接口，不直接调用底层 API
- JWT Token 保存在 localStorage
- 不暴露 Token/Course ID/API Base 给用户

## 设计原则

- 用户不接触工程概念（Token, Course ID, API Base）
- 所有页面有内容，无大面积空白
- 每个状态有下一步引导
- 5 类资源有可视化展示区
- 三栏布局降低认知负载
