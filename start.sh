#!/bin/bash
# AI + PQC 演示系统一键启动脚本

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ">>> 安装 Python 依赖..."
pip install -r "$ROOT/requirements.txt" -q

echo ">>> 安装前端依赖..."
cd "$ROOT/frontend" && npm install

echo ""
echo "=========================================="
echo "  AI + PQC 安全监控系统"
echo "=========================================="
echo "  后端 API:  http://127.0.0.1:8000"
echo "  前端界面:  http://127.0.0.1:5173"
echo "=========================================="
echo ""
echo "请在两个终端分别运行："
echo "  终端1: cd $ROOT && python api.py"
echo "  终端2: cd $ROOT/frontend && npm run dev"
echo ""
