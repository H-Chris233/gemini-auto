"""
工具函数模块
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional


def setup_logger(name: str = "gemini-auto") -> logging.Logger:
    """
    配置日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 控制台处理器
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)

    return logger


def format_timestamp(ts: str) -> str:
    """
    格式化时间戳为可读格式
    """
    if not ts:
        return "未设置"

    try:
        # 尝试解析常见格式
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"]:
            try:
                dt = datetime.strptime(ts.replace("+00:00", ""), fmt.replace("%z", ""))
                # 转换为北京时间
                dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
        return ts
    except Exception:
        return ts
