#!/bin/bash
# 蒲剧数字活化平台 · 一键启动（macOS双击运行）
# 首次运行会自动创建虚拟环境并安装依赖，之后秒开

cd "$(dirname "$0")" || exit 1

# 检查 Python3
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ 未找到 python3，请先安装 Python（https://www.python.org/downloads/）"
  echo "按任意键退出..."
  read -n 1
  exit 1
fi

# 首次运行：创建虚拟环境 + 装依赖
if [ ! -d "venv" ]; then
  echo "🔧 首次运行：创建虚拟环境并安装依赖（约1~3分钟，只需一次）..."
  python3 -m venv venv || exit 1
  ./venv/bin/pip install -q --upgrade pip
  ./venv/bin/pip install -q -r requirements.txt || { echo "❌ 依赖安装失败，请检查网络后重新双击本文件"; read -n 1; exit 1; }
fi

# 依赖完整性预检：缺组件时自动补装（离线检查，秒级）
if ! ./venv/bin/python -c "import fastapi, uvicorn, sqlalchemy, jwt, multipart, jieba, dotenv, PIL, requests" 2>/dev/null; then
  echo "📦 检测到缺少依赖组件，正在自动补装..."
  ./venv/bin/pip install -q -r requirements.txt || { echo "❌ 依赖补装失败，请检查网络后重试"; read -n 1; exit 1; }
fi

# 清理残留的旧网站进程（避免端口占用导致启动失败）
if lsof -ti:8000 >/dev/null 2>&1; then
  echo "🧹 检测到8000端口被占用（可能是上次的网站还没关），正在自动清理..."
  pkill -f "uvicorn app.api.main" 2>/dev/null
  sleep 1
fi

echo ""
echo "================================================"
echo "  🎭 蒲韵 · 蒲剧数字活化平台 正在启动..."
echo ""
echo "  网址: http://localhost:8000"
echo "  （浏览器会自动打开；若提示无法访问，等2秒刷新一下）"
echo ""
echo "  ⚠️ 浏览网站期间，请保持本窗口开着不要关！"
echo "     停止网站: 回到本窗口按 Ctrl+C，或直接关闭本窗口"
echo "================================================"
echo ""

# 等网站真正就绪后再打开浏览器（最多等30秒）
(
  for i in $(seq 1 60); do
    if curl -s -o /dev/null "http://127.0.0.1:8000/api/health" 2>/dev/null; then
      echo ""
      echo "✅✅✅ 网站已就绪！正在打开浏览器... ✅✅✅"
      echo "   （若浏览器没有自动打开，手动访问 http://localhost:8000）"
      open "http://localhost:8000"
      exit 0
    fi
    sleep 0.5
  done
  echo ""
  echo "⚠️ 等待30秒后网站仍未就绪，请把本窗口显示的文字复制发给开发者排查"
) &

./venv/bin/python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000

# 如果走到这里说明网站已停止
echo ""
echo "网站已停止。重新双击本文件即可再次启动。"
read -n 1
