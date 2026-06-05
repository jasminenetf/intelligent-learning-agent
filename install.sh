#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  智能学习Agent — 一键安装脚本
#  支持：Linux / macOS / WSL (Windows Subsystem for Linux)
#  用法：bash install.sh
# ═══════════════════════════════════════════════════════════════

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend-demo"
SEED_DIR="$ROOT/seed"
VENV_DIR="$ROOT/.venv"
PYTHON_MIN="3.10"

# ── 颜色 ──────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; }
title() { echo -e "\n${CYAN}══════════════════════════════════════════${NC}"; echo -e "${BLUE}  $1${NC}"; echo -e "${CYAN}══════════════════════════════════════════${NC}\n"; }

echo ""
title "智能学习Agent — 一键安装"

# ── 1. 检查 Python ──────────────────────────────────────────
echo "检测 Python 环境..."
PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$cmd"
            info "找到 Python $ver ($(command -v "$cmd"))"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    err "需要 Python >= 3.10，未找到。请先安装 Python。"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  macOS:         brew install python@3.12"
    echo "  Windows:       https://www.python.org/downloads/"
    exit 1
fi

# ── 2. 创建虚拟环境 ────────────────────────────────────────
echo ""
echo "创建虚拟环境..."
if [ -d "$VENV_DIR" ]; then
    warn "虚拟环境已存在，跳过创建。如需重新创建请删除 $VENV_DIR"
else
    "$PYTHON" -m venv "$VENV_DIR"
    info "虚拟环境创建完成"
fi

source "$VENV_DIR/bin/activate"

# ── 3. 升级 pip ─────────────────────────────────────────────
echo ""
echo "升级 pip..."
"$PYTHON" -m pip install --upgrade pip -q
info "pip 已升级"

# ── 4. 安装依赖 ─────────────────────────────────────────────
echo ""
echo "安装 Python 依赖（可能需要几分钟）..."
pip install -r "$BACKEND_DIR/requirements.txt" -q
info "所有依赖安装完成"

# ── 5. 复制 .env 配置文件 ──────────────────────────────────
echo ""
echo "配置环境变量..."
if [ -f "$BACKEND_DIR/.env" ]; then
    warn ".env 已存在，跳过。如需重新生成请删除 backend/.env"
else
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    info ".env 已从 .env.example 创建"
fi

# ── 6. 创建必要目录 ─────────────────────────────────────────
mkdir -p "$ROOT/data/raw" "$ROOT/data/chroma" "$ROOT/data/generated"
info "数据目录已就绪"

# ── 7. 种子演示数据 ─────────────────────────────────────────
echo ""
echo "初始化演示数据..."
if [ -f "$SEED_DIR/demo_knowledge.txt" ]; then
    mkdir -p "$ROOT/data/raw/2"
    cp "$SEED_DIR/demo_knowledge.txt" "$ROOT/data/raw/2/高数上_demo_knowledge.txt"
fi

# 运行种子脚本
if [ -f "$SEED_DIR/seed_demo.py" ]; then
    cd "$ROOT"
    python "$SEED_DIR/seed_demo.py" 2>&1 | while IFS= read -r line; do
        echo "  $line"
    done
    info "演示数据初始化完成"
else
    warn "种子脚本未找到，跳过演示数据初始化"
fi

# ── 8. 完成 ─────────────────────────────────────────────────
echo ""
title "安装完成！"

echo "下一步："
echo ""
echo -e "  ${YELLOW}1. 配置 DeepSeek API Key${NC}"
echo "     编辑 backend/.env，填入你的 API Key："
echo -e "     ${CYAN}DEEPSEEK_API_KEY=sk-你的Key${NC}"
echo ""
echo -e "  ${YELLOW}2. 启动应用${NC}"
echo -e "     ${GREEN}bash scripts/start_app.sh${NC}"
echo "     （Windows 用户双击 启动智能学习Agent.bat）"
echo ""
echo -e "  ${YELLOW}3. 打开浏览器${NC}"
echo "     http://127.0.0.1:5173"
echo ""
echo -e "  ${YELLOW}获取 DeepSeek API Key：${NC}"
echo "     https://platform.deepseek.com/api_keys"
echo "     新用户赠送 500 万 tokens，足够体验"
echo ""

# 自动打开浏览器
AUTO_OPEN="${1:-yes}"
if [ "$AUTO_OPEN" != "no" ]; then
    echo "按 Enter 立即启动应用（Ctrl+C 跳过）..."
    read -r
    echo ""
    bash "$ROOT/scripts/start_app.sh"
fi
