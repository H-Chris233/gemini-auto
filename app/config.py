"""
配置管理模块
从环境变量加载配置，支持默认值
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    应用配置类
    使用 Pydantic Settings 进行环境变量管理
    """

    # ========== 服务器 API 配置 ==========
    API_HOST: str = "请输入你的服务器API地址"
    ADMIN_KEY: str = "请输入你的管理员密钥"

    # ========== 临时邮箱 API 配置 ==========
    MAIL_API: str = "https://mail.chatgpt.org.uk"
    MAIL_KEY: str = "gpt-test"

    # ========== 浏览器配置 ==========
    HEADLESS_MODE: bool = True
    CONCURRENT_TASKS: int = 1

    # ========== 服务器配置 ==========
    LISTEN_PORT: int = 8080
    LOG_LEVEL: str = "INFO"

    # ========== 文件路径配置 ==========
    ACCOUNTS_FILE: str = "accounts.json"
    ERROR_LOG_FILE: str = "errors.log"

    class Config:
        env_prefix = "GEMINI_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例
    使用 lru_cache 避免重复加载
    """
    return Settings()


# 页面元素定位
XPATH = {
    "email_input": "/html/body/c-wiz/div/div/div[1]/div/div/div/form/div[1]/div[1]/div/span[2]/input",
    "continue_btn": "/html/body/c-wiz/div/div/div[1]/div/div/div/form/div[2]/div/button",
    "verify_btn": "/html/body/c-wiz/div/div/div[1]/div/div/div/form/div[2]/div/div[1]/span/div[1]/button",
}

# Gemini 登录页面
LOGIN_URL = "https://auth.business.gemini.google/login?continueUrl=https:%2F%2Fbusiness.gemini.google%2F&wiffid=CAoSJDIwNTlhYzBjLTVlMmMtNGUxZS1hY2JkLThmOGY2ZDE0ODM1Mg"

# 随机姓名池
NAMES = [
    "James Smith", "John Johnson", "Robert Williams", "Michael Brown", "William Jones",
    "David Garcia", "Mary Miller", "Patricia Davis", "Jennifer Rodriguez", "Linda Martinez",
    "Elizabeth Taylor", "Richard Moore", "Susan Wilson", "Joseph Anderson", "Jessica Thomas",
    "Charles Jackson", "Sarah White", "Christopher Harris", "Karen Martin", "Daniel Thompson",
    "Thomas Garcia", "Nancy Martinez", "Matthew Robinson", "Lisa Clark", "Anthony Lewis",
    "Betty Walker", "Mark Young", "Margaret Allen", "Donald King", "Sandra Wright"
]
