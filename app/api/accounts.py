"""
账号管理路由
仅提供账号查看功能，账号由注册任务自动生成
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List
from fastapi import APIRouter

from app.schemas.account import Account, AccountStats
from app.config import get_settings


router = APIRouter(prefix="/accounts", tags=["账号管理"])


def load_accounts() -> List[dict]:
    """加载本地账号文件"""
    settings = get_settings()
    accounts_file = settings.ACCOUNTS_FILE or "accounts.json"
    if not Path(accounts_file).exists():
        return []
    try:
        with open(accounts_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


@router.get("/", response_model=List[Account])
async def list_accounts():
    """
    获取账号列表
    """
    accounts = load_accounts()
    return [Account(**acc) for acc in accounts]


@router.get("/stats", response_model=AccountStats)
async def get_account_stats():
    """
    获取账号统计信息
    """
    accounts = load_accounts()
    now = datetime.now(timezone(timedelta(hours=8)))

    active = 0
    disabled_count = 0
    expired = 0

    for acc in accounts:
        if acc.get('disabled', False):
            disabled_count += 1
            continue

        expires_at = acc.get('expires_at')
        if expires_at and expires_at != '未设置':
            try:
                expire_time = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                if expire_time.replace(tzinfo=timezone(timedelta(hours=8))) <= now:
                    expired += 1
                    continue
            except Exception:
                pass

        active += 1

    return AccountStats(
        total=len(accounts),
        active=active,
        disabled=disabled_count,
        expired=expired,
    )
