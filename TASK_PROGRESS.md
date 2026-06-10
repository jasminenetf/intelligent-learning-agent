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

## 2026-06-10 再次恢复现场

- 当前分支：`feat/product-workbench-core-pipeline`。
- 恢复时未提交修改：无。
- 最近提交：
  - `d673f00 chore: harden competition demo candidate`
  - `1e1d683 Add official A3 defense deck`
  - `c448132 Add static QA workflow and update delivery docs`
  - `dd191d0 Strengthen gaoshu demo loop and deep QA`
  - `f310ddf Fit mindmap to preview viewport`
  - `6182214 Explain quiz mistakes inline and expand lectures`
  - `09d5884 Generate teaching-focused PPT markdown decks`
  - `b3b7e94 Export PPT resources as readable markdown decks`
  - `4535d04 Personalize learning path and profile updates`
  - `af7db85 Auto generate readable study artifacts`
- 关键提交检查：
  - `18ede88 Fix learning artifact generation quality`：存在。
  - `09d5884 Generate teaching-focused PPT markdown decks`：存在。
- 本轮继续原则：不重构、不重复 P0 修复；只复核当前候选成品状态，发现 S0/S1 再修。
- 本轮验证：
  - `python -m py_compile backend/app/demo_main.py scripts/verify_p0_smoke.py scripts/deep_qa_check.py`：通过。
  - `node --check frontend-demo/app.js`：通过。
  - `python -m pytest -q backend/tests`：通过，4 passed，1 个 StarletteDeprecationWarning。
  - `python scripts/verify_p0_smoke.py`：通过，`=== ALL CHECKS PASSED ===`。
  - `python scripts/deep_qa_check.py`：通过，`=== DEEP QA PASSED ===`。
  - `npx playwright test`：通过，9 passed。
  - 候选提交文件安全扫描：通过，未发现用户 Spark Key、token、refresh token、`.env` 或日志密钥进入提交候选。
- 本轮结论：当前候选状态仍满足初赛提交候选标准；本轮无 S0/S1 新缺口。

## 2026-06-10 第四次上传前复核

- 当前分支：`feat/product-workbench-core-pipeline`。
- 恢复时未提交业务修改：无；本节用于记录本次上传前复核。
- 最近提交：
  - `1d3fb6d chore: harden competition demo candidate`
  - `2d02ace chore: harden competition demo candidate`
  - `d673f00 chore: harden competition demo candidate`
  - `1e1d683 Add official A3 defense deck`
  - `c448132 Add static QA workflow and update delivery docs`
- 本轮继续原则：上传前只做质量门禁和安全扫描；如果发现 S0/S1 缺口再修复。
- 本轮验证：
  - `python -m py_compile backend/app/demo_main.py scripts/verify_p0_smoke.py scripts/deep_qa_check.py`：通过。
  - `node --check frontend-demo/app.js`：通过。
  - `python -m pytest -q backend/tests`：通过，4 passed，1 个 StarletteDeprecationWarning。
  - `python scripts/verify_p0_smoke.py`：通过，`=== ALL CHECKS PASSED ===`。
  - `python scripts/deep_qa_check.py`：通过，`=== DEEP QA PASSED ===`。
  - `npx playwright test`：通过，9 passed。
  - 候选提交文件安全扫描：通过，未发现用户 Spark Key、token、refresh token、`.env` 或日志密钥进入提交候选。
- 本轮结论：当前候选状态仍满足 GitHub 提交标准；本轮仅更新复核记录，无业务代码改动。

## 2026-06-10 第五次完成度审计

- 当前分支：`feat/product-workbench-core-pipeline`。
- 恢复时未提交修改：无。
- 最近提交：
  - `b5d37d3 chore: record github upload verification`
  - `1d3fb6d chore: harden competition demo candidate`
  - `2d02ace chore: harden competition demo candidate`
  - `d673f00 chore: harden competition demo candidate`
  - `1e1d683 Add official A3 defense deck`
  - `c448132 Add static QA workflow and update delivery docs`
  - `dd191d0 Strengthen gaoshu demo loop and deep QA`
  - `f310ddf Fit mindmap to preview viewport`
  - `6182214 Explain quiz mistakes inline and expand lectures`
  - `09d5884 Generate teaching-focused PPT markdown decks`
- 关键提交检查：
  - `18ede88 Fix learning artifact generation quality`：存在。
  - `09d5884 Generate teaching-focused PPT markdown decks`：存在。
- 本轮验证：
  - `python -m py_compile backend/app/demo_main.py scripts/verify_p0_smoke.py scripts/deep_qa_check.py`：通过。
  - `node --check frontend-demo/app.js`：通过。
  - `python -m pytest -q backend/tests`：通过，4 passed，1 个 StarletteDeprecationWarning。
  - `python scripts/verify_p0_smoke.py`：通过，`=== ALL CHECKS PASSED ===`。
  - `python scripts/deep_qa_check.py`：通过，`=== DEEP QA PASSED ===`。
  - `npx playwright test`：通过，9 passed。
  - 候选提交文件安全扫描：通过，未发现用户 Spark Key、token、refresh token、`.env` 或日志密钥进入提交候选。
  - 1366×768 浏览器验收：通过。页面无控制台错误、无横向溢出；一键演示后答案、课程依据、Agent 协作面板可见；点击生成思维导图后导图面板可见且无横向溢出。
- 本轮未重复消耗 Spark 额度；真实 Spark 连通性仍以此前单独测试记录为依据，提交文件中不保存 API Key。
- 本轮结论：当前候选状态满足“初赛可提交候选成品 + 人工最终验收”标准；本轮只新增完成度审计记录。

## 2026-06-10 第六次需求级收口审计

- 当前分支：`feat/product-workbench-core-pipeline`。
- 恢复时未提交修改：无。
- 最近提交：
  - `25065cf chore: harden competition demo candidate`
  - `b5d37d3 chore: record github upload verification`
  - `1d3fb6d chore: harden competition demo candidate`
  - `2d02ace chore: harden competition demo candidate`
  - `d673f00 chore: harden competition demo candidate`
  - `1e1d683 Add official A3 defense deck`
  - `c448132 Add static QA workflow and update delivery docs`
  - `dd191d0 Strengthen gaoshu demo loop and deep QA`
  - `f310ddf Fit mindmap to preview viewport`
  - `6182214 Explain quiz mistakes inline and expand lectures`
- 关键提交检查：
  - `18ede88 Fix learning artifact generation quality`：存在。
  - `09d5884 Generate teaching-focused PPT markdown decks`：存在。
- 本轮发现并修复：
  - `backend/app/demo_main.py`：`ask` 自动资源包的 5 类资源建议补齐 question/profile/citations/context_chunks/provider/model/fallback_used/used_rag/used_profile/created_at，满足资源卡片元信息一致性。
  - `backend/app/services/app_resource_service.py`：资源 metadata 不再硬编码 deepseek/deepseek-chat/used_rag=true，改用实际 provider/model/fallback/used_rag。
  - `backend/app/services/learning_report_service.py`：学习报告推荐从旧 AI 主题改为函数极限、左右极限、无穷小、连续、导数、积分等高数上主题。
- 本轮验证：
  - 运行态 ask 断言：通过。answer/citations/retrieved_chunks/student_profile/profile_delta/agent_traces/grounding/resource_package 均存在；5 类资源均带完整元信息；mock 风险等级为 medium。
  - 旧主题/硬编码扫描：通过。旧 AI 主题仅保留在文档“已不再使用旧主题”的说明中；资源服务不再硬编码 deepseek-chat。
  - `python -m py_compile backend/app/demo_main.py scripts/verify_p0_smoke.py scripts/deep_qa_check.py backend/app/services/app_resource_service.py backend/app/services/learning_report_service.py`：通过。
  - `node --check frontend-demo/app.js`：通过。
  - `python -m pytest -q backend/tests`：通过，4 passed，1 个 StarletteDeprecationWarning。
  - `python scripts/verify_p0_smoke.py`：通过，`=== ALL CHECKS PASSED ===`。
  - `python scripts/deep_qa_check.py`：通过，`=== DEEP QA PASSED ===`。
  - `npx playwright test`：通过，9 passed。
  - 1366×768 浏览器验收：通过。无控制台错误、无横向溢出；一键演示后答案/引用/Agent 面板可见；思维导图可见且无横向溢出。
  - 候选提交文件安全扫描：通过，未发现用户 Spark Key、token、refresh token、`.env` 或日志密钥进入提交候选。
- 本轮结论：修复了需求级审计发现的 S1/S2 残余问题，当前仍满足初赛提交候选标准。

## 2026-06-10 第三次恢复现场

- 当前分支：`feat/product-workbench-core-pipeline`。
- 恢复时未提交修改：无业务改动；本节为本次恢复记录。
- 最近提交：
  - `2d02ace chore: harden competition demo candidate`
  - `d673f00 chore: harden competition demo candidate`
  - `1e1d683 Add official A3 defense deck`
  - `c448132 Add static QA workflow and update delivery docs`
  - `dd191d0 Strengthen gaoshu demo loop and deep QA`
  - `f310ddf Fit mindmap to preview viewport`
  - `6182214 Explain quiz mistakes inline and expand lectures`
  - `09d5884 Generate teaching-focused PPT markdown decks`
  - `b3b7e94 Export PPT resources as readable markdown decks`
  - `4535d04 Personalize learning path and profile updates`
- 关键提交检查：
  - `18ede88 Fix learning artifact generation quality`：存在。
  - `09d5884 Generate teaching-focused PPT markdown decks`：存在。
- 本轮继续原则：只做候选状态复核；如果验证发现 S0/S1 缺口再窄修。
- 本轮验证：
  - `python -m py_compile backend/app/demo_main.py scripts/verify_p0_smoke.py scripts/deep_qa_check.py`：通过。
  - `node --check frontend-demo/app.js`：通过。
  - `python -m pytest -q backend/tests`：通过，4 passed，1 个 StarletteDeprecationWarning。
  - `python scripts/verify_p0_smoke.py`：通过，`=== ALL CHECKS PASSED ===`。
  - `python scripts/deep_qa_check.py`：通过，`=== DEEP QA PASSED ===`。
  - `npx playwright test`：通过，9 passed。
  - 候选提交文件安全扫描：通过，未发现用户 Spark Key、token、refresh token、`.env` 或日志密钥进入提交候选。
- 本轮结论：当前候选状态仍满足初赛提交候选标准；本轮无 S0/S1 新缺口。
