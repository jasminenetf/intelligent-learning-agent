# 运行手册 — 智能学习Agent系统

## 环境要求
- Docker 24+ + Docker Compose v2（当前环境未安装，部署前装好）
- Python 3.10+（本地开发）
- 科大讯飞 Spark API 凭证（APP_ID、API_KEY、API_SECRET）

## 快速启动

### 本地开发
```bash
cd /home/zhang/projects/intelligent-learning-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend

# 验证
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/version
```

### Docker 启动（Docker 安装后）
```bash
# 安装 Docker（Ubuntu/WSL）
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
# 重新登录后：
docker compose up -d --build
curl http://127.0.0.1:8000/health
```

### Docker 停止
```bash
docker compose down
```

## API 验证 curl

### 注册
```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"student1","email":"s@ex.com","password":"12345678","role":"student"}'
```

### 登录
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"student1","password":"12345678"}'
```

### 获取当前用户
```bash
TOKEN="<from login response>"
curl http://127.0.0.1:8000/api/auth/me -H "Authorization: Bearer $TOKEN"
```

## 常用命令

```bash
# 查看日志
docker compose logs -f backend

# 重启单个服务
docker compose restart backend

# 进入后端容器
docker compose exec backend bash

# 数据库迁移
docker compose exec backend python -m app.db.migrate
```

## 目录结构
```
project-root/
├── frontend/        # LobeChat 配置
├── backend/
│   ├── app/
│   │   ├── api/     # FastAPI 路由
│   │   ├── agents/  # LangGraph Agent 节点
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
| Spark API 调用失败 | 检查 .env 凭证是否正确，API 额度是否耗尽 |
| ChromaDB 无法连接 | `docker compose restart chroma` |
| Presenton 生成失败 | 检查 Presenton 容器日志，确认 API 密钥 |
| 向量检索无结果 | 确认已上传教材并构建索引 |
| 端口冲突 | 修改 docker-compose.yml 中的端口映射 |

## 开发模式
```bash
# 后端热重载
cd backend && uvicorn app.main:app --reload --port 8000

# 仅启动基础设施（不启动后端）
docker compose up -d chroma postgres redis minio
```
