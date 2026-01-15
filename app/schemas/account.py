"""
账号相关数据模型
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class Account(BaseModel):
    """账号模型"""
    id: str = Field(description="账号 ID (邮箱)")
    csesidx: str = Field(description="会话索引")
    config_id: str = Field(description="配置 ID")
    secure_c_ses: str = Field(description="安全会话 Cookie")
    host_c_oses: str = Field(description="主机 Cookie")
    expires_at: Optional[str] = Field(None, description="过期时间")
    status: str = Field(default="active", description="账号状态")
    disabled: bool = Field(default=False, description="是否禁用")
    conversation_count: int = Field(default=0, description="累计对话数")
    remaining_display: Optional[str] = Field(None, description="剩余额度显示")

    class Config:
        from_attributes = True


class AccountCreate(BaseModel):
    """账号创建/上传模型"""
    id: str = Field(description="账号 ID (邮箱)")
    csesidx: Optional[str] = Field(None, description="会话索引")
    config_id: Optional[str] = Field(None, description="配置 ID")
    secure_c_ses: Optional[str] = Field(None, description="安全会话 Cookie")
    host_c_oses: Optional[str] = Field(None, description="主机 Cookie")
    expires_at: Optional[str] = Field(None, description="过期时间")
    status: str = Field(default="active", description="账号状态")
    disabled: bool = Field(default=False, description="是否禁用")
    conversation_count: int = Field(default=0, description="累计对话数")
    remaining_display: Optional[str] = Field(None, description="剩余额度显示")


class AccountUpload(BaseModel):
    """账号上传模型"""
    accounts: List[AccountCreate]
    mode: str = Field(default="replace", description="上传模式 (replace/merge)")


class AccountStats(BaseModel):
    """账号统计信息"""
    total: int
    active: int
    disabled: int
    expired: int
