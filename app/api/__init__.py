"""
API 路由模块
导出所有路由
"""

from .health import router as health_router
from .tasks import router as tasks_router
from .accounts import router as accounts_router
from .config import router as config_router

__all__ = [
    "health_router",
    "tasks_router",
    "accounts_router",
    "config_router",
]
