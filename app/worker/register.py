"""
注册任务模块
从原 gemini-auto.py 迁移的核心注册逻辑
"""

import json
import time
import random
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
import re
import threading

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from app.config import (
    get_settings, XPATH, LOGIN_URL, NAMES,
)
from app.worker.browser import BrowserManager


def print_log(msg: str, level: str = "INFO"):
    """统一日志输出"""
    icons = {"INFO": "→", "WARN": "⚠", "ERROR": "✗", "OK": "✓"}
    icon = icons.get(level, "•")
    log_msg = f"{icon} {msg}"
    print(log_msg)
    return log_msg


def log_error(email: str, error_msg: str, error_file: str = "errors.log"):
    """记录错误到日志文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] 邮箱: {email} | 错误: {error_msg}\n"

    try:
        with open(error_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"[WARN] 写入错误日志失败: {e}")


def create_temp_email() -> str:
    """创建临时邮箱地址"""
    settings = get_settings()
    try:
        response = requests.get(
            f"{settings.MAIL_API}/api/generate-email",
            headers={"X-API-Key": settings.MAIL_KEY},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('data'):
                return data['data']['email']
    except Exception as e:
        print(f"[ERROR] 邮箱服务异常: {e}")
    return None


def prefetch_email(email_queue: list):
    """预创建邮箱并加入队列"""
    email = create_temp_email()
    if email:
        email_queue.append(email)
        print(f"[INFO] 预创建邮箱: {email}")


def get_email(email_queue: list) -> str:
    """获取邮箱地址"""
    if email_queue:
        email = email_queue.pop(0)
        print_log(f"邮箱就绪 → {email}", "OK")
        return email

    email = create_temp_email()
    if email:
        print_log(f"已生成 → {email}", "OK")
    return email


def fetch_verification_code(email: str, timeout: int = 60) -> str:
    """获取邮箱验证码"""
    settings = get_settings()
    print_log("等待邮件验证码...")
    start_time = time.time()
    code_pattern = re.compile(r"\b(\d{6})\b")

    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"{settings.MAIL_API}/api/emails",
                params={"email": email},
                headers={"X-API-Key": settings.MAIL_KEY},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                emails = data.get('data', {}).get('emails', [])
                if emails:
                    html_content = emails[0].get('html_content') or emails[0].get('content', '')
                    soup = BeautifulSoup(html_content, 'html.parser')
                    code_element = soup.find('span', class_='verification-code')

                    if code_element:
                        code = code_element.get_text().strip()
                        if len(code) == 6:
                            print_log(f"验证码 → {code}", "OK")
                            return code
                    # 兜底: 从正文文本提取 6 位验证码
                    text_content = soup.get_text(" ", strip=True)
                    match = code_pattern.search(text_content) or code_pattern.search(html_content)
                    if match:
                        code = match.group(1)
                        print_log(f"验证码 → {code}", "OK")
                        return code
        except Exception:
            pass

        elapsed = int(time.time() - start_time)
        print(f"  等待中... ({elapsed}s)", end='\r')
        time.sleep(2)

    print_log("验证码超时,请检查网络", "ERROR")
    return None


def fast_type(element, text: str, delay: float = 0.02):
    """快速输入文本"""
    for c in text:
        element.send_keys(c)
        time.sleep(delay)


def save_account_config(email: str, driver, timeout: int = 10) -> dict:
    """提取并保存账号配置信息"""
    settings = get_settings()
    print_log(f"提取账号配置中(最多 {timeout}s)...")
    start_time = time.time()
    account_data = None
    accounts_file = settings.ACCOUNTS_FILE

    while time.time() - start_time < timeout:
        try:
            cookies = driver.get_cookies()
            current_url = driver.current_url
            parsed_url = urlparse(current_url)

            # 提取 config_id
            url_parts = current_url.split('/')
            config_id = None
            for i, part in enumerate(url_parts):
                if part == 'cid' and i + 1 < len(url_parts):
                    config_id = url_parts[i + 1].split('?')[0]
                    break

            # 提取关键 cookies
            cookie_map = {c['name']: c for c in cookies}
            session_cookie = cookie_map.get('__Secure-C_SES', {})
            host_cookie = cookie_map.get('__Host-C_OSES', {})

            # 提取 csesidx
            csesidx = parse_qs(parsed_url.query).get('csesidx', [None])[0]

            # 验证所有必需字段
            if all([
                session_cookie.get('value'),
                host_cookie.get('value'),
                csesidx,
                config_id
            ]):
                expiry_timestamp = session_cookie.get('expiry', 0) - 43200
                expires_at = datetime.fromtimestamp(expiry_timestamp).strftime('%Y-%m-%d %H:%M:%S') if expiry_timestamp > 0 else None

                account_data = {
                    "id": email,
                    "csesidx": csesidx,
                    "config_id": config_id,
                    "secure_c_ses": session_cookie.get('value'),
                    "host_c_oses": host_cookie.get('value'),
                    "expires_at": expires_at
                }

                elapsed = time.time() - start_time
                print_log(f"配置提取完成 ({elapsed:.1f}s)", "OK")
                break

        except Exception as e:
            print(f"[ERROR] 提取配置异常: {e}")

        time.sleep(1)

    if not account_data:
        print_log(f"配置不完整,已跳过 → {email}", "WARN")
        return None

    # 保存到文件
    existing_accounts = []
    if Path(accounts_file).exists():
        try:
            with open(accounts_file, 'r', encoding='utf-8') as f:
                existing_accounts = json.load(f)
        except Exception as e:
            print(f"[ERROR] 读取账号文件失败: {e}")

    existing_accounts.append(account_data)

    with open(accounts_file, 'w', encoding='utf-8') as f:
        json.dump(existing_accounts, f, indent=2, ensure_ascii=False)

    print_log(f"已保存 → {accounts_file}", "OK")
    return account_data


def register_single_account(browser: BrowserManager, email: str) -> dict:
    """注册单个账号"""
    start_time = time.time()
    driver = browser.get_driver()

    if not driver:
        return {"email": email, "success": False, "elapsed": 0}

    wait = WebDriverWait(driver, 30)

    try:
        # 1. 访问登录页
        driver.get(LOGIN_URL)
        time.sleep(2)

        page_source = driver.page_source
        if len(page_source) < 500 or "about:blank" in driver.current_url:
            raise Exception("页面加载空白，需要重启浏览器")

        # 2. 输入邮箱
        print_log("输入邮箱...")
        inp = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH["email_input"])))
        inp.click()
        inp.clear()
        fast_type(inp, email)

        # 验证输入
        time.sleep(0.3)
        actual_value = inp.get_attribute("value")
        if actual_value != email:
            print_log(f"输入验证失败，清空后重新输入...", "WARN")
            driver.execute_script("arguments[0].value = '';", inp)
            time.sleep(0.1)
            driver.execute_script("arguments[0].value = arguments[1];", inp, email)
            driver.execute_script("""
                var event = new Event('input', { bubbles: true });
                arguments[0].dispatchEvent(event);
            """, inp)
            time.sleep(0.3)

        print_log(f"邮箱 → {email}", "OK")

        # 3. 点击继续
        time.sleep(0.5)
        btn = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH["continue_btn"])))
        driver.execute_script("arguments[0].click();", btn)
        print_log("继续下一步", "OK")

        # 4. 获取验证码
        time.sleep(2)
        code = fetch_verification_code(email)
        if not code:
            return {"email": email, "success": False, "elapsed": time.time() - start_time}

        # 5. 输入验证码
        time.sleep(1)
        print_log(f"输入验证码 → {code}")
        try:
            pin = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='pinInput']")))
            pin.click()
            time.sleep(0.1)
            fast_type(pin, code, 0.05)
        except Exception:
            try:
                span = driver.find_element(By.CSS_SELECTOR, "span[data-index='0']")
                span.click()
                time.sleep(0.2)
                driver.switch_to.active_element.send_keys(code)
            except Exception as e:
                print_log(f"验证码输入失败: {e}", "ERROR")
                return {"email": email, "success": False, "elapsed": time.time() - start_time}

        # 6. 点击验证
        time.sleep(0.5)
        try:
            vbtn = driver.find_element(By.XPATH, XPATH["verify_btn"])
            driver.execute_script("arguments[0].click();", vbtn)
        except Exception:
            for btn in driver.find_elements(By.TAG_NAME, "button"):
                if '验证' in btn.text:
                    driver.execute_script("arguments[0].click();", btn)
                    break
        print_log("提交验证", "OK")

        # 7. 输入姓名
        print_log("等待姓名输入...")
        selectors = [
            "input[formcontrolname='fullName']",
            "input[placeholder='全名']",
            "input[placeholder='Full name']",
            "input#mat-input-0",
        ]
        name_inp = None

        for _ in range(30):
            for sel in selectors:
                try:
                    name_inp = driver.find_element(By.CSS_SELECTOR, sel)
                    if name_inp.is_displayed():
                        break
                except:
                    continue
            if name_inp and name_inp.is_displayed():
                break
            time.sleep(1)

        if name_inp and name_inp.is_displayed():
            name = random.choice(NAMES)
            name_inp.click()
            time.sleep(0.2)
            name_inp.clear()
            fast_type(name_inp, name)
            print_log(f"姓名 → {name}", "OK")
            time.sleep(0.3)
            name_inp.send_keys(Keys.ENTER)
            time.sleep(1)
        else:
            print_log("未找到姓名输入框", "ERROR")
            return {"email": email, "success": False, "elapsed": time.time() - start_time}

        # 8. 等待进入工作台
        print_log("等待工作台...")
        for _ in range(30):
            time.sleep(1)
            url = driver.current_url
            if 'business.gemini.google' in url and '/cid/' in url:
                print_log("工作台加载完成", "OK")
                break
        else:
            print_log(f"未跳转到工作台 → {driver.current_url}", "WARN")

        # 9. 保存配置
        elapsed = time.time() - start_time
        config = save_account_config(email, driver)
        if config:
            print_log(f"注册成功 → {email} (耗时 {elapsed:.1f}s)", "OK")
            return {"email": email, "success": True, "config": config, "elapsed": elapsed}

        return {"email": email, "success": False, "elapsed": elapsed}

    except Exception as e:
        print_log(f"注册异常: {e}", "ERROR")
        log_error(email, str(e))
        return {"email": email, "success": False, "elapsed": time.time() - start_time}


def run_batch_registration(
    count: int,
    log_callback=None,
    progress_callback=None,
    stop_event: threading.Event | None = None,
) -> dict:
    """
    批量注册账号

    Args:
        count: 目标成功数量
        log_callback: 日志回调函数
        progress_callback: 进度回调函数

    Returns:
        注册结果统计
    """
    settings = get_settings()
    accounts_file = settings.ACCOUNTS_FILE

    # 清空旧文件
    if Path(accounts_file).exists():
        Path(accounts_file).unlink()
        print_log(f"已清空 → {accounts_file}")

    browser = BrowserManager()
    success_count = 0
    fail_count = 0
    attempt_count = 0
    total_time = 0
    success_times = []

    # 预创建第一个邮箱
    email_queue: list = []
    prefetch_email(email_queue)

    stop_requested = False

    while success_count < count:
        if stop_event and stop_event.is_set():
            stop_requested = True
            if log_callback:
                log_callback("任务停止标志已触发，准备退出注册循环")
            break
        # 检查浏览器可用性
        if not browser.ensure_driver():
            if browser.consecutive_fails >= browser._MAX_CONSECUTIVE_FAILS:
                print_log(f"连续失败 {browser._MAX_CONSECUTIVE_FAILS} 次，中止本轮任务", "ERROR")
                break

        attempt_count += 1

        print(f"\n{'=' * 60}")
        print(f"正在注册第 {attempt_count} 个账号 (成功: {success_count}/{count})")
        print(f"{'=' * 60}\n")

        # 获取邮箱
        email = get_email(email_queue)
        if not email:
            fail_count += 1
            browser.increment_fails()
            continue

        # 执行注册
        result = register_single_account(browser, email)

        elapsed = result.get("elapsed", 0)
        total_time += elapsed

        if result.get("success"):
            success_count += 1
            success_times.append(elapsed)
            browser.reset_fails()
            print_log(f"进度: {success_count}/{count} 完成", "OK")
        else:
            fail_count += 1
            browser.increment_fails()
            print_log(f"失败 +1 (连续失败: {browser.consecutive_fails}/{browser._MAX_CONSECUTIVE_FAILS})", "WARN")

        # 回调通知
        avg_time = total_time / attempt_count if total_time > 0 else 0
        if progress_callback:
            progress_callback({
                "success": success_count,
                "fail": fail_count,
                "total_time": total_time,
                "avg_time": avg_time,
                "message": f"已注册 {success_count}/{count}",
            })

        if log_callback:
            log_callback(f"第 {attempt_count} 个账号注册完成，成功: {result.get('success', False)}")

        # 准备下一个
        if success_count < count:
            if stop_event and stop_event.is_set():
                stop_requested = True
                if log_callback:
                    log_callback("任务停止标志已触发，跳过浏览器重置并结束任务")
                break
            browser.reset_for_new_account()
            prefetch_email(email_queue)

    # 清理浏览器
    browser.close()

    # 统计
    avg_time = sum(success_times) / len(success_times) if success_times else 0

    result = {
        "success": success_count,
        "fail": fail_count,
        "attempts": attempt_count,
        "total_time": total_time,
        "avg_time": avg_time,
        "is_ok": success_count > 0,
        "stopped": stop_requested,
    }

    print(f"\n{'=' * 60}")
    print(f"注册完成! 目标: {count}, 成功: {success_count}, 失败: {fail_count}, 总尝试: {attempt_count}")
    print(f"总耗时: {total_time:.1f}s | 平均: {avg_time:.1f}s")
    print(f"账号已保存至: {accounts_file}")
    print(f"{'=' * 60}")

    return result
