"""
健康检查路由
"""

from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    uptime: float


router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    健康检查接口
    用于 K8s livenessProbe 和负载均衡健康检测
    """
    from app.main import startup_time, version

    import time
    uptime = time.time() - startup_time

    return {
        "status": "healthy",
        "version": version,
        "uptime": uptime,
    }
