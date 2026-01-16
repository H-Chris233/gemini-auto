"""
配置管理模块
从环境变量加载配置，支持默认值
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    应用配置类
    使用 Pydantic Settings 进行环境变量管理
    """

    # ========== 远程上传配置 ==========
    # 任务完成后自动上传到远程服务器（配置了地址就上传）
    UPLOAD_API_HOST: str = ""  # 远程服务器地址
    UPLOAD_ADMIN_KEY: str = ""  # 远程管理员密钥
    UPLOAD_MODE: str = "merge"  # 上传模式: replace (覆盖) 或 merge (合并)

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

    model_config = SettingsConfigDict(
        env_prefix="GEMINI_",
        case_sensitive=False,  # 环境变量不区分大小写
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            cls._legacy_env_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    @staticmethod
    def _legacy_env_settings():
        legacy_env_map = {
            "UPLOAD_API_HOST": "GEMINI_API_HOST",
            "UPLOAD_ADMIN_KEY": "GEMINI_ADMIN_KEY",
        }
        values = {}
        for field_name, env_name in legacy_env_map.items():
            env_value = os.getenv(env_name)
            if env_value:
                values[field_name] = env_value
        return values


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
LOGIN_URL = "https://auth.business.gemini.google/login?continueUrl=https://business.gemini.google/home/cid/ea35f5ea-6cdf-4a83-a370-e1e9c6dc6975?csesidx%3D355873723%26mods&wiffid=CAoSJDVlZGI3MjIwLTgzOTQtNGIyMy05NzUxLWRmOTdhNTEzNDMyNg"

# 随机姓名池
NAMES = [
    "James Smith", "John Johnson", "Robert Williams", "Michael Brown", "William Jones",
    "David Garcia", "Mary Miller", "Patricia Davis", "Jennifer Rodriguez", "Linda Martinez",
    "Elizabeth Taylor", "Richard Moore", "Susan Wilson", "Joseph Anderson", "Jessica Thomas",
    "Charles Jackson", "Sarah White", "Christopher Harris", "Karen Martin", "Daniel Thompson",
    "Thomas Garcia", "Nancy Martinez", "Matthew Robinson", "Lisa Clark", "Anthony Lewis",
    "Betty Walker", "Mark Young", "Margaret Allen", "Donald King", "Sandra Wright"
]
