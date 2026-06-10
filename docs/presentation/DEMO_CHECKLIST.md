# Demo 操作清单与应急方案

当前答辩主线：`高数上`课程智能助教。演示目标是证明系统能完成：

`提问 -> 教材检索 -> 可信回答 -> 自动生成学习资源 -> 做题反馈 -> 错题复盘 -> 画像更新 -> 学习路径调整`

## 启动方式

推荐直接双击项目根目录：

```text
启动智能学习Agent.bat
```

手动启动时使用当前 Demo 入口：

```powershell
cd C:\Users\zhang\Desktop\智能学习\backend
python -m uvicorn app.demo_main:app --host 127.0.0.1 --port 8010

cd C:\Users\zhang\Desktop\智能学习\frontend-demo
python -m http.server 5173
```

浏览器访问：

```text
http://127.0.0.1:5173
```

后端健康检查：

```powershell
curl http://127.0.0.1:8010/health
```

## 演示前检查

```powershell
python -m py_compile backend/app/demo_main.py
node --check frontend-demo/app.js
$env:P0_SMOKE_BASE='http://127.0.0.1:8010'
python scripts/verify_p0_smoke.py
python scripts/deep_qa_check.py
```

`deep_qa_check.py` 会检查：

- 语法检查
- P0 smoke
- 问答后是否出现 5 类资源建议
- 导图、练习、讲义、学习路径、Markdown PPT 是否可生成
- 下载文件是否包含教材依据和 Verifier
- 答错题是否原地反馈并写入错题闭环
- 明显密钥泄露扫描

## 推荐演示问题

```text
我不懂函数极限，讲清定义、常见误区，并给一个例题
```

备用问题：

```text
请根据教材解释导数的几何意义和物理意义
```

```text
我对定积分和不定积分总是混淆，请用例题讲清楚
```

## 必须展示的页面和证据

| 页面 | 展示点 |
|---|---|
| 设置页 | Spark / Mock 状态，真实模型失败时能自动 fallback |
| 会话中心 | 提问后自动出现导图、练习、讲义、学习路径、PPT 文本版 |
| 右侧依据 | 教材引用、grounding、风险等级、内容安全 |
| Agent 轨迹 | Tutor / Informer / Profile / Verifier 等协作步骤 |
| 思维导图 | 默认可读知识树，支持全屏和 Mermaid 备份 |
| 练习题 | 题目绑定当前问题，答错后原地详细讲解 |
| 画像中心 | 六维画像、证据来源、置信度、历史版本 |
| 学习路径 | 每步有原因、资源、预计时间、练习任务、检验标准 |
| 资源中心 | `.md` 下载可打开，文件内含教材依据和 Verifier |
| 学习报告 | 掌握度、错因、薄弱点、下一步推荐 |

## 应急方案

### Spark Key 不可用或 401

现象：顶部显示 `Mock`，回答中出现真实模型失败原因。

处理：

- 继续演示本地课程 fallback，说明它用于节省额度和保证答辩稳定。
- 如需验证真实 Key，只在设置页执行一次连接测试。
- 系统有失败缓存，坏 Key 不会反复拖慢资源生成。

### 首次提问等待数秒

原因：系统会短时间尝试真实模型，失败后进入本地课程 fallback。

处理：

- 等待一次即可。
- 后续资源生成会明显变快。

### 导图看不全

当前默认已改为可读知识树。若仍需展示原图：

- 点击 `Mermaid备份`。
- 点击 `全屏/退出` 展示大图结构。

### 资源下载失败

处理：

- 到资源中心刷新。
- 重新生成对应资源。
- 确认后端 `http://127.0.0.1:8010/health` 正常。

### 端口占用

```powershell
.\停止智能学习Agent.bat
```

或手动查看：

```powershell
Get-NetTCPConnection -LocalPort 8010 -State Listen
```

## 演示后清理

```powershell
cd C:\Users\zhang\Desktop\智能学习
.\停止智能学习Agent.bat
```
