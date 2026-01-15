# Gemini Auto Web

Gemini Business 自动注册工具 - Web 版

## 功能特性

- 🌐 Web UI 操作界面
- 🚀 单 Docker 镜像部署
- 📊 实时任务监控
- 📋 账号管理
- ⚙️ 环境变量配置

## 快速开始

### 本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装 Node 依赖并构建前端
cd frontend
npm install
npm run build
cd ..

# 3. 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

访问 http://localhost:8080

### Docker 构建运行

```bash
# 构建镜像
docker build -t gemini-auto:latest .

# 运行容器
docker run -d \
  --name gemini-auto \
  -p 8080:8080 \
  -e GEMINI_API_HOST="https://your-api-server.com" \
  -e GEMINI_ADMIN_KEY="your-admin-key-here" \
  -e GEMINI_MAIL_API="https://mail.chatgpt.org.uk" \
  -e GEMINI_MAIL_KEY="gpt-test" \
  -e GEMINI_HEADLESS_MODE="true" \
  -v $(pwd)/data:/app/data \
  gemini-auto:latest

# 查看日志
docker logs -f gemini-auto

# 停止容器
docker stop gemini-auto && docker rm gemini-auto
```

## 环境变量

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `GEMINI_API_HOST` | 是 | - | 服务器 API 地址 |
| `GEMINI_ADMIN_KEY` | 是 | - | 管理员密钥 |
| `GEMINI_MAIL_API` | 否 | `https://mail.chatgpt.org.uk` | 临时邮箱 API |
| `GEMINI_MAIL_KEY` | 否 | `gpt-test` | 邮箱 API 密钥 |
| `GEMINI_HEADLESS_MODE` | 否 | `true` | 浏览器无头模式 |
| `GEMINI_CONCURRENT_TASKS` | 否 | `1` | 并发任务数 |
| `GEMINI_LISTEN_PORT` | 否 | `8080` | Web 服务端口 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| POST | /api/tasks | 启动注册任务 |
| GET | /api/tasks/{id} | 查询任务状态 |
| DELETE | /api/tasks/{id} | 停止任务 |
| GET | /api/tasks/{id}/logs | SSE 日志流 |
| GET | /api/accounts | 账号列表 |
| GET | /api/accounts/stats | 账号统计 |
| DELETE | /api/accounts/{email} | 删除账号 |

## 项目结构

```
gemini-auto/
├── app/                    # FastAPI 后端
│   ├── main.py            # 应用入口
│   ├── config.py          # 配置管理
│   ├── api/               # API 路由
│   ├── worker/            # 注册任务逻辑
│   └── schemas/           # 数据模型
├── frontend/              # Vue3 前端
│   ├── src/
│   │   ├── api/           # API 封装
│   │   ├── components/    # 通用组件
│   │   └── views/         # 页面视图
│   └── vite.config.js
├── nginx/                 # Nginx 配置
├── scripts/               # 启动脚本
├── requirements.txt
└── Dockerfile
```

## License

MIT
