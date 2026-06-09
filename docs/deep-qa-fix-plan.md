# 深度检验与正常使用修复长任务清单

更新时间：2026-06-08

## 正常使用目标

- 双击 `启动智能学习Agent.bat` 后能稳定打开前端。
- 用户无需登录，直接填写 Spark / DeepSeek API Key 或使用 Mock fallback。
- 会话问答、课程资料、知识库、资源生成、思维导图、练习题、PPT、学习路径、错题本、学习报告、画像、资源中心都能点击使用。
- GitHub 项目不提交真实密钥、数据库、Chroma 数据、日志、大型本地资源。

## 本轮检验结论

已通过：

- `python -m py_compile`：核心后端文件语法通过。
- `node --check frontend-demo/app.js`：前端 JS 语法通过。
- `app.demo_main:app` 和 `app.main:app` 均可启动并通过 `/health`。
- `scripts/verify_p0_smoke.py`：
  - demo 后端：全部通过。
  - main 后端：P0 通过，种子课程 RAG 问答带引用通过。
- 前端浏览器导航检查：设置、首页、会话、课程、资源生成、资源中心、错题本、学习报告、画像、知识库均无错误卡片和空白页。
- 前端交互检查：快捷生成思维导图、练习题、讲义、PPT、多资源生成器均可用。
- 学习路径页可生成 4 步学习计划。
- `.env`、数据库、Chroma、日志、`.codex/`、大型 OCR 语言包均被 `.gitignore` 忽略。

发现问题：

- P0-1：`scripts/start_app.sh` 曾启动 `app.main:app` 的 `8000`，但 `frontend-demo/app.js` 默认请求 `8010`。已对齐为 `app.demo_main:app` + `8010`。
- P0-2：`README.md`、`RUNBOOK.md`、`frontend-demo/README.md` 曾混用 `8000/app.main` 和 `8010/app.demo_main`。已统一当前 Demo 启动说明。
- P0-3：`install.bat` 安装后提示曾指向不清。已明确下一步启动 `启动智能学习Agent.bat`。
- P1-1：正式后端 `app.main` 的资源生成链路偏慢，单资源约 25 秒，复习计划约 40 秒；功能可用但用户会以为卡住。
- P1-2：`pytest` 当前没有测试用例，质量门禁空转。
- P1-3：`tests/e2e` 声明 Playwright 测试，但依赖未安装时 `npm test` 直接失败，缺少一键安装/CI 说明。
- P1-4：`app.main` 导入时 LangGraph 提示节点 `config` 参数类型应使用 `RunnableConfig`，不影响运行但需要清理。
- P1-5：学习路径快捷按钮会跳到独立隐藏页面，功能正常但用户路径感弱；建议在侧边栏增加入口或在助手预览区同步显示。
- P1-6：root `.env.example` 曾有重复 `SPARK_API_KEY`，且 `ADMIN_ENABLED=true` 不适合公开模板。已修正为 `SPARK_API_PASSWORD` 和 `ADMIN_ENABLED=false`。
- P1-7：demo 下载接口目前统一下载 `.txt`，PPT 资源可预览但下载不是 `.pptx`，答辩演示可接受，正式体验需升级。

## 修复长任务清单

### P0：必须修到正常使用

- [x] 统一启动端口和入口。
  - Windows：继续使用 `app.demo_main:app` + `8010` + `5173`。
  - Linux/WSL：将 `scripts/start_app.sh` 改为同样启动 `app.demo_main:app` + `8010`，或让前端可通过环境/配置指定 `8000`。
  - 验收：`bash scripts/start_app.sh` 后前端所有接口请求不再打到错误端口。

- [x] 修正文档启动说明。
  - `README.md`：明确“答辩/朋友运行”使用 `启动智能学习Agent.bat`。
  - `RUNBOOK.md`：手动启动命令改成当前 demo 入口，另列正式后端入口作为开发模式。
  - `frontend-demo/README.md`：后端端口改为 `8010` 或补充 API Base 配置。
  - 验收：新用户只看 README 就能启动页面并点问答。

- [x] 修正安装脚本文案。
  - `install.bat` 安装完成后提示双击 `启动智能学习Agent.bat`。
  - `install.sh` 完成后给出 Windows / Linux 对应启动方式。
  - 验收：安装后的下一步不会误导用户继续双击安装器。

- [x] 增加一键启动健康检查。
  - 启动后自动请求 `/health` 和前端首页。
  - 后端启动失败时窗口输出明确原因，例如缺少依赖、端口占用、Python 不存在。
  - 验收：失败不再只闪退或卡住。

- [x] 复跑 P0 验证。
  - `python -m py_compile ...`
  - `node --check frontend-demo/app.js`
  - `P0_SMOKE_BASE=http://127.0.0.1:8010 python scripts/verify_p0_smoke.py`
  - 浏览器点击设置、首页、会话、资源生成、资源中心、错题本、学习报告、画像、知识库。

### P1：提升真实可用性

- [ ] 优化正式后端资源生成耗时。
  - 将 `/api/resources/generate` 和 `/api/analytics/review-plan` 改为真正异步 job 或前端显示长耗时进度。
  - 设置明确超时和 fallback，不让用户等待 25-40 秒无反馈。
  - 验收：首屏 1 秒内显示任务已创建，最终结果可轮询获取。

- [x] 补齐后端基础测试门禁。
  - 新增后端 pytest：auth 免登录、settings、ask、generate、resources、learning-report。
  - 前端最小 E2E 仍在 P1 队列中，需先安装 Playwright 依赖。
  - 验收：`pytest` 不再显示 `no tests ran`。

- [ ] 修复 E2E 依赖安装路径。
  - 为 `tests/e2e` 增加 `package-lock.json` 或根级脚本。
  - 文档增加 `npm install` / `npx playwright install` 步骤。
  - 验收：`npm --prefix tests/e2e test` 可执行。

- [ ] 清理 LangGraph 类型警告。
  - 将相关节点函数 `config` 标注为 `RunnableConfig | None`。
  - 验收：`python -c "import app.main"` 不再提示类型警告。

- [ ] 优化学习路径入口。
  - 侧边栏增加“学习路径”入口，或让助手右侧学习路径 tab 直接显示步骤。
  - 验收：用户点击“学习路径”后能明确看到跳转目标和步骤内容。

- [x] 规范 `.env.example`。
  - 去掉重复 `SPARK_API_KEY`。
  - root 模板 `ADMIN_ENABLED` 默认改为 `false`。
  - 统一 Spark 推荐字段为 `SPARK_API_PASSWORD`。
  - 验收：敏感扫描只命中文档示例，不出现真实或误导性配置。

- [ ] 升级 demo 下载文件格式。
  - 讲义下载 Markdown/TXT。
  - 思维导图下载 `.mmd` 或 `.md`。
  - 练习题下载 `.json` 或 `.md`。
  - PPT 下载 `.pptx`。
  - 验收：资源中心下载文件类型和资源类型一致。

### P2：答辩稳定性与项目观感

- [ ] 将本轮深检命令固化成 `scripts/deep_qa_check.py`。
- [ ] 增加 GitHub Actions：语法检查、smoke、敏感文件检查。
- [x] 整理 README 中 “一键演示” 和当前真实按钮名称，避免写不存在的按钮。
- [ ] 固化种子课程：首次启动自动提供“人工智能导论 - 演示课程”。
- [ ] 增加 API 设置页的连接失败解释，不只显示泛化错误。
- [ ] 把正式后端和 demo 后端的职责写入 `DECISIONS.md`，避免后续又混淆入口。
- [ ] 清理或说明本地 OCR 语言包路径，避免用户误以为需要上传大文件。
- [ ] 对资源中心增加空态演示入口：没有资源时一键生成默认资源包。

## 下一步建议

先修 P0-1 到 P0-4。它们是“别人拿到项目能不能正常启动”的核心问题。P1/P2 再继续抛光，不要反过来先做复杂架构。
