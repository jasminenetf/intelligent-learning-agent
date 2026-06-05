# Demo 操作清单 + 应急方案

---

## 启动命令

```bash
# 终端1: 后端 (必须先启动)
cd /home/zhang/projects/intelligent-learning-agent/backend
source ../.venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 终端2: 前端
cd /home/zhang/projects/intelligent-learning-agent/frontend-demo
python -m http.server 5173
# 浏览器: http://127.0.0.1:5173
```

---

## 登录账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin_ocr | admintest123 | admin |

---

## 课程 ID

`2` — 高等数学上（已有课程资料和 chunks）

```bash
# 确认课程存在
curl http://127.0.0.1:8000/api/courses
```

---

## 演示前健康检查

```bash
# 1. 后端存活
curl http://127.0.0.1:8000/health
# → {"status":"ok"}

# 2. DeepSeek 状态
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_ocr","password":"admintest123"}' | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/llm/status
# → is_mock必须为false, deepseek_configured为true

# 3. RAG 有数据
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/rag/status
# → vector_count > 0

# 4. 画像存在
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/profiles/me
# → 返回 profile 对象
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

### DeepSeek 超时
- 现象: 资源生成卡住超过30秒
- 方案: 刷新页面，重试。如持续超时，用 mock 模式演示流程，口头说明真 LLM 能力
- 检查: `curl http://127.0.0.1:8000/api/llm/status`

### Token 过期
- 现象: API 返回 401
- 方案: 重新点击"登录"按钮

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
- 方案: `fuser -k 8000/tcp` 然后重启

---

## 演示后清理

```bash
# 停止服务
Ctrl+C (两个终端各一次)

# 确认端口释放
fuser 8000/tcp
fuser 5173/tcp
```
