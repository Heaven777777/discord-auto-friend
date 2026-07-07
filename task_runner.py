import time
import json
import os

import config
import logger
from discord_bot import DiscordAutomator
from data_reader import load_accounts, load_friends


class TaskRunner:
    """任务调度器：管理整个自动化流程"""

    def __init__(self):
        self.bot = DiscordAutomator()
        self.accounts = []
        self.friends = []
        self.results = {
            "total_accounts": 0,
            "login_success": 0,
            "login_fail": 0,
            "total_friend_requests": 0,
            "friend_success": 0,
            "friend_fail": 0,
            "details": []
        }
        self.result_file = os.path.join(config.LOG_DIR, "result.json")
        self.added_file = os.path.join(config.BASE_DIR, "已添加好友.txt")

    def load_data(self):
        """加载账号和好友数据"""
        logger.info("=" * 60)
        logger.info("加载数据...")
        logger.info("=" * 60)

        self.accounts = load_accounts()
        self.friends = load_friends()

        if not self.accounts:
            logger.error("没有读取到任何账号，请检查 Excel 文件")
            return False

        if not self.friends:
            logger.error("没有读取到任何好友，请检查好友列表文件")
            return False

        logger.info(f"账号数量: {len(self.accounts)}")
        logger.info(f"好友数量: {len(self.friends)}")
        logger.info(f"每账号添加: {config.FRIENDS_PER_ACCOUNT} 个")
        return True

    def connect_device(self):
        """连接模拟器"""
        logger.info("=" * 60)
        logger.info("连接模拟器...")
        logger.info("=" * 60)
        return self.bot.connect()

    def run_single_account(self, account, friend_list):
        """处理单个账号：登录 → 添加好友 → 退出"""
        email = account["email"]
        password = account["password"]
        result = {
            "email": email,
            "row": account["row"],
            "login_success": False,
            "login_error": "",
            "friends_added": [],
            "friends_failed": [],
        }

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"处理账号 [{account['row']}]: {email}")
        logger.info("=" * 60)

        # 检查连接，断了就重连
        if not self.bot.ensure_connected():
            logger.error("模拟器连接失败，终止任务")
            return None  # 返回 None 表示需要终止

        # ---- 步骤1: 登录 ----
        login_ok = False
        for retry in range(config.LOGIN_MAX_RETRY + 1):
            if retry > 0:
                logger.info(f"登录重试 ({retry}/{config.LOGIN_MAX_RETRY})...")
                self.bot.restart_discord()

            self.bot.launch_discord()
            ok, msg = self.bot.login(email, password)
            if ok:
                login_ok = True
                break
            else:
                logger.fail(f"登录失败: {msg}")
                result["login_error"] = msg

            # 如果是验证码，直接跳过这个账号
            captcha_keywords = ["验证", "captcha", "Captcha", "人机", "hCaptcha", "recaptcha"]
            if any(kw in msg for kw in captcha_keywords):
                logger.warning(f"账号 {email} 出现人机验证，跳过")
                break

        if not login_ok:
            result["login_success"] = False
            self.results["login_fail"] += 1
            return result

        result["login_success"] = True
        self.results["login_success"] += 1
        logger.success(f"账号 {email} 登录成功")

        # ---- 步骤2: 进入添加好友页 ----
        go_ok = self.bot.go_to_add_friend()
        if not go_ok:
            logger.warning("进入添加好友页面失败，尝试继续")

        # ---- 步骤3: 逐个添加好友 ----
        added_count = 0
        for idx, friend_name in enumerate(friend_list):
            if added_count >= config.FRIENDS_PER_ACCOUNT:
                break

            logger.info(f"  [{idx + 1}/{len(friend_list)}] 添加 {friend_name}...")

            add_ok = False
            for retry in range(config.ADD_FRIEND_MAX_RETRY + 1):
                if retry > 0:
                    logger.info(f"    重试添加 {friend_name} ({retry}/{config.ADD_FRIEND_MAX_RETRY})...")

                ok, msg = self.bot.add_friend_by_username(friend_name)
                if ok:
                    add_ok = True
                    break
                elif msg == "captcha":
                    # 人机验证，直接退出当前账号
                    logger.warning(f"    添加好友时出现人机验证，退出当前账号")
                    add_ok = False
                    break
                else:
                    logger.debug(f"    添加失败: {msg}")

            if add_ok:
                result["friends_added"].append(friend_name)
                self.results["friend_success"] += 1
                added_count += 1
                logger.success(f"  ✅ {friend_name} 添加成功")
                # 立即写入已添加好友文件，防止中断丢失
                with open(self.added_file, "a", encoding="utf-8") as f:
                    f.write(friend_name + "\n")
            else:
                if msg == "captcha":
                    result["friends_failed"].append({"name": friend_name, "error": "人机验证"})
                    result["captcha_triggered"] = True
                    self.results["friend_fail"] += 1
                    logger.fail(f"  ❌ {friend_name} 人机验证，跳过")
                    # 直接跳出整个好友添加循环
                    break
                else:
                    result["friends_failed"].append({"name": friend_name, "error": msg})
                    self.results["friend_fail"] += 1
                    logger.fail(f"  ❌ {friend_name} 添加失败: {msg}")

            self.results["total_friend_requests"] += 1

            # 每个好友之间延时
            if idx < len(friend_list) - 1 and added_count < config.FRIENDS_PER_ACCOUNT:
                self.bot.sleep(config.DELAY_BETWEEN_FRIENDS)

        logger.info(f"账号 {email} 完成: 成功 {len(result['friends_added'])}, 失败 {len(result['friends_failed'])}")

        # ---- 步骤4: 退出登录 ----
        try:
            self.bot.logout()
            logger.info(f"已退出账号 {email}")
        except Exception as e:
            logger.warning(f"退出登录异常: {e}")
            self.bot.stop_discord()

        # 账号切换延时
        self.bot.sleep(config.DELAY_BETWEEN_ACCOUNTS)

        return result

    def run(self, start_index=0, max_accounts=None, friend_start_index=0):
        """
        运行全部任务

        start_index: 从第几个账号开始（0-based）
        max_accounts: 最多处理多少个账号，None 表示全部
        friend_start_index: 从第几个好友开始（0-based）
        """
        if not self.load_data():
            return False

        if not self.connect_device():
            return False

        accounts_to_process = self.accounts[start_index:]
        if max_accounts:
            accounts_to_process = accounts_to_process[:max_accounts]

        self.results["total_accounts"] = len(accounts_to_process)
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"开始执行任务，共 {len(accounts_to_process)} 个账号")
        logger.info(f"从第 {start_index + 1} 个账号开始")
        logger.info(f"从第 {friend_start_index + 1} 个好友开始")
        logger.info("=" * 60)

        start_time = time.time()
        consecutive_captcha = 0  # 连续验证计数器

        for i, account in enumerate(accounts_to_process):
            logger.info(f"\n进度: [{i + 1}/{len(accounts_to_process)}]")

            # 好友列表已全部添加完毕，停止
            if friend_start_index >= len(self.friends):
                logger.info("")
                logger.info("=" * 60)
                logger.info("所有好友已添加完毕，自动停止!")
                logger.info("=" * 60)
                break

            # 计算这个账号要加哪些好友（从当前偏移开始，成功后递增）
            friend_batch = self.friends[friend_start_index:friend_start_index + config.FRIENDS_PER_ACCOUNT]

            try:
                result = self.run_single_account(account, friend_batch)
                if result is None:  # 连接失败，终止
                    break
                self.results["details"].append(result)
                # 只推进实际成功添加的好友数量（人机验证时部分好友未添加）
                if result["login_success"]:
                    actual_added = len(result["friends_added"])
                    friend_start_index += actual_added
                    if actual_added < config.FRIENDS_PER_ACCOUNT:
                        logger.info(f"本账号仅添加 {actual_added}/{config.FRIENDS_PER_ACCOUNT} 个好友，"
                                    f"下一个账号从第 {friend_start_index + 1} 个继续")
                # 连续验证计数器：有验证触发则+1，否则清零
                if result.get("captcha_triggered"):
                    consecutive_captcha += 1
                    logger.warning(f"连续验证计数: {consecutive_captcha}/3")
                    if consecutive_captcha >= 3:
                        logger.info("")
                        logger.info("=" * 60)
                        logger.info("连续3个账号触发验证，重启模拟器以重置状态...")
                        logger.info("=" * 60)
                        if self.bot.restart_emulator():
                            consecutive_captcha = 0
                            logger.info("模拟器重启完成，继续执行")
                        else:
                            logger.error("模拟器重启失败，终止任务")
                            break
                else:
                    consecutive_captcha = 0
            except Exception as e:
                logger.error(f"处理账号 {account['email']} 时发生异常: {e}")
                self.bot.stop_discord()
                time.sleep(5)
                self.results["details"].append({
                    "email": account["email"],
                    "row": account["row"],
                    "login_success": False,
                    "login_error": f"异常: {e}",
                    "friends_added": [],
                    "friends_failed": [],
                })

            # 每处理完一个账号保存一次结果
            self.save_results()

        # 统计
        elapsed = time.time() - start_time
        logger.info("")
        logger.info("=" * 60)
        logger.info("全部任务完成!")
        logger.info(f"总耗时: {int(elapsed // 60)} 分 {int(elapsed % 60)} 秒")
        logger.info(f"账号总数: {self.results['total_accounts']}")
        logger.info(f"登录成功: {self.results['login_success']}")
        logger.info(f"登录失败: {self.results['login_fail']}")
        logger.info(f"好友请求成功: {self.results['friend_success']}")
        logger.info(f"好友请求失败: {self.results['friend_fail']}")
        logger.info(f"详细结果已保存到: {self.result_file}")
        logger.info("=" * 60)

        return True

    def save_results(self):
        """保存运行结果"""
        os.makedirs(config.LOG_DIR, exist_ok=True)
        with open(self.result_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)