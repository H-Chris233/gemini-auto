"""
账号管理路由
"""

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.account import Account, AccountUpload, AccountStats


router = APIRouter(prefix="/accounts", tags=["账号管理"])

# 账号文件路径
ACCOUNTS_FILE = "accounts.json"


def load_accounts() -> List[dict]:
    """加载本地账号文件"""
    if not Path(ACCOUNTS_FILE).exists():
        return []
    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_accounts(accounts: List[dict]):
    """保存账号到文件"""
    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)


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


@router.post("/upload")
async def upload_accounts(upload: AccountUpload):
    """
    上传账号配置
    mode: replace (覆盖) 或 merge (合并)
    """
    if upload.mode == "replace":
        # 覆盖模式：直接保存
        account_list = [acc.model_dump() for acc in upload.accounts]
        save_accounts(account_list)
        return {"message": f"已覆盖保存 {len(account_list)} 个账号", "count": len(account_list)}

    elif upload.mode == "merge":
        # 合并模式：保留远程正常账号
        remote_accounts = load_accounts()
        local_ids = {acc.get('id') for acc in upload.accounts}
        remote_valid = []

        beijing_tz = timezone(timedelta(hours=8))
        now = datetime.now(beijing_tz)

        for acc in remote_accounts:
            if acc.get('disabled', False):
                continue

            expires_at = acc.get('expires_at')
            if expires_at and expires_at != '未设置':
                try:
                    expire_time = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                    if expire_time.replace(tzinfo=beijing_tz) <= now:
                        continue
                except Exception:
                    pass

            if acc.get('id') not in local_ids:
                remote_valid.append(acc)

        # 合并
        merged = remote_valid + [acc.model_dump() for acc in upload.accounts]
        save_accounts(merged)

        return {
            "message": f"合并完成，新增 {len(upload.accounts)} 个，保留 {len(remote_valid)} 个远程有效账号",
            "count": len(merged),
        }

    else:
        raise HTTPException(status_code=400, detail="无效的上传模式")


@router.delete("/{email}")
async def delete_account(email: str):
    """
    删除单个账号
    """
    accounts = load_accounts()
    original_count = len(accounts)

    accounts = [acc for acc in accounts if acc.get('id') != email]

    if len(accounts) == original_count:
        raise HTTPException(status_code=404, detail="账号不存在")

    save_accounts(accounts)
    return {"message": f"已删除账号: {email}"}


@router.post("/clear")
async def clear_accounts():
    """
    清空所有账号
    """
    save_accounts([])
    return {"message": "已清空所有账号"}
