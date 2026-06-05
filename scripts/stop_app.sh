#!/bin/bash
# 智能学习Agent — 停止脚本

echo "Stopping Intelligent Learning Agent..."
fuser -k 8000/tcp 2>/dev/null && echo "  Backend stopped (port 8000)" || echo "  Backend not running"
fuser -k 5173/tcp 2>/dev/null && echo "  Frontend stopped (port 5173)" || echo "  Frontend not running"
echo "Done."
