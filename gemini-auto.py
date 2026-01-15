"""
Gemini Business 自动注册上传工具
"""

# 标准库
import sys
import json
import time
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

# 第三方库
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ==================== 配置区域 ====================
# 服务器 API 配置
API_HOST = "请输入你的服务器API地址"
ADMIN_KEY = "请输入你的管理员密钥"

# 临时邮箱 API 配置
MAIL_API = "https://mail.chatgpt.org.uk"
MAIL_KEY = "gpt-test"

# Gemini 登录页面
LOGIN_URL = "https://auth.business.gemini.google/login?continueUrl=https:%2F%2Fbusiness.gemini.google%2F&wiffid=CAoSJDIwNTlhYzBjLTVlMmMtNGUxZS1hY2JkLThmOGY2ZDE0ODM1Mg"

# 本地账号文件
ACCOUNTS_FILE = "accounts.json"

# 页面元素定位
XPATH = {
    "email_input": "/html/body/c-wiz/div/div/div[1]/div/div/div/form/div[1]/div[1]/div/span[2]/input",
    "continue_btn": "/html/body/c-wiz/div/div/div[1]/div/div/div/form/div[2]/div/button",
    "verify_btn": "/html/body/c-wiz/div/div/div[1]/div/div/div/form/div[2]/div/div[1]/span/div[1]/button",
}

# 随机姓名池
NAMES = [
    "James Smith", "John Johnson", "Robert Williams", "Michael Brown", "William Jones",
    "David Garcia", "Mary Miller", "Patricia Davis", "Jennifer Rodriguez", "Linda Martinez",
    "Elizabeth Taylor", "Richard Moore", "Susan Wilson", "Joseph Anderson", "Jessica Thomas",
    "Charles Jackson", "Sarah White", "Christopher Harris", "Karen Martin", "Daniel Thompson",
    "Thomas Garcia", "Nancy Martinez", "Matthew Robinson", "Lisa Clark", "Anthony Lewis",
    "Betty Walker", "Mark Young", "Margaret Allen", "Donald King", "Sandra Wright"
]

# 全局停止标志 (用于 GUI 停止任务)
STOP_FLAG = False

# 无头模式开关 (True=后台运行无窗口, False=显示浏览器窗口)
HEADLESS_MODE = True
# ==================================================


# ==================== 工具函数 ====================
def print_log(msg, level="INFO"):
    """统一日志输出格式"""
    icons = {"INFO": "→", "WARN": "⚠", "ERROR": "✗", "OK": "✓"}
    icon = icons.get(level, "•")
    print(f"{icon} {msg}")


def print_separator(char="=", length=80):
    """打印分隔线"""
    print(char * length)


def print_progress(current, total, success, fail, avg_time):
    """打印进度信息"""
    print(f"\n>>> 进度: {current}/{total} | 成功: {success} | 失败: {fail} | 平均耗时: {avg_time:.1f}s")


def log_error(email, error_msg):
    """记录错误到日志文件"""
    error_file = Path("errors.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] 邮箱: {email} | 错误: {error_msg}\n"
    
    try:
        with open(error_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        print_log(f"错误已记录到 errors.log", "INFO")
    except Exception as e:
        print_log(f"写入错误日志失败: {e}", "WARN")


# ==================== 邮箱管理 ====================
email_queue = []


def create_temp_email():
    """创建临时邮箱地址"""
    try:
        response = requests.get(
            f"{MAIL_API}/api/generate-email",
            headers={"X-API-Key": MAIL_KEY},
            timeout=30
        )
        if response.status_code == 200 and response.json().get('success'):
            email = response.json()['data']['email']
            return email
    except Exception as e:
        print_log(f"邮箱服务异常: {e}", "❌")
    return None


def prefetch_email():
    """预创建邮箱并加入队列"""
    email = create_temp_email()
    if email:
        email_queue.append(email)


def get_email():
    """获取邮箱地址(优先使用队列中的)"""
    if email_queue:
        email = email_queue.pop(0)
        print_log(f"邮箱就绪 → {email}")
        return email
    
    email = create_temp_email()
    if email:
        print_log(f"已生成 → {email}")
    return email


def fetch_verification_code(email, timeout=60):
    """获取邮箱验证码"""
    print_log("等待邮件验证码...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"{MAIL_API}/api/emails",
                params={"email": email},
                headers={"X-API-Key": MAIL_KEY},
                timeout=10
            )
            
            if response.status_code == 200:
                emails = response.json().get('data', {}).get('emails', [])
                if emails:
                    html_content = emails[0].get('html_content') or emails[0].get('content', '')
                    soup = BeautifulSoup(html_content, 'html.parser')
                    code_element = soup.find('span', class_='verification-code')
                    
                    if code_element:
                        code = code_element.get_text().strip()
                        if len(code) == 6:
                            print_log(f"验证码 → {code}", "OK")
                            return code
        except:
            pass
        
        elapsed = int(time.time() - start_time)
        print(f"  等待中... ({elapsed}s)", end='\r')
        time.sleep(2)
    
    print_log("验证码超时,请检查网络", "ERROR")
    return None


# ==================== 账号注册 ====================
def save_account_config(email, driver, timeout=10):
    """提取并保存账号配置信息"""
    print_log(f"提取账号配置中(最多 {timeout}s)...")
    start_time = time.time()
    account_data = None

    while time.time() - start_time < timeout:
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

        time.sleep(1)

    if not account_data:
        print_log(f"配置不完整,已跳过 → {email}", "WARN")
        return None

    # 保存到文件
    existing_accounts = []
    if Path(ACCOUNTS_FILE).exists():
        try:
            with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                existing_accounts = json.load(f)
        except:
            pass
    
    existing_accounts.append(account_data)
    
    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing_accounts, f, indent=2, ensure_ascii=False)
    
    print_log(f"已保存 → {ACCOUNTS_FILE}", "OK")
    return account_data


def fast_type(element, text, delay=0.02):
    """快速输入文本"""
    for c in text:
        element.send_keys(c)
        time.sleep(delay)


def register_single_account(driver, executor):
    """注册单个账号 (来自 app.py 的简洁版本)"""
    start_time = time.time()
    email = get_email()
    if not email:
        return None, False, None, 0

    wait = WebDriverWait(driver, 30)

    try:
        # 1. 访问登录页
        driver.get(LOGIN_URL)
        
        # 检测空白页
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
        
        # 验证邮箱是否成功输入
        time.sleep(0.3)
        actual_value = inp.get_attribute("value")
        if actual_value != email:
            print_log(f"输入验证失败，清空后重新输入...", "WARN")
            # 清空后用 JS 输入
            driver.execute_script("arguments[0].value = '';", inp)
            time.sleep(0.1)
            driver.execute_script("arguments[0].value = arguments[1];", inp, email)
            # 触发 input 事件
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

        # 异步预创建下一个邮箱
        executor.submit(prefetch_email)

        # 4. 获取验证码
        time.sleep(2)
        code = fetch_verification_code(email)
        if not code:
            return email, False, None, time.time() - start_time

        # 5. 输入验证码
        time.sleep(1)
        print_log(f"输入验证码 → {code}")
        try:
            pin = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='pinInput']")))
            pin.click()
            time.sleep(0.1)
            fast_type(pin, code, 0.05)
        except:
            try:
                span = driver.find_element(By.CSS_SELECTOR, "span[data-index='0']")
                span.click()
                time.sleep(0.2)
                driver.switch_to.active_element.send_keys(code)
            except Exception as e:
                print_log(f"验证码输入失败: {e}", "ERROR")
                return email, False, None, time.time() - start_time

        # 6. 点击验证
        time.sleep(0.5)
        try:
            vbtn = driver.find_element(By.XPATH, XPATH["verify_btn"])
            driver.execute_script("arguments[0].click();", vbtn)
        except:
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

        # 轮询检测姓名输入框
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
            return email, False, None, time.time() - start_time

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
            return email, True, config, elapsed
        return email, False, None, elapsed

    except Exception as e:
        print_log(f"注册异常: {e}", "ERROR")
        log_error(email, str(e))
        return email, False, None, time.time() - start_time


# ==================== 账号上传 ====================
class AccountUploader:
    """账号上传管理类"""
    
    def __init__(self, api_host, admin_key):
        self.api_host = api_host.rstrip('/')
        self.admin_key = admin_key
        self.session = requests.Session()
        
    def login(self):
        """登录到服务器"""
        print_log("连接服务器中...")
        login_url = f"{self.api_host}/login"
        
        try:
            response = self.session.post(
                login_url,
                data={"admin_key": self.admin_key},
                allow_redirects=True,
                timeout=30
            )
            
            if len(self.session.cookies) > 0:
                print_log("服务器连接成功", "OK")
                return True
            
            if response.status_code == 200 and '登录' in response.text:
                print_log("密钥验证失败", "ERROR")
                return False
            
            print_log("服务器连接失败", "ERROR")
            return False
                
        except Exception as e:
            print_log(f"连接异常: {e}", "ERROR")
            return False
    
    def upload_and_replace(self, file_path):
        """覆盖上传账号配置"""
        if not Path(file_path).exists():
            print_log(f"文件不存在 → {file_path}", "ERROR")
            return False
        
        print_log(f"读取本地文件 → {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                accounts_data = json.load(f)
        except Exception as e:
            print_log(f"文件读取异常: {e}", "ERROR")
            return False
        
        print_log(f"本地账号 → {len(accounts_data)} 个")
        print_log("开始上传...")
        
        upload_url = f"{self.api_host}/accounts-config"
        
        try:
            response = self.session.put(
                upload_url,
                json=accounts_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print_log("上传完成!", "OK")
                print_log(f"{result.get('message', '配置已更新')}")
                print_log(f"服务器账号 → {result.get('account_count', len(accounts_data))} 个")
                
                print()
                print_separator()
                print_log("正在获取服务器账号状态...")
                print_separator()
                self.view_accounts()
                
                return True
            else:
                print_log(f"上传失败,状态码: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            print_log(f"上传异常: {e}", "ERROR")
            return False
    
    def upload_and_merge(self, file_path):
        """合并上传账号配置(保留远程正常账号)"""
        print_log("智能合并模式启动...")
        
        # 读取本地账号
        if not Path(file_path).exists():
            print_log(f"本地文件缺失 → {file_path}", "ERROR")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                local_accounts = json.load(f)
            print_log(f"本地账号 → {len(local_accounts)} 个")
        except Exception as e:
            print_log(f"读取本地文件失败: {e}", "ERROR")
            return False
        
        # 获取远程账号配置
        print_log("获取远程配置...")
        config_url = f"{self.api_host}/accounts-config"
        
        try:
            response = self.session.get(config_url, timeout=30)
            if response.status_code == 200:
                remote_config = response.json()
                remote_accounts = remote_config.get('accounts', [])
                print_log(f"远程账号 → {len(remote_accounts)} 个")
            else:
                print_log("远程配置获取失败,仅上传本地", "WARN")
                remote_accounts = []
        except Exception as e:
            print_log(f"远程连接异常: {e},仅上传本地", "WARN")
            remote_accounts = []
        
        # 筛选远程正常账号(未过期、未禁用)
        valid_remote_accounts = []
        for account in remote_accounts:
            if account.get('disabled', False):
                continue
            
            expires_at = account.get('expires_at')
            if expires_at and expires_at != '未设置':
                try:
                    beijing_tz = timezone(timedelta(hours=8))
                    expire_time = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                    expire_time = expire_time.replace(tzinfo=beijing_tz)
                    current_time = datetime.now(beijing_tz)
                    if expire_time <= current_time:
                        continue
                except:
                    pass
            
            valid_remote_accounts.append(account)
        
        print_log(f"有效远程账号 → {len(valid_remote_accounts)} 个")
        
        # 合并账号(去重)
        merged_accounts = list(valid_remote_accounts)
        remote_ids = {acc.get('id') for acc in valid_remote_accounts}
        
        new_count = 0
        for local_account in local_accounts:
            local_id = local_account.get('id')
            if local_id not in remote_ids:
                merged_accounts.append(local_account)
                new_count += 1
        
        print_log(f"合并结果 → 保留 {len(valid_remote_accounts)} 个,新增 {new_count} 个,共 {len(merged_accounts)} 个")
        
        # 上传合并后的配置
        print_log("上传合并配置...")
        upload_url = f"{self.api_host}/accounts-config"
        
        try:
            response = self.session.put(
                upload_url,
                json=merged_accounts,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print_log("合并上传完成!", "OK")
                print_log(f"{result.get('message', '配置已更新')}")
                print_log(f"服务器账号 → {result.get('account_count', len(merged_accounts))} 个")
                
                print()
                print_separator()
                print_log("正在获取服务器账号状态...")
                print_separator()
                self.view_accounts()
                
                return True
            else:
                print_log(f"上传失败,状态码: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            print_log(f"上传异常: {e}", "ERROR")
            return False
    
    def view_accounts(self):
        """查看远程账号状态"""
        print_log("查询远程账号...")
        
        view_url = f"{self.api_host}/accounts"
        
        try:
            response = self.session.get(view_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                accounts = data.get('accounts', [])
                total = data.get('total', len(accounts))
                
                if not accounts:
                    print_log("远程无账号配置", "INFO")
                    return True
                
                print(f"\n共 {total} 个账号")
                print_separator("=", 120)
                
                # 表头
                print(f"{'序号':<6} {'账号ID':<35} {'状态':<12} {'过期时间':<22} {'剩余时长':<15} {'累计对话':<10}")
                print_separator("-", 120)
                
                # 账号列表
                for i, account in enumerate(accounts, 1):
                    acc_id = account.get('id', 'N/A')
                    status = account.get('status', 'N/A')
                    expires_at = account.get('expires_at', '未设置')
                    remaining = account.get('remaining_display', 'N/A')
                    conversations = account.get('conversation_count', 0)
                    
                    if len(acc_id) > 33:
                        acc_id = acc_id[:30] + "..."
                    
                    print(f"{i:<6} {acc_id:<35} {status:<12} {expires_at:<22} {remaining:<15} {conversations:<10}")
                
                print_separator("=", 120)
                return True
            else:
                print_log(f"查询失败 → 状态码 {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            print_log(f"查询异常: {e}", "ERROR")
            return False


# ==================== 主程序流程 ====================
def run_batch_registration(target_count):
    """批量注册账号 (保底成功数模式)"""
    print()
    print_separator()
    print(f"目标: 成功注册 {target_count} 个账号")
    print_separator()
    print()
    
    # 清空旧文件
    if Path(ACCOUNTS_FILE).exists():
        Path(ACCOUNTS_FILE).unlink()
        print_log(f"已清空 → {ACCOUNTS_FILE}")
    
    driver = None
    executor = ThreadPoolExecutor(max_workers=2)
    success_count = 0
    fail_count = 0
    attempt_count = 0
    total_time = 0
    success_times = []

    # 预创建第一个邮箱
    executor.submit(prefetch_email)
    
    # 连续失败计数器（用于保护机制）
    consecutive_fails = 0
    MAX_CONSECUTIVE_FAILS = 20

    # 循环直到成功数达到目标
    while success_count < target_count:
        # 检查全局停止标志
        global STOP_FLAG
        if STOP_FLAG:
            print_log("收到停止信号，中止任务", "WARN")
            STOP_FLAG = False  # 重置标志
            break
        
        # 连续失败保护
        if consecutive_fails >= MAX_CONSECUTIVE_FAILS:
            print_log(f"连续失败 {MAX_CONSECUTIVE_FAILS} 次，中止本轮任务", "ERROR")
            break
        
        attempt_count += 1
        current_target = target_count + fail_count  # 动态调整显示的总数
        
        print()
        print_separator("#", 60)
        print(f"正在注册第 {attempt_count} 个账号 (成功: {success_count}/{target_count})")
        print_separator("#", 60)
        print()

        # 确保浏览器可用
        if driver is None:
            options = uc.ChromeOptions()
            if HEADLESS_MODE:
                print_log("启动无头浏览器...")
                options.add_argument("--headless=new")
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("--window-size=1200,800")
            else:
                print_log("启动浏览器...")
            driver = uc.Chrome(options=options, use_subprocess=True)
            if not HEADLESS_MODE:
                driver.set_window_size(100, 200)
                driver.set_window_position(50, 50)
            time.sleep(1)
        else:
            try:
                _ = driver.current_url
            except:
                print_log("浏览器已关闭,重启中...")
                try: 
                    driver.quit()
                except: 
                    pass
                options = uc.ChromeOptions()
                if HEADLESS_MODE:
                    options.add_argument("--headless=new")
                    options.add_argument("--disable-gpu")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--window-size=1200,800")
                driver = uc.Chrome(options=options, use_subprocess=True)
                if not HEADLESS_MODE:
                    driver.set_window_size(100, 200)
                    driver.set_window_position(50, 50)
                time.sleep(1)

        try:
            email, success, config, elapsed = register_single_account(driver, executor)
            total_time += elapsed
            
            if success and config:
                success_count += 1
                success_times.append(elapsed)
                consecutive_fails = 0  # 重置连续失败计数
                print_log(f"进度: {success_count}/{target_count} 完成", "OK")
            else:
                fail_count += 1
                consecutive_fails += 1
                print_log(f"失败 +1 (连续失败: {consecutive_fails}/{MAX_CONSECUTIVE_FAILS})", "WARN")
                
        except Exception as e:
            error_msg = str(e).lower()
            print_log(f"注册异常: {e}", "ERROR")
            fail_count += 1
            consecutive_fails += 1
            
            # 检测空白页或页面加载问题
            if "blank" in error_msg or "timeout" in error_msg or "element" in error_msg:
                print_log("检测到页面异常，重启浏览器...", "WARN")
                if driver:
                    try: 
                        driver.quit()
                    except: 
                        pass
                    driver = None
            elif driver:
                try: 
                    driver.quit()
                except: 
                    pass
                driver = None

        avg_time = total_time / attempt_count if total_time > 0 else 0
        print_progress(success_count, target_count, success_count, fail_count, avg_time)

        if success_count < target_count and driver:
            try:
                driver.delete_all_cookies()
            except:
                pass
            time.sleep(random.randint(2, 3))

    executor.shutdown(wait=False)
    if driver:
        try: 
            driver.quit()
        except: 
            pass
        
        # Monkeypatch: 防止 __del__ 再次调用 quit 导致 WinError 6
        try:
            driver.quit = lambda: None
        except:
            pass
            
        driver = None

    # 统计信息
    avg_time = sum(success_times) / len(success_times) if success_times else 0
    min_time = min(success_times) if success_times else 0
    max_time = max(success_times) if success_times else 0
    
    print()
    print_separator()
    print(f"注册完成! 目标: {target_count}, 成功: {success_count}, 失败: {fail_count}, 总尝试: {attempt_count}")
    print(f"总耗时: {total_time:.1f}s | 平均: {avg_time:.1f}s | 最快: {min_time:.1f}s | 最慢: {max_time:.1f}s")
    print(f"账号已保存至: {ACCOUNTS_FILE}")
    print_separator()
    
    return {
        "success": success_count,
        "fail": fail_count,
        "attempts": attempt_count,
        "avg_time": avg_time,
        "success_times": success_times,
        "is_ok": success_count > 0
    }


def handle_task_execution(count, upload_mode, uploader):
    """执行一次完整的任务(注册+上传)"""
    stats = run_batch_registration(count)
    
    if stats.get('is_ok'):
        print()
        # 先登录再上传
        if not uploader.login():
            print_log("服务器登录失败,无法上传", "ERROR")
            return stats
        
        if upload_mode == 'replace':
            print_log("开始覆盖上传到服务器...")
            uploader.upload_and_replace(ACCOUNTS_FILE)
        elif upload_mode == 'merge':
            print_log("开始合并上传到服务器...")
            uploader.upload_and_merge(ACCOUNTS_FILE)
    else:
        print_log("注册流程未成功,取消上传", "WARN")
        
    return stats


def main():
    """主程序入口"""
    print_separator()
    print("Gemini Business 自动注册上传工具")
    print_separator()
    print()
    
    uploader = AccountUploader(API_HOST, ADMIN_KEY)
    
    # 登录服务器
    if not uploader.login():
        print_log("登录失败,无法继续", "ERROR")
        input("\n按回车键退出...")
        sys.exit(1)
    
    print()
    
    while True:
        print("\n请选择操作:")
        print("  1. 注册上传")
        print("  2. 查看远程账号状态")
        print("  3. 退出")
        print()
        
        choice = input("请输入选项 (1-3): ").strip()
        
        if choice == "1":
            # 确定上传模式
            upload_mode = 'merge'
            
            # 1. 询问数量
            count_str = input("\n请输入注册数量 (默认 5): ").strip()
            count = int(count_str) if count_str else 5
            
            # 2. 询问执行模式
            print("\n请选择执行模式:")
            print("  1. 立即执行一次")
            print("  2. 定时循环执行 (支持自定义间隔)")
            mode_choice = input("请输入选项 (1-2): ").strip()
            
            if mode_choice == "2":
                # 定时模式
                hours_str = input("\n请输入循环间隔小时 (默认 12): ").strip()
                try:
                    interval_hours = float(hours_str) if hours_str else 12.0
                except:
                    print_log("输入无效,使用默认值 12 小时", "WARN")
                    interval_hours = 12.0
                
                print(f"\n已选择: 定时循环模式 (间隔 {interval_hours} 小时)")
                run_now_str = input("是否在开始循环前立即运行一次? (y/n, 默认 y): ").strip().lower()
                run_now = run_now_str != 'n'
                
                print_log("定时任务已启动! 按 Ctrl+C 可随时停止", "INFO")
                
                loop_count = 0
                while True:
                    loop_count += 1
                    
                    if run_now or loop_count > 1:
                        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] >>> 开始第 {loop_count} 次循环任务")
                        handle_task_execution(count, upload_mode, uploader)
                        print_log(f"第 {loop_count} 次任务完成", "INFO")
                    else:
                        print_log("跳过首次运行,直接进入等待", "INFO")

                    # 计算下次运行时间
                    next_run = datetime.now() + timedelta(hours=interval_hours)
                    print_log(f"下一次任务将在 {next_run.strftime('%Y-%m-%d %H:%M:%S')} 开始", "INFO")
                    
                    # 倒计时等待
                    total_seconds = int(interval_hours * 3600)
                    try:
                        while total_seconds > 0:
                            # 每分钟更新一次状态，显示剩余时间
                            if total_seconds % 60 == 0:
                                pass 
                            time.sleep(1)
                            total_seconds -= 1
                    except KeyboardInterrupt:
                        print("\n")
                        print_log("检测到中断, 停止定时任务", "WARN")
                        break
                        
            else:
                # 立即执行模式 (默认)
                print()
                handle_task_execution(count, upload_mode, uploader)
                
        elif choice == "2":
            print()
            uploader.view_accounts()
            
        elif choice == "3":
            print("\n再见!")
            break
            
        else:
            print_log("无效选项,请重试", "WARN")
        
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        print_log("用户中断程序", "INFO")
    except Exception as e:
        print_log(f"程序异常: {e}", "ERROR")
        input("\n按回车键退出...")