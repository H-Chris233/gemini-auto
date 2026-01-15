"""
账号上传模块
将本地账号上传到远程服务器
"""

import json
import requests
from typing import Optional
from pathlib import Path

from app.config import get_settings


class AccountUploader:
    """账号上传管理类"""

    def __init__(self, api_host: str = "", admin_key: str = ""):
        """
        初始化上传器

        Args:
            api_host: 远程服务器地址
            admin_key: 管理员密钥
        """
        self.api_host = api_host.rstrip('/') if api_host else ""
        self.admin_key = admin_key
        self.session = requests.Session()

    def _log(self, msg: str, level: str = "INFO"):
        """日志输出"""
        icons = {"INFO": "→", "WARN": "⚠", "ERROR": "✗", "OK": "✓"}
        icon = icons.get(level, "•")
        print(f"{icon} {msg}")

    def login(self) -> bool:
        """登录到远程服务器"""
        if not self.api_host:
            self._log("未配置远程服务器地址", "WARN")
            return False

        login_url = f"{self.api_host}/login"

        try:
            response = self.session.post(
                login_url,
                data={"admin_key": self.admin_key},
                allow_redirects=True,
                timeout=30
            )

            if len(self.session.cookies) > 0:
                self._log("远程服务器连接成功", "OK")
                return True

            if response.status_code == 200 and '登录' in response.text:
                self._log("远程服务器密钥验证失败", "ERROR")
                return False

            self._log("远程服务器连接失败", "ERROR")
            return False

        except Exception as e:
            self._log(f"连接远程服务器异常: {e}", "ERROR")
            return False

    def _load_local_accounts(self, file_path: str) -> list:
        """加载本地账号文件"""
        if not Path(file_path).exists():
            self._log(f"本地文件不存在 → {file_path}", "ERROR")
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self._log(f"读取本地文件失败: {e}", "ERROR")
            return []

    def upload(self, file_path: str, mode: str = "merge") -> dict:
        """
        上传账号到远程服务器

        Args:
            file_path: 本地账号文件路径
            mode: 上传模式 (replace/merge)

        Returns:
            上传结果字典
        """
        # 检查配置
        if not self.api_host:
            return {"success": False, "message": "未配置远程服务器地址"}

        if not self.admin_key:
            return {"success": False, "message": "未配置管理员密钥"}

        # 加载本地账号
        local_accounts = self._load_local_accounts(file_path)
        if not local_accounts:
            return {"success": False, "message": "本地无账号数据"}

        self._log(f"本地账号 → {len(local_accounts)} 个")

        # 登录远程服务器
        if not self.login():
            return {"success": False, "message": "远程服务器登录失败"}

        if mode == "replace":
            return self._upload_replace(local_accounts)
        else:
            return self._upload_merge(local_accounts)

    def _upload_replace(self, local_accounts: list) -> dict:
        """覆盖上传"""
        upload_url = f"{self.api_host}/accounts-config"

        try:
            response = self.session.put(
                upload_url,
                json=local_accounts,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                self._log(f"覆盖上传成功! 共 {len(local_accounts)} 个账号", "OK")
                return {
                    "success": True,
                    "message": result.get('message', '配置已更新'),
                    "count": len(local_accounts),
                }
            else:
                self._log(f"上传失败, 状态码: {response.status_code}", "ERROR")
                return {"success": False, "message": f"上传失败: {response.status_code}"}

        except Exception as e:
            self._log(f"上传异常: {e}", "ERROR")
            return {"success": False, "message": str(e)}

    def _upload_merge(self, local_accounts: list) -> dict:
        """合并上传 (保留远程正常账号)"""
        # 获取远程账号配置
        config_url = f"{self.api_host}/accounts-config"

        remote_accounts = []
        try:
            response = self.session.get(config_url, timeout=30)
            if response.status_code == 200:
                remote_config = response.json()
                remote_accounts = remote_config.get('accounts', [])
                self._log(f"远程账号 → {len(remote_accounts)} 个")
        except Exception as e:
            self._log(f"获取远程配置失败: {e}", "WARN")
            remote_accounts = []

        # 筛选远程正常账号
        from datetime import datetime, timezone, timedelta
        valid_remote = []
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
                except:
                    pass
            valid_remote.append(acc)

        self._log(f"有效远程账号 → {len(valid_remote)} 个")

        # 合并账号
        merged = list(valid_remote)
        remote_ids = {acc.get('id') for acc in valid_remote}
        new_count = 0

        for local_acc in local_accounts:
            local_id = local_acc.get('id')
            if local_id not in remote_ids:
                merged.append(local_acc)
                new_count += 1

        self._log(f"合并结果 → 保留 {len(valid_remote)} 个, 新增 {new_count} 个, 共 {len(merged)} 个")

        # 上传合并后的配置
        upload_url = f"{self.api_host}/accounts-config"

        try:
            response = self.session.put(
                upload_url,
                json=merged,
                timeout=30
            )

            if response.status_code == 200:
                self._log(f"合并上传成功! 共 {len(merged)} 个账号", "OK")
                return {
                    "success": True,
                    "message": f"新增 {new_count} 个, 保留 {len(valid_remote)} 个远程有效账号",
                    "count": len(merged),
                }
            else:
                self._log(f"合并上传失败: {response.status_code}", "ERROR")
                return {"success": False, "message": f"上传失败: {response.status_code}"}

        except Exception as e:
            self._log(f"上传异常: {e}", "ERROR")
            return {"success": False, "message": str(e)}


def upload_to_remote(api_host: str = "", admin_key: str = "", mode: str = "merge") -> dict:
    """
    便捷函数：上传本地账号到远程服务器

    从环境变量读取配置
    """
    settings = get_settings()

    # 使用传入参数或环境变量
    api_host = api_host or settings.UPLOAD_API_HOST
    admin_key = admin_key or settings.UPLOAD_ADMIN_KEY
    mode = mode or settings.UPLOAD_MODE

    if not api_host:
        return {"success": False, "message": "未配置远程服务器地址 (GEMINI_UPLOAD_API_HOST)"}

    if not admin_key:
        return {"success": False, "message": "未配置管理员密钥 (GEMINI_UPLOAD_ADMIN_KEY)"}

    uploader = AccountUploader(api_host, admin_key)
    accounts_file = settings.ACCOUNTS_FILE

    return uploader.upload(accounts_file, mode)
