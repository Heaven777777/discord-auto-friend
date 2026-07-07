import json
import os
import sys

# PyInstaller 打包后，exe 所在目录才是真正的根目录
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==================== 加载 JSON 配置 ====================
_config_path = os.path.join(BASE_DIR, "config.json")
_defaults = {
    "emulator_serial": "127.0.0.1:7555",
    "excel_email_col": 1,
    "excel_password_col": 2,
    "excel_start_row": 1,
    "friends_per_account": 7,
    "delay_between_actions": 0.8,
    "delay_between_friends": 1.5,
    "delay_between_accounts": 3,
    "random_delay_range": 0.3,
    "element_wait_timeout": 5,
    "page_load_timeout": 5,
    "discord_package": "com.discord",
    "discord_activity": "com.discord.main.MainActivity",
    "login_max_retry": 2,
    "add_friend_max_retry": 1,
}

_cfg = {}
if os.path.exists(_config_path):
    with open(_config_path, "r", encoding="utf-8") as f:
        _cfg = json.load(f)

# 导出配置项，JSON 中有就用 JSON 的，没有就用默认值
EMULATOR_SERIAL = _cfg.get("emulator_serial", _defaults["emulator_serial"])
EXCEL_EMAIL_COL = _cfg.get("excel_email_col", _defaults["excel_email_col"])
EXCEL_PASSWORD_COL = _cfg.get("excel_password_col", _defaults["excel_password_col"])
EXCEL_START_ROW = _cfg.get("excel_start_row", _defaults["excel_start_row"])
FRIENDS_PER_ACCOUNT = _cfg.get("friends_per_account", _defaults["friends_per_account"])
DELAY_BETWEEN_ACTIONS = _cfg.get("delay_between_actions", _defaults["delay_between_actions"])
DELAY_BETWEEN_FRIENDS = _cfg.get("delay_between_friends", _defaults["delay_between_friends"])
DELAY_BETWEEN_ACCOUNTS = _cfg.get("delay_between_accounts", _defaults["delay_between_accounts"])
RANDOM_DELAY_RANGE = _cfg.get("random_delay_range", _defaults["random_delay_range"])
ELEMENT_WAIT_TIMEOUT = _cfg.get("element_wait_timeout", _defaults["element_wait_timeout"])
PAGE_LOAD_TIMEOUT = _cfg.get("page_load_timeout", _defaults["page_load_timeout"])
DISCORD_PACKAGE = _cfg.get("discord_package", _defaults["discord_package"])
DISCORD_ACTIVITY = _cfg.get("discord_activity", _defaults["discord_activity"])
LOGIN_MAX_RETRY = _cfg.get("login_max_retry", _defaults["login_max_retry"])
ADD_FRIEND_MAX_RETRY = _cfg.get("add_friend_max_retry", _defaults["add_friend_max_retry"])

# ==================== 文件路径（始终在 exe 所在目录） ====================
ACCOUNTS_FILE = os.path.join(BASE_DIR, "账号.xlsx")
FRIENDS_FILE = os.path.join(BASE_DIR, "好友列表.txt")
LOG_DIR = os.path.join(BASE_DIR, "logs")