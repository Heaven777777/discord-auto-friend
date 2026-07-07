import re

# 从日志中提取已添加的好友
added = set()
with open("logs/run_20260706_112125.log", encoding="utf-8") as f:
    for line in f:
        m = re.search(r"✅ (.+?) 添加成功", line)
        if m:
            added.add(m.group(1))

print(f"已添加好友: {len(added)} 个")

# 读取完整好友列表
with open("好友列表.txt", encoding="utf-8") as f:
    all_friends = [line.strip() for line in f if line.strip()]

print(f"好友总数: {len(all_friends)} 个")

# 过滤
remaining = [f for f in all_friends if f not in added]

print(f"剩余需添加: {len(remaining)} 个")

# 保存
with open("好友列表.txt", "w", encoding="utf-8") as f:
    for friend in remaining:
        f.write(friend + "\n")

print("已更新 好友列表.txt")