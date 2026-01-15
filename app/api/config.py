"""
配置路由
"""

from fastapi import APIRouter
from pydantic import BaseModel


class ConfigResponse(BaseModel):
    """配置响应"""
    mail_api: str
    mail_key_set: bool  # 是否已设置
    headless_mode: bool
    concurrent_tasks: int
    version: str


router = APIRouter(prefix="/config", tags=["配置管理"])


@router.get("/", response_model=ConfigResponse)
async def get_config():
    """
    获取当前配置（敏感信息不返回）
    """
    from app.config import get_settings, MAIL_API
    from app.main import version

    settings = get_settings()

    return {
        "mail_api": MAIL_API,
        "mail_key_set": bool(settings.MAIL_KEY and settings.MAIL_KEY != "gpt-test"),
        "headless_mode": settings.HEADLESS_MODE,
        "concurrent_tasks": settings.CONCURRENT_TASKS,
        "version": version,
    }
