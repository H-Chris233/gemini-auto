#!/bin/bash
set -e

echo "[Gemini Auto] 容器启动中..."

# 设置环境变量默认值
export GEMINI_LISTEN_PORT=${GEMINI_LISTEN_PORT:-8080}
export GEMINI_BACKEND_PORT=${GEMINI_BACKEND_PORT:-8081}
export GEMINI_HEADLESS_MODE=${GEMINI_HEADLESS_MODE:-true}
export GEMINI_CONCURRENT_TASKS=${GEMINI_CONCURRENT_TASKS:-1}

echo "[Gemini Auto] 监听端口: $GEMINI_LISTEN_PORT"
echo "[Gemini Auto] 后端端口: $GEMINI_BACKEND_PORT"
echo "[Gemini Auto] Headless 模式: $GEMINI_HEADLESS_MODE"

# 确保目录存在
mkdir -p /app/static /app/run /app/log

# 渲染 Nginx 配置
NGINX_TEMPLATE="/etc/nginx/conf.d/default.conf.template"
NGINX_CONF="/etc/nginx/conf.d/default.conf"
if [ -f "$NGINX_TEMPLATE" ]; then
  echo "[Gemini Auto] 渲染 Nginx 监听端口..."
  sed "s/{{GEMINI_LISTEN_PORT}}/${GEMINI_LISTEN_PORT}/g; s/{{GEMINI_BACKEND_PORT}}/${GEMINI_BACKEND_PORT}/g" "$NGINX_TEMPLATE" > "$NGINX_CONF"
fi

# 启动 FastAPI (后台运行)
echo "[Gemini Auto] 启动 FastAPI 服务..."
cd /app
uvicorn app.main:app --host 0.0.0.0 --port "$GEMINI_BACKEND_PORT" &
UVICORN_PID=$!

# 等待 FastAPI 启动
sleep 3

# 启动 Nginx (前台运行)
echo "[Gemini Auto] 启动 Nginx..."
exec nginx -g "daemon off;"
