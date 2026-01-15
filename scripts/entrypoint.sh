#!/bin/bash
set -e

echo "[Gemini Auto] 容器启动中..."

# 设置环境变量默认值
export GEMINI_LISTEN_PORT=${GEMINI_LISTEN_PORT:-8080}
export GEMINI_HEADLESS_MODE=${GEMINI_HEADLESS_MODE:-true}
export GEMINI_CONCURRENT_TASKS=${GEMINI_CONCURRENT_TASKS:-1}

echo "[Gemini Auto] 监听端口: $GEMINI_LISTEN_PORT"
echo "[Gemini Auto] Headless 模式: $GEMINI_HEADLESS_MODE"

# 创建 Nginx 所需的目录 (需要 root 权限)
mkdir -p /var/lib/nginx/body /var/lib/nginx/proxy /var/lib/nginx/fastcgi /var/lib/nginx/uwsgi /var/lib/nginx/scgi

# 确保静态资源目录存在
mkdir -p /app/static

# 切换到 non-root 用户运行应用
echo "[Gemini Auto] 切换到 appuser 运行..."
exec su -s /bin/bash -c '
    # 启动 FastAPI (后台运行)
    echo "[Gemini Auto] 启动 FastAPI 服务..."
    cd /app
    uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    UVICORN_PID=$!

    # 等待 FastAPI 启动
    sleep 3

    # 启动 Nginx (前台运行)
    echo "[Gemini Auto] 启动 Nginx..."
    exec nginx -g "daemon off;"
' appuser
