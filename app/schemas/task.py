"""
任务相关数据模型
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class TaskCreate(BaseModel):
    """创建任务请求模型"""
    count: int = Field(default=5, ge=1, le=100, description="要注册的账号数量")
    upload_mode: Optional[str] = Field(
        default=None,
        description="上传模式: replace (覆盖) 或 merge (合并)，为空则使用默认配置",
    )


class TaskResponse(BaseModel):
    """任务响应模型"""
    id: str
    status: TaskStatus
    count: int
    success_count: int = 0
    fail_count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskResult(BaseModel):
    """单个任务结果"""
    email: str
    success: bool
    config: Optional[dict] = None
    elapsed: float


class TaskLogs(BaseModel):
    """任务日志模型"""
    task_id: str
    timestamp: datetime
    level: str  # INFO, WARN, ERROR, OK
    message: str
