"""
Discord 模拟器自动加好友脚本
使用方法:
    python main.py                  # 运行全部账号（自动恢复上次进度）
    python main.py --start 10       # 从第11个账号开始
    python main.py --count 5        # 只跑5个账号
    python main.py --start 10 --count 5
    python main.py --reset          # 重置进度，从头开始
"""

import sys
import os
import traceback
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="Discord 自动加好友工具")
    parser.add_argument("--start", type=int, default=None, help="从第几个账号开始（0-based），默认自动恢复")
    parser.add_argument("--count", type=int, default=None, help="最多处理多少个账号，默认全部")
    parser.add_argument("--friend-start", type=int, default=None, help="从第几个好友开始（0-based），默认自动恢复")
    parser.add_argument("--reset", action="store_true", help="重置进度，从头开始")
    args = parser.parse_args()

    print(r"""
  ____  _                       _
 |  _ \(_)___  ___ ___  _ __ __| |
 | | | | / __|/ __/ _ \| '__/ _` |
 | |_| | \__ \ (_| (_) | | | (_| |
 |____/|_|___/\___\___/|_|  \__,_|
      自动加好友工具 (模拟器版)
    """)

    from task_runner import TaskRunner
    import logger, config

    # 自动恢复上次进度
    start_index = args.start if args.start is not None else 0
    friend_start_index = args.friend_start if args.friend_start is not None else 0
    result_file = os.path.join(config.LOG_DIR, "result.json")

    if not args.reset and args.start is None and args.friend_start is None:
        if os.path.exists(result_file):
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    prev = json.load(f)
                prev_accounts = len(prev.get("details", []))
                prev_friends = prev.get("friend_index", 0)
                if prev_accounts > 0 or prev_friends > 0:
                    logger.info(f"检测到上次进度: 已处理 {prev_accounts} 个账号, 好友进度 {prev_friends}")
                    logger.info("自动从断点继续... (使用 --reset 可从头开始)")
                    start_index = prev_accounts
                    friend_start_index = prev_friends
            except Exception:
                pass

    runner = TaskRunner()

    try:
        success = runner.run(start_index=start_index, max_accounts=args.count, friend_start_index=friend_start_index)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\n用户中断，正在保存结果...")
        runner.save_results()
        logger.info("已保存当前进度，下次运行会自动从此处继续")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        traceback.print_exc()
        try:
            runner.save_results()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open("error.txt", "w", encoding="utf-8") as f:
            f.write(f"程序启动失败: {e}\n\n")
            traceback.print_exc(file=f)
        print(f"\n程序启动失败: {e}")
        print("详细错误已写入 error.txt，请查看后反馈")
        input("\n按回车键退出...")
        sys.exit(1)
