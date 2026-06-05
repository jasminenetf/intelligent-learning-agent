# CLAUDE.md — 智学工坊 AI 自动学习助手 (Intelligent Learning Agent)

## 项目定位

本项目是"智学工坊 AI 自动学习助手"，当前目标为 **30 天比赛版收敛**，非商业级 v2 重构。

**核心指令：每步改动最小化，只做比赛需要的事。**

## 当前技术栈

- 后端：FastAPI + SQLModel + SQLite + ChromaDB + LangGraph + DeepSeek + sentence-transformers + python-pptx
- 前端：frontend-demo/index.html + frontend-demo/app.js + frontend-demo/app.css
- 测试：后续使用 Playwright
- 环境：WSL / DeepSeek v4-pro / HF_HUB_OFFLINE=1 / pip --break-system-packages
- 启动：`backend/ && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- 前端：Vite dev server on :5173

## 当前比赛版策略

- 不要重构后端
- 不要迁移 Next.js
- 不要整体接入 Dify / RAGFlow / FastGPT
- 不要删除旧页面
- 新增"比赛演示模式"作为默认入口
- 旧页面保留为高级功能（通过 secondary entry 访问）

## 安全红线 (CRITICAL)

1. 不准读取、输出、提交 `backend/.env`
2. 不准输出 DeepSeek Key、Spark APIPassword、JWT Token
3. 不准把真实密钥写进 README、报告、截图、日志
4. 提交前必须检查：
   ```
   git check-ignore -v backend/.env
   git ls-files backend/.env
   ```

## 每次修改前必须先读

- `backend/app/main.py`
- `backend/app/api/app.py`
- `frontend-demo/index.html`
- `frontend-demo/app.js`
- `frontend-demo/app.css`
- `docs/handoff/` 最近报告（如存在）

## 每次修改后必须运行

```bash
cd backend && python -m compileall app
cd .. && node --check frontend-demo/app.js
```

如果已有 E2E：
```bash
bash scripts/e2e_browser_smoke.sh
```

## 不允许的行为

- 不允许删除大量旧代码
- 不允许随机重命名 API
- 不允许改动 .env
- 不允许把 course_id / token 暴露到前端主界面
- 不允许页面出现 `Failed to fetch` / `undefined` / `[object Object]`
- 不允许只跑 curl 就说浏览器通过

## 当前比赛主线

学生输入问题（示例）：
> 我在学习人工智能导论，机器学习基础一般，容易混淆过拟合和欠拟合。请帮我理解过拟合和正则化的关系。

系统自动展示学习流程：
画像抽取 → 课程资料检索 → 可信讲解 → 引用溯源 → 思维导图 → 测验 → 学习路径 → PPT 学习包

## 质量门禁

每次提交前必须运行：
```bash
bash scripts/claude_quality_gate.sh
```

## 七个旧页面（保留）

1. 📊 数据看板 (dashboard)
2. 💬 学习助手 (assistant)
3. ⚡ 资源生成 (generator)
4. 📚 课程管理 (courses)
5. 🧠 知识库 (knowledge)
6. 🗺️ 学习路径 (learning-path)
7. ⚙️ 设置 (settings)

以上页面全部保留，通过"高级功能"入口访问。
