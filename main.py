"""
Discord 模拟器自动加好友脚本
使用方法:
    python main.py                  # 运行全部账号
    python main.py --start 10       # 从第11个账号开始（跳过前10个）
    python main.py --count 5        # 只跑5个账号
    python main.py --start 10 --count 5
"""

import sys
import os
import traceback
import argparse


def main():
    parser = argparse.ArgumentParser(description="Discord 自动加好友工具")
    parser.add_argument("--start", type=int, default=0, help="从第几个账号开始（0-based，默认0）")
    parser.add_argument("--count", type=int, default=None, help="最多处理多少个账号，默认全部")
    parser.add_argument("--friend-start", type=int, default=0, help="从第几个好友开始（0-based，默认0）")
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
    import logger

    runner = TaskRunner()

    try:
        success = runner.run(start_index=args.start, max_accounts=args.count, friend_start_index=args.friend_start)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\n用户中断，正在保存结果...")
        runner.save_results()
        logger.info("已保存当前进度，可以用 --start 参数从中断处继续")
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
        # 最外层兜底：写入 error.txt 防止闪退看不到错误
        with open("error.txt", "w", encoding="utf-8") as f:
            f.write(f"程序启动失败: {e}\n\n")
            traceback.print_exc(file=f)
        print(f"\n程序启动失败: {e}")
        print("详细错误已写入 error.txt，请查看后反馈")
        input("\n按回车键退出...")
        sys.exit(1)