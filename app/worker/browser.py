"""
浏览器管理模块
处理 Chrome 浏览器初始化和清理
"""

import time
import random
from typing import Optional
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from app.config import get_settings, XPATH, LOGIN_URL


class BrowserManager:
    """
    浏览器管理器
    负责 Chrome 的启动、关闭和状态检查
    """

    def __init__(self):
        self.settings = get_settings()
        self.driver: Optional[uc.Chrome] = None
        self._consecutive_fails = 0
        self._MAX_CONSECUTIVE_FAILS = 20

    def ensure_driver(self) -> bool:
        """
        确保浏览器可用
        如果浏览器关闭或异常，则重启
        """
        if self.driver is None:
            return self._create_driver()

        try:
            # 检查浏览器是否还活着
            _ = self.driver.current_url
            return True
        except Exception:
            print("[Browser] 检测到浏览器异常，准备重启...")
            self._cleanup()
            return self._create_driver()

    def _create_driver(self) -> bool:
        """
        创建新的 Chrome 浏览器实例
        """
        try:
            options = uc.ChromeOptions()

            if self.settings.HEADLESS_MODE:
                options.add_argument("--headless=new")

            # 基础配置
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--window-size=1200,800")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")

            # 创建浏览器
            self.driver = uc.Chrome(options=options, use_subprocess=True)

            # 设置窗口位置（如果是 GUI 模式）
            if not self.settings.HEADLESS_MODE:
                self.driver.set_window_size(100, 200)
                self.driver.set_window_position(50, 50)

            time.sleep(1)
            self._consecutive_fails = 0
            print("[Browser] 浏览器启动成功")
            return True

        except Exception as e:
            print(f"[Browser] 浏览器启动失败: {e}")
            self._consecutive_fails += 1
            return False

    def _cleanup(self):
        """
        清理浏览器资源
        """
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None

    def reset_for_new_account(self):
        """
        重置浏览器状态，准备注册新账号
        """
        if self.driver:
            try:
                self.driver.delete_all_cookies()
            except Exception:
                pass

        # 随机延迟，避免被检测
        time.sleep(random.uniform(2, 3))

    def close(self):
        """
        关闭浏览器
        """
        self._cleanup()

    @property
    def is_available(self) -> bool:
        """
        检查浏览器是否可用
        """
        if self.driver is None:
            return False

        try:
            _ = self.driver.current_url
            return True
        except Exception:
            return False

    @property
    def consecutive_fails(self) -> int:
        """
        获取连续失败次数
        """
        return self._consecutive_fails

    def increment_fails(self):
        """
        记录一次失败
        """
        self._consecutive_fails += 1

    def reset_fails(self):
        """
        重置失败计数
        """
        self._consecutive_fails = 0

    def get_driver(self):
        """
        获取 driver 实例
        """
        return self.driver
