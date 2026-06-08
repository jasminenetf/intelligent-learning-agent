# 运行手册 — 智能学习Agent系统

## 环境要求
- Windows / PowerShell（当前主开发与答辩环境）
- Python 3.10+
- 可选：Docker 24+ + Docker Compose v2（仅用于 PostgreSQL / Redis / MinIO 基础设施）
- 科大讯飞 Spark API 凭证（推荐配置 APIPassword）
- 可选：DeepSeek API Key（开发 fallback）

## 快速启动

### Windows 本地 Demo
```powershell
cd C:\Users\zhang\Desktop\智能学习
.\启动智能学习Agent.bat

# 验证
curl http://127.0.0.1:8010/health
curl http://127.0.0.1:8010/api/version
```

前端默认地址：
```text
http://127.0.0.1:5173
```

后端默认地址：
```text
http://127.0.0.1:8010
```

### 手动启动当前免登录 Demo 后端
```powershell
cd C:\Users\zhang\Desktop\智能学习\backend
python -m pip install -r requirements.txt
python -m uvicorn app.demo_main:app --host 127.0.0.1 --port 8010 --reload
```

### 手动启动前端
```powershell
cd C:\Users\zhang\Desktop\智能学习\frontend-demo
python -m http.server 5173
```

### 可选基础设施
```powershell
cd C:\Users\zhang\Desktop\智能学习
docker compose up -d postgres redis minio
```

### 停止
```powershell
cd C:\Users\zhang\Desktop\智能学习
.\停止智能学习Agent.bat
```

## API 验证 curl

当前答辩 Demo 以免登录体验为主。旧 `/api/auth/register`、`/api/auth/login` 接口处于兼容/禁用状态；正式认证和角色权限属于后续安全加固项。

### 健康检查
```powershell
curl http://127.0.0.1:8010/health
curl http://127.0.0.1:8010/api/version
curl http://127.0.0.1:8010/api/app/bootstrap
```

## 常用命令

```bash
# P0 smoke
python scripts/verify_p0_smoke.py

# 初始化演示数据
python scripts/seed_demo_data.py

# 可选：启动基础设施
docker compose up -d postgres redis minio
```

## 目录结构
```
project-root/
├── frontend-demo/   # 当前答辩 Demo 前端
├── backend/
│   ├── app/
│   │   ├── api/     # FastAPI 路由
│   │   ├── services/# 业务逻辑
│   │   ├── models/  # ORM 模型
│   │   └── main.py  # 入口
│   └── Dockerfile
├── data/            # 上传文件、向量库持久化
├── scripts/         # 工具脚本
├── docker-compose.yml
└── docs/            # 文档
```

## 故障排查

| 问题 | 解决 |
|------|------|
| Spark API 调用失败 | 检查 `backend/.env` 中 Spark APIPassword、模型名和额度 |
| DeepSeek 调用失败 | 检查 `backend/.env` 中 DeepSeek Key、模型权限和余额 |
| ChromaDB 无结果 | 确认已上传教材、已解析出知识片段并重建索引 |
| PPT 下载失败 | 检查 `data/generated/` 和 `/api/resources/generated` |
| 向量检索无结果 | 确认已上传教材并构建索引 |
| 端口冲突 | 修改 docker-compose.yml 中的端口映射 |

## 开发模式
```powershell
# 正式后端开发热重载
cd C:\Users\zhang\Desktop\智能学习\backend
python -m uvicorn app.main:app --reload --port 8000

# 仅启动基础设施
cd C:\Users\zhang\Desktop\智能学习
docker compose up -d postgres redis minio
```
