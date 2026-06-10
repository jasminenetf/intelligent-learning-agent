# 初赛提交清单

## 必交材料

- [ ] GitHub 仓库地址：`https://github.com/jasminenetf/intelligent-learning-agent`
- [ ] README.md：启动、API 配置、一键演示、验证命令
- [ ] RUNBOOK.md：故障排查、E2E、smoke、deep QA
- [ ] DEMO_SCRIPT_7MIN.md：录屏讲解脚本
- [ ] AI_CODING_USAGE.md：AI Coding 使用说明
- [ ] OSS_LICENSES.md：开源组件说明
- [ ] 答辩 PPT：`docs/presentation/中国软件杯A3_高数智能助教答辩.pptx`

## 提交前本地验证

```powershell
python -m py_compile backend/app/demo_main.py
node --check frontend-demo/app.js
python -m pytest -q backend/tests
python scripts/verify_p0_smoke.py
python scripts/deep_qa_check.py
cd tests/e2e
npx playwright test
```

## 人工验收路径

- [ ] 双击 `启动智能学习Agent.bat`
- [ ] 打开 `http://127.0.0.1:5173`
- [ ] 设置页填写 Spark APIPassword 并测试连接
- [ ] 无 Key 时确认显示 Mock/fallback，且标注“本地演示兜底”
- [ ] 进入会话中心，提问函数极限标准问题
- [ ] 检查回答、引用、retrieved chunks、画像、Agent 轨迹、基础可信度
- [ ] 自动出现 5 类资源：讲义、思维导图/知识树、练习题、学习路径、Markdown PPT
- [ ] 思维导图可滚动、可全屏、可切 Mermaid 备份
- [ ] 故意选错题，原地显示详细解析和错因
- [ ] 查看学习报告：正确率、错题数、薄弱点、推荐资源、下一步操作
- [ ] 运行一键演示按钮，失败时有可读状态或错误提示
- [ ] 检查浏览器控制台无明显 ReferenceError/TypeError

## 安全检查

- [ ] 不提交 `.env`
- [ ] 不提交真实 API Key、token、refresh token、日志密钥
- [ ] 不提交 `data/`、`outputs/`、Chroma、本地日志、大 PDF
- [ ] Mock、fallback、hash_mock、基础 Verifier 均诚实标注

## 当前结论模板

结论选择：

- A：已达到初赛提交候选标准，但需人工最终验收。
- B：基本可演示，但仍有阻断。
- C：不适合提交。
