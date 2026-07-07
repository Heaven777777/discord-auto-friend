import time
import random
import os
import subprocess

import uiautomator2 as u2

import config
import logger


class DiscordAutomator:
    """Discord 模拟器自动化操作类"""

    def __init__(self, serial=None):
        self.serial = serial or config.EMULATOR_SERIAL
        self.d = None
        self.width = 0
        self.height = 0

    # ================ 基础连接 ================
    def connect(self):
        """连接模拟器"""
        try:
            logger.info(f"正在连接模拟器: {self.serial}")

            # 先尝试 adb connect 确保连接
            adb_path = os.path.join(os.path.dirname(u2.__file__), "..", "adbutils", "binaries", "adb.exe")
            if not os.path.exists(adb_path):
                adb_path = "adb"
            for attempt in range(3):
                try:
                    subprocess.run(
                        [adb_path, "connect", self.serial],
                        capture_output=True, timeout=5
                    )
                    break
                except Exception:
                    time.sleep(2)

            self.d = u2.connect(self.serial)
            self.width, self.height = self.d.window_size()
            logger.info(f"连接成功! 分辨率: {self.width}x{self.height}")
            return True
        except Exception as e:
            logger.error(f"连接模拟器失败: {e}")
            logger.error("请检查: 1) 模拟器是否已启动 2) config.json 中 emulator_serial 是否正确")
            return False

    def ensure_connected(self):
        """检查连接是否正常，断了就自动重连"""
        try:
            self.d.info
        except Exception:
            logger.warning("模拟器连接断开，正在重连...")
            return self.connect()
        return True

    def safe_call(self, func, *args, **kwargs):
        """带自动重连的操作调用，最多重试2次"""
        for attempt in range(3):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                err_msg = str(e)
                if "not found" in err_msg.lower() or "10054" in err_msg or "connection" in err_msg.lower():
                    logger.warning(f"连接异常 (尝试 {attempt+1}/3): {e}")
                    if attempt < 2:
                        time.sleep(3)
                        self.connect()
                    else:
                        raise
                else:
                    raise

    def sleep(self, base_delay=None):
        """带随机浮动的延时"""
        if base_delay is None:
            base_delay = config.DELAY_BETWEEN_ACTIONS
        delay = base_delay + random.uniform(-config.RANDOM_DELAY_RANGE, config.RANDOM_DELAY_RANGE)
        delay = max(0.5, delay)
        time.sleep(delay)

    # ================ 应用管理 ================
    def launch_discord(self):
        """启动 Discord"""
        logger.info("启动 Discord...")
        self.d.app_start(config.DISCORD_PACKAGE, activity=config.DISCORD_ACTIVITY, stop=True)
        time.sleep(config.PAGE_LOAD_TIMEOUT)
        return True

    def stop_discord(self):
        """停止 Discord"""
        logger.debug("停止 Discord...")
        self.d.app_stop(config.DISCORD_PACKAGE)
        time.sleep(1)
    def restart_discord(self):
        """重启 Discord"""
        self.stop_discord()
        self.launch_discord()

    def restart_emulator(self):
        """重启模拟器（ADB reboot），用于重置人机验证状态"""
        logger.info("=" * 60)
        logger.info("正在重启模拟器以重置验证状态...")
        logger.info("=" * 60)
        try:
            self.d.shell("reboot")
            logger.info("模拟器重启指令已发送，等待启动...")
            time.sleep(30)  # 等待模拟器重启
            # 重连
            for attempt in range(10):
                try:
                    self.d = u2.connect(self.serial)
                    self.width, self.height = self.d.window_size()
                    logger.info("模拟器重启完成，连接成功!")
                    return True
                except Exception:
                    logger.info(f"等待模拟器启动... ({attempt+1}/10)")
                    time.sleep(10)
            logger.error("模拟器重启超时，未能连接")
            return False
        except Exception as e:
            logger.error(f"模拟器重启失败: {e}")
            return False

    # ================ 元素操作封装 ================
    def wait_element(self, **kwargs):
        """等待元素出现，返回元素对象或 None"""
        timeout = kwargs.pop("timeout", config.ELEMENT_WAIT_TIMEOUT)
        try:
            el = self.d(**kwargs)
            if el.wait(timeout=timeout):
                return el
            return None
        except Exception:
            return None

    def element_exists(self, **kwargs):
        """判断元素是否存在"""
        try:
            return self.d(**kwargs).exists
        except Exception:
            return False

    def click_element(self, **kwargs):
        """点击元素，成功返回 True"""
        el = self.wait_element(**kwargs)
        if el:
            try:
                el.click()
                self.sleep()
                return True
            except Exception as e:
                logger.debug(f"点击元素失败: {e}")
                return False
        return False

    def set_text(self, text, **kwargs):
        """输入文本"""
        el = self.wait_element(**kwargs)
        if el:
            try:
                el.set_text(text)
                self.sleep(0.5)
                return True
            except Exception as e:
                logger.debug(f"输入文本失败: {e}")
                return False
        return False

    def get_text(self, **kwargs):
        """获取元素文本"""
        el = self.wait_element(**kwargs)
        if el:
            try:
                return el.get_text()
            except Exception:
                return ""
        return ""

    def click_position(self, x_ratio, y_ratio):
        """按比例点击屏幕位置"""
        x = int(self.width * x_ratio)
        y = int(self.height * y_ratio)
        self.d.click(x, y)
        self.sleep()

    def swipe_up(self, steps=10):
        """向上滑动"""
        self.d.swipe(
            self.width // 2,
            int(self.height * 0.8),
            self.width // 2,
            int(self.height * 0.3),
            steps=steps
        )
        self.sleep()

    def swipe_down(self, steps=10):
        """向下滑动"""
        self.d.swipe(
            self.width // 2,
            int(self.height * 0.3),
            self.width // 2,
            int(self.height * 0.8),
            steps=steps
        )
        self.sleep()

    def press_back(self):
        """按返回键"""
        self.d.press("back")
        self.sleep()

    def press_enter(self):
        """按回车键"""
        self.d.press("enter")
        self.sleep(0.5)

    def screenshot(self, name):
        """截图保存到日志目录"""
        path = os.path.join(config.LOG_DIR, f"{name}_{int(time.time())}.png")
        try:
            self.d.screenshot(path)
            logger.debug(f"截图已保存: {path}")
            return path
        except Exception as e:
            logger.debug(f"截图失败: {e}")
            return None

    # ================ 登录相关 ================
    def is_login_page(self):
        """判断是否在登录页面"""
        return (
            self.element_exists(text="登录")
            or self.element_exists(text="Log In")
            or self.element_exists(descriptionContains="登录")
        )

    def is_logged_in(self):
        """判断是否已登录（在主页）"""
        return (
            self.element_exists(description="主页")
            or self.element_exists(description="Home")
            or self.element_exists(textContains="好友")
            or self.element_exists(textContains="Friends")
        )

    def login(self, email, password):
        """
        登录 Discord
        返回: (成功/失败, 原因)
        """
        logger.info(f"开始登录账号: {email}")

        # 确保在登录页
        if not self.is_login_page():
            logger.debug("当前不在登录页，尝试回到登录页")
            if self.is_logged_in():
                self.logout()
            else:
                self.restart_discord()

        # 等待登录页加载
        time.sleep(2)

        # Discord 可能有欢迎页，需要先点击"登录"按钮进入登录表单
        for _ in range(3):
            # 如果邮箱输入框已出现，说明已在登录表单，无需再点
            if self.element_exists(className="android.widget.EditText", instance=0):
                break
            if self.element_exists(text="登录"):
                self.click_element(text="登录")
                time.sleep(1.5)
            elif self.element_exists(text="Log In"):
                self.click_element(text="Log In")
                time.sleep(1.5)
            else:
                break

        # 输入邮箱
        email_input = None
        for attempt in range(3):
            email_input = self.wait_element(className="android.widget.EditText", instance=0)
            if email_input:
                break
            time.sleep(1)
            # 可能还在欢迎页，再点一次登录
            for txt in ["登录", "Log In"]:
                if self.element_exists(text=txt):
                    self.click_element(text=txt)
                    time.sleep(1.5)
                    break

        if email_input:
            email_input.clear_text()
            email_input.set_text(email)
            logger.debug("已输入邮箱")
            self.sleep(0.5)
        else:
            self.screenshot("no_email_input")
            return False, "找不到邮箱输入框"

        # 输入密码（第二个输入框）
        pwd_input = self.d(className="android.widget.EditText", instance=1)
        if pwd_input.exists:
            pwd_input.clear_text()
            pwd_input.set_text(password)
            logger.debug("已输入密码")
            self.sleep(0.5)
        else:
            return False, "找不到密码输入框"

        # 点击登录按钮
        login_btn = None
        for txt in ["登录", "Log In", "登 录"]:
            if self.element_exists(text=txt):
                login_btn = txt
                break

        if login_btn:
            self.click_element(text=login_btn)
        else:
            btns = self.d(className="android.widget.Button")
            if btns.count >= 2:
                btns[1].click()
            elif btns.count == 1:
                btns[0].click()
            else:
                return False, "找不到登录按钮"

        # 等待登录结果
        time.sleep(4)

        # 检查是否有验证码/人机验证
        if self.is_captcha():
            self.screenshot("captcha")
            return False, "出现人机验证，需要人工处理"

        # 检查是否登录成功
        if self.is_logged_in():
            return True, "登录成功"

        # 检查错误提示
        error_texts = ["密码错误", "无效", "错误", "Invalid", "incorrect"]
        for t in error_texts:
            if self.element_exists(textContains=t):
                return False, f"登录失败: {self.get_text(textContains=t)}"

        # 再等一会儿再判断一次
        time.sleep(3)
        if self.is_logged_in():
            return True, "登录成功"

        self.screenshot("login_unknown")
        return False, "登录结果未知"

    def logout(self):
        """切换账号 - 清除 Discord 数据回到初始登录页"""
        logger.info("退出当前账号...")
        self.stop_discord()
        time.sleep(0.5)
        # 清除 Discord 应用数据，确保回到初始登录页
        self.d.shell(f"pm clear {config.DISCORD_PACKAGE}")
        time.sleep(2)
        self.launch_discord()
        logger.info("退出登录完成")
        return True

    # ================ 添加好友相关 ================
    def is_captcha(self):
        """检测当前页面是否出现人机验证"""
        captcha_keywords = ["验证", "captcha", "Captcha", "I am human", "人机",
                            "hCaptcha", "recaptcha", "Verify", "不是机器人"]
        for kw in captcha_keywords:
            if self.element_exists(textContains=kw):
                return True
        return False

    def go_to_add_friend(self):
        """进入添加好友页面"""
        logger.info("进入添加好友页面...")

        # 先确保在主页
        if not self.is_logged_in():
            return False

        # 点击底部的好友/Friends 标签
        clicked = False
        for txt in ["好友", "Friends"]:
            if self.element_exists(text=txt):
                self.click_element(text=txt)
                clicked = True
                break

        if not clicked:
            # 尝试点击底部第二个 tab（通常是好友）
            self.click_position(0.3, 0.95)

        time.sleep(1)

        # 点击"添加好友"或"添加朋友"按钮
        for txt in ["添加好友", "添加朋友", "Add Friend", "添加"]:
            if self.element_exists(text=txt):
                self.click_element(text=txt)
                clicked = True
                break

        if not clicked:
            # 尝试找右上角 + 号
            self.click_position(0.9, 0.08)
            time.sleep(1)
            for txt in ["添加好友", "Add Friend"]:
                if self.element_exists(text=txt):
                    self.click_element(text=txt)
                    break

        time.sleep(3)

        # 检查是否到了添加好友页
        on_page = (
            self.element_exists(textContains="用户名添加")
            or self.element_exists(textContains="username")
            or self.element_exists(textContains="用户名")
        )

        if on_page:
            logger.info("已进入添加好友页面")
            return True
        else:
            logger.warning("可能未进入添加好友页面")
            self.screenshot("add_friend_page")
            return False

    def add_friend_by_username(self, username):
        """
        通过用户名添加好友
        返回: (成功/失败, 原因)
        """
        logger.info(f"尝试添加好友: {username}")

        # 找输入框
        input_el = self.wait_element(className="android.widget.EditText")
        if not input_el:
            # 尝试点击"通过用户名添加"
            for txt in ["通过用户名添加", "通过用户名搜索", "搜索用户名"]:
                if self.element_exists(textContains=txt):
                    self.click_element(textContains=txt)
                    time.sleep(1)
                    break
            input_el = self.wait_element(className="android.widget.EditText")

        if not input_el:
            return False, "找不到用户名输入框"

        # 清空并输入用户名
        input_el.clear_text()
        input_el.set_text(username)
        self.sleep(1)

        # 点击搜索/下一步/发送
        for txt in ["搜索", "Search", "下一步", "Next", "发送好友请求", "Send Friend Request", "添加"]:
            if self.element_exists(text=txt):
                self.click_element(text=txt)
                break
        else:
            # 按回车搜索
            self.press_enter()

        time.sleep(3)

        # 检查是否出现人机验证
        if self.is_captcha():
            self.screenshot(f"captcha_add_{username}")
            return False, "captcha"

        # 检查搜索结果并点击添加
        for txt in ["发送好友请求", "Send Friend Request", "添加好友", "Add Friend"]:
            if self.element_exists(text=txt):
                self.click_element(text=txt)
                time.sleep(2)
                # 发送后也可能弹出验证
                if self.is_captcha():
                    self.screenshot(f"captcha_add_{username}")
                    return False, "captcha"
                logger.success(f"好友请求已发送给 {username}")
                return True, "好友请求已发送"

        # 检查是否已经是好友
        for txt in ["已是好友", "Friends", "已添加", "已发送", "Pending"]:
            if self.element_exists(textContains=txt):
                logger.info(f"{username} 已是好友或请求已发送")
                return True, "已是好友或请求待处理"

        # 检查用户不存在
        for txt in ["没有找到", "未找到", "No results", "找不到"]:
            if self.element_exists(textContains=txt):
                return False, "用户不存在"

        # 没找到明确结果，截图记录
        self.screenshot(f"add_{username}")
        return False, "添加结果不明确"

    def clear_input_and_go_back(self):
        """清空输入框，准备添加下一个"""
        input_el = self.d(className="android.widget.EditText")
        if input_el.exists:
            input_el.clear_text()
            self.sleep(0.5)