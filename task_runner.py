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
        self.friends = []          # 全部好友
        self.added_friends = set() # 已添加的好友集合
        self.friend_index = 0      # 当前好友索引（基于原始列表）
        self.results = {
            "total_accounts": 0,
            "login_success": 0,
            "login_fail": 0,
            "total_friend_requests": 0,
            "friend_success": 0,
            "friend_fail": 0,
            "friend_index": 0,     # 保存当前好友进度
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
        self.friends, self.added_friends = load_friends()

        if not self.accounts:
            logger.error("没有读取到任何账号，请检查 Excel 文件")
            return False

        if not self.friends:
            logger.error("没有读取到任何好友，请检查好友列表文件")
            return False

        logger.info(f"账号数量: {len(self.accounts)}")
        logger.info(f"好友总数: {len(self.friends)}")
        logger.info(f"已添加: {len(self.added_friends)}")
        logger.info(f"待添加: {len(self.friends) - len(self.added_friends)}")
        logger.info(f"每账号添加: {config.FRIENDS_PER_ACCOUNT} 个")
        return True

    def connect_device(self):
        """连接模拟器"""
        logger.info("=" * 60)
        logger.info("连接模拟器...")
        logger.info("=" * 60)
        return self.bot.connect()

    def _next_friend_batch(self):
        """获取下一个好友批次，自动跳过已添加的，返回 (batch, actual_start_index)"""
        batch = []
        idx = self.friend_index
        while idx < len(self.friends) and len(batch) < config.FRIENDS_PER_ACCOUNT:
            name = self.friends[idx]
            if name not in self.added_friends:
                batch.append(name)
            idx += 1
        return batch

    def _mark_added(self, friend_name):
        """标记好友为已添加（内存 + 文件）"""
        self.added_friends.add(friend_name)
        with open(self.added_file, "a", encoding="utf-8") as f:
            f.write(friend_name + "\n")

    def run_single_account(self, account):
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
            return None

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
        while added_count < config.FRIENDS_PER_ACCOUNT and self.friend_index < len(self.friends):
            # 跳过已添加的
            if self.friend_index < len(self.friends):
                friend_name = self.friends[self.friend_index]
                if friend_name in self.added_friends:
                    self.friend_index += 1
                    continue

            friend_name = self.friends[self.friend_index]
            logger.info(f"  [好友 {self.friend_index + 1}/{len(self.friends)}] 添加 {friend_name}...")

            add_ok = False
            last_msg = ""

            for retry in range(config.ADD_FRIEND_MAX_RETRY + 1):
                if retry > 0:
                    logger.info(f"    重试添加 {friend_name} ({retry}/{config.ADD_FRIEND_MAX_RETRY})...")

                ok, msg = self.bot.add_friend_by_username(friend_name)
                if ok:
                    add_ok = True
                    break
                elif msg == "captcha":
                    add_ok = False
                    last_msg = msg
                    break
                else:
                    last_msg = msg
                    logger.debug(f"    添加失败: {msg}")

            self.results["total_friend_requests"] += 1

            if add_ok:
                result["friends_added"].append(friend_name)
                self.results["friend_success"] += 1
                added_count += 1
                self._mark_added(friend_name)
                logger.success(f"  ✅ {friend_name} 添加成功")
                self.friend_index += 1
            else:
                if last_msg == "captcha":
                    result["friends_failed"].append({"name": friend_name, "error": "人机验证"})
                    result["captcha_triggered"] = True
                    self.results["friend_fail"] += 1
                    logger.fail(f"  ❌ {friend_name} 人机验证，跳过")
                    break  # 退出循环，切换账号
                else:
                    # 非 captcha 失败（如"用户不存在"），跳过这个好友继续下一个
                    result["friends_failed"].append({"name": friend_name, "error": last_msg})
                    self.results["friend_fail"] += 1
                    logger.fail(f"  ❌ {friend_name} 添加失败: {last_msg}")
                    self.friend_index += 1  # 跳过这个好友

            # 好友之间延时
            if added_count < config.FRIENDS_PER_ACCOUNT and self.friend_index < len(self.friends):
                self.bot.sleep(config.DELAY_BETWEEN_FRIENDS)

        logger.info(f"账号 {email} 完成: 成功 {len(result['friends_added'])}, 失败 {len(result['friends_failed'])}")

        # ---- 步骤4: 退出登录 ----
        try:
            self.bot.logout()
            logger.info(f"已退出账号 {email}")
        except Exception as e:
            logger.warning(f"退出登录异常: {e}")
            self.bot.stop_discord()

        self.bot.sleep(config.DELAY_BETWEEN_ACCOUNTS)

        return result

    def run(self, start_index=0, max_accounts=None, friend_start_index=0):
        """
        运行全部任务

        start_index: 从第几个账号开始（0-based）
        max_accounts: 最多处理多少个账号，None 表示全部
        friend_start_index: 从第几个好友开始（0-based，基于原始列表）
        """
        if not self.load_data():
            return False

        if not self.connect_device():
            return False

        self.friend_index = friend_start_index

        accounts_to_process = self.accounts[start_index:]
        if max_accounts:
            accounts_to_process = accounts_to_process[:max_accounts]

        self.results["total_accounts"] = len(accounts_to_process)
        self.results["friend_index"] = self.friend_index
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"开始执行任务，共 {len(accounts_to_process)} 个账号")
        logger.info(f"从第 {start_index + 1} 个账号开始")
        logger.info(f"从第 {friend_start_index + 1} 个好友开始")
        logger.info("=" * 60)

        start_time = time.time()
        consecutive_captcha = 0

        for i, account in enumerate(accounts_to_process):
            logger.info(f"\n进度: [{i + 1}/{len(accounts_to_process)}]")

            # 好友列表已全部处理完毕
            if self.friend_index >= len(self.friends):
                logger.info("")
                logger.info("=" * 60)
                logger.info("所有好友已添加完毕，自动停止!")
                logger.info("=" * 60)
                break

            try:
                result = self.run_single_account(account)
                if result is None:
                    break

                self.results["details"].append(result)
                self.results["friend_index"] = self.friend_index

                # 连续验证计数器
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
        logger.info(f"好友进度: {self.friend_index}/{len(self.friends)}")
        logger.info(f"详细结果已保存到: {self.result_file}")
        logger.info("=" * 60)

        return True

    def save_results(self):
        """保存运行结果"""
        os.makedirs(config.LOG_DIR, exist_ok=True)
        self.results["friend_index"] = self.friend_index
        with open(self.result_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
