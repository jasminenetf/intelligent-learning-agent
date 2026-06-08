# Demo 操作清单 + 应急方案

---

## 启动命令

```bash
# 终端1: 后端 (必须先启动)
cd C:\Users\zhang\Desktop\智能学习\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 终端2: 前端
cd C:\Users\zhang\Desktop\智能学习\frontend-demo
python -m http.server 5173
# 浏览器: http://127.0.0.1:5173
```

---

## 登录状态

当前答辩 Demo 使用免登录体验。正式注册/登录和角色权限作为后续安全加固项，不作为当前演示依赖。

---

## 课程 ID

`2` — 高等数学上（已有课程资料和 chunks）

```powershell
# 确认课程存在
curl http://127.0.0.1:8000/api/courses
```

---

## 演示前健康检查

```powershell
# 1. 后端存活
curl http://127.0.0.1:8000/health
# → {"status":"ok"}

# 2. 模型状态
curl http://127.0.0.1:8000/api/settings/status
# → 推荐显示 spark；无密钥时允许 deepseek/mock fallback 验证工程链路

# 3. RAG 有数据
curl http://127.0.0.1:8000/api/app/bootstrap
# → vector_count > 0
```

---

## 演示主题

| 用途 | topic |
|------|-------|
| 默认演示 | 导数与极限入门 |
| 备用 | 函数极限 |
| 演示PPT | 高等数学导数入门 |

---

## 演示问题

| 用途 | question |
|------|---------|
| 默认RAG | 根据课程资料解释导数和函数变化率的关系 |
| 备用 | 函数极限的定义是什么 |

---

## 应急方案

### Spark / fallback 模型超时
- 现象: 资源生成卡住超过30秒
- 方案: 刷新页面，重试。如持续超时，用 mock 模式演示流程，口头说明 Spark 为主引擎，fallback 用于工程稳定性
- 检查: `curl http://127.0.0.1:8000/api/settings/status`

### course_id 不存在
- 现象: 返回 404
- 方案: 检查 `curl http://127.0.0.1:8000/api/courses`，使用实际存在的 ID

### 前端无法连接后端
- 现象: 状态栏显示"未连接"，API 返回 Network Error
- 方案: 
  1. 检查后端是否在 8000 端口运行
  2. 浏览器打开 http://127.0.0.1:8000/health 测试
  3. 检查 CORS 是否生效

### PPT 下载失败
- 现象: 点击下载无反应或 404
- 方案: 
  1. 重新生成 PPT（resource_id 可能过期）
  2. 检查 backend/data/generated/ 目录

### Mermaid 不渲染
- 现象: 只显示 Mermaid 源码文本
- 方案: 
  1. 检查网络能否访问 cdn.jsdelivr.net
  2. 展示 Mermaid 源码文本，口头说明渲染效果

### 后端端口被占用
- 现象: `address already in use`
- 方案: 执行 `停止智能学习Agent.bat`，或在任务管理器中结束占用 8000 端口的 Python 进程，然后重启

---

## 演示后清理

```powershell
cd C:\Users\zhang\Desktop\智能学习
.\停止智能学习Agent.bat
```
