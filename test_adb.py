"""ADB 连接测试"""
import subprocess, sys, os

# 找 adb.exe
possible_adb = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Lib", "site-packages", "adbutils", "binaries", "adb.exe"),
    "adb",
]

adb = None
for p in possible_adb:
    try:
        r = subprocess.run([p, "version"], capture_output=True, timeout=3)
        if r.returncode == 0:
            adb = p
            print(f"✅ 找到 adb: {p}")
            break
    except:
        continue

if not adb:
    print("❌ 未找到 adb.exe")
    input("按回车退出...")
    sys.exit(1)

ports = ["7555", "5555", "62001", "16384", "21503", "21505"]
for port in ports:
    addr = f"127.0.0.1:{port}"
    print(f"尝试 {addr}...")
    r = subprocess.run([adb, "connect", addr], capture_output=True, timeout=5)
    output = r.stdout.decode() + r.stderr.decode()
    print(f"  {output.strip()}")
    if "connected" in output.lower() or "already" in output.lower():
        print(f"\n✅ 成功! 端口是 {port}，在 config.json 里改成 127.0.0.1:{port}")
        break

input("\n按回车退出...")