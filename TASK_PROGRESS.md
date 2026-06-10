# TASK_PROGRESS

## 2026-06-10 恢复现场

- 工作目录：`C:\Users\zhang\Desktop\智能学习`
- 远端仓库：`https://github.com/jasminenetf/intelligent-learning-agent`
- 当前分支：`feat/product-workbench-core-pipeline`
- 分支检查：已在目标工作分支，不改 `main`。
- 未提交修改：恢复现场时 `git status --short` 为空。
- 关键提交检查：
  - `18ede88 Fix learning artifact generation quality`：完整历史存在。
  - `09d5884 Generate teaching-focused PPT markdown decks`：完整历史存在。
- 最近 10 条提交：
  - `1e1d683 Add official A3 defense deck`
  - `c448132 Add static QA workflow and update delivery docs`
  - `dd191d0 Strengthen gaoshu demo loop and deep QA`
  - `f310ddf Fit mindmap to preview viewport`
  - `6182214 Explain quiz mistakes inline and expand lectures`
  - `09d5884 Generate teaching-focused PPT markdown decks`
  - `b3b7e94 Export PPT resources as readable markdown decks`
  - `4535d04 Personalize learning path and profile updates`
  - `af7db85 Auto generate readable study artifacts`
  - `ebc1cea Harden dynamic UI action buttons`

## 本轮执行原则

- 不重做已完成 P0，不大重构，不替换技术栈。
- 不提交真实 API Key、`.env`、日志密钥或本地数据库。
- Spark Key 只允许用于必要的单次连接验证，验证记录必须脱敏。
- Mock、fallback、hash_mock、基础 Verifier 必须诚实标注，不能包装成真实模型或真实事实核查。

## 待记录验证

- `python -m py_compile backend/app/demo_main.py`
- `node --check frontend-demo/app.js`
- `python -m pytest -q backend/tests`
- `python scripts/verify_p0_smoke.py`
- 可选：`npx playwright test`
- 可选：浏览器从首次打开到一键演示完整验收。

## 2026-06-10 本轮进展

- 验证：
  - `python -m py_compile backend/app/demo_main.py`：通过。
  - `node --check frontend-demo/app.js`：通过。
  - `python -m pytest -q backend/tests`：通过，4 passed，1 个 StarletteDeprecationWarning。
  - `python scripts/verify_p0_smoke.py`：首次因 8010 未启动失败；启动 Demo 后端后通过。
  - `npx playwright test`：首次缺少 `@playwright/test`，安装依赖后缺少 Chromium，安装浏览器后发现 4 个真实 E2E 缺口；修复后 9 passed。
  - `python scripts/deep_qa_check.py`：通过。
  - Spark 真实连接测试：通过。`/api/settings/test-llm` 返回 `provider=spark`、`model=generalv3.5`、`message=spark 连接可用`，延迟约 8.8 秒；未记录或提交 API Key。
  - 已跟踪文件敏感信息扫描：通过，未发现用户提供的 Spark Key 或真实 token 进入仓库。
  - 内置浏览器 1366×768 可视化验收：通过。默认课程为高等数学上册；一键演示可生成问题、回答、引用、可读思维导图和 Agent 面板；页面无横向溢出；控制台无 error。
- 修复：
  - 前端 placeholder、E2E、后端测试、离线 demo payload 统一为《高数上/函数极限》。
  - `/api/settings/status` 增加 Chroma/vector_count/knowledge_base_status/course_name/embedding_note。
  - 设置页显示 provider/model/Spark/DeepSeek/fallback/embedding/知识库状态，并标注 `hash_mock` 仅流程验证。
  - `/api/app/ask` 增加 `retrieved_chunks`，Mock 或无引用时风险至少 `medium`，Verifier 标注为基础可信度。
  - 资源 item 增加 question/profile/citations/context_chunks/provider/model/fallback/used_rag/used_profile/created_at 相关字段。
  - 资源中心和生成结果卡片显示生成来源、fallback、RAG、画像和引用片段数。
  - 会话页新增“一键演示”按钮，自动填入函数极限标准问题并发送。
  - Playwright E2E 端口改为 8010，测试主题改为函数极限。
  - README/RUNBOOK/.env.example 更新；新增 `DEMO_SCRIPT_7MIN.md`、`SUBMISSION_CHECKLIST.md`、`AI_CODING_USAGE.md`。
