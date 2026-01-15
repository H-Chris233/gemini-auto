"""
账号管理路由
提供账号查看/上传/删除/清空等功能
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException

from app.schemas.account import Account, AccountStats, AccountUpload, AccountsResponse
from app.config import get_settings
from app.utils.uploader import fetch_remote_accounts


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


def save_accounts(accounts: List[dict]) -> None:
    """保存账号到本地文件"""
    settings = get_settings()
    accounts_file = settings.ACCOUNTS_FILE or "accounts.json"
    Path(accounts_file).parent.mkdir(parents=True, exist_ok=True)
    with open(accounts_file, 'w', encoding='utf-8') as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)


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
async def upload_accounts(payload: AccountUpload):
    """
    上传账号配置 (replace/merge)
    """
    mode = payload.mode or "replace"
    incoming_accounts = [acc.model_dump() for acc in payload.accounts]

    if mode not in {"replace", "merge"}:
        raise HTTPException(status_code=400, detail="不支持的上传模式")

    if mode == "replace":
        save_accounts(incoming_accounts)
        return {"message": "账号配置已覆盖", "count": len(incoming_accounts)}

    existing_accounts = load_accounts()
    existing_ids = {acc.get("id") for acc in existing_accounts}
    merged_accounts = list(existing_accounts)
    new_count = 0

    for account in incoming_accounts:
        if account.get("id") not in existing_ids:
            merged_accounts.append(account)
            new_count += 1

    save_accounts(merged_accounts)
    return {
        "message": "账号配置已合并",
        "count": len(merged_accounts),
        "new_count": new_count,
    }


@router.get("/remote", response_model=AccountsResponse)
async def get_remote_accounts():
    """
    获取远程账号列表
    """
    result = fetch_remote_accounts()
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "远程账号获取失败"))

    accounts = [Account(**acc) for acc in result.get("accounts", [])]
    total = result.get("total", len(accounts))
    return {"accounts": accounts, "total": total}


@router.delete("/{email}")
async def delete_account(email: str):
    """
    删除指定账号
    """
    accounts = load_accounts()
    remaining_accounts = [acc for acc in accounts if acc.get("id") != email]

    if len(remaining_accounts) == len(accounts):
        raise HTTPException(status_code=404, detail="账号不存在")

    save_accounts(remaining_accounts)
    return {"message": "账号已删除", "count": len(remaining_accounts)}


@router.post("/clear")
async def clear_accounts():
    """
    清空所有账号
    """
    save_accounts([])
    return {"message": "账号已清空", "count": 0}
