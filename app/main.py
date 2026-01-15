"""
FastAPI 主应用入口
"""

import time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import HTTPException

from app.api import health_router, tasks_router, accounts_router, config_router
from app.config import get_settings


# 全局变量
startup_time = time.time()
version = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时初始化，关闭时清理
    """
    # 启动时
    print("[Gemini Auto] 服务启动中...")

    settings = get_settings()
    print(f"[Gemini Auto] 监听端口: {settings.LISTEN_PORT}")
    print(f"[Gemini Auto] Headless 模式: {settings.HEADLESS_MODE}")

    yield

    # 关闭时
    print("[Gemini Auto] 服务正在关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title="Gemini Auto Web",
    description="Gemini Business 自动注册工具 Web 版",
    version=version,
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(accounts_router)
app.include_router(config_router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
ASSETS_DIR = STATIC_DIR / "assets"
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/", include_in_schema=False)
def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="index.html not found")

# API 前缀兼容 (/api/*)
app.include_router(health_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(accounts_router, prefix="/api")
app.include_router(config_router, prefix="/api")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例
    用于 uvicorn 启动
    """
    return app


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.LISTEN_PORT,
        reload=False,
    )
