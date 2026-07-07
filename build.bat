@echo off
chcp 65001 >nul
echo ============================================
echo   Discord 自动加好友工具 - 打包脚本
echo ============================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 安装 PyInstaller...
pip install pyinstaller -q

echo [2/3] 安装依赖...
pip install uiautomator2 openpyxl -q

echo [3/3] 开始打包（约 1-2 分钟）...
rmdir /s /q build dist release 2>nul

pyinstaller --onedir ^
    --name DiscordAutoFriend ^
    --hidden-import uiautomator2 ^
    --hidden-import openpyxl ^
    --hidden-import adbutils ^
    --hidden-import PIL ^
    --collect-data uiautomator2 ^
    --clean ^
    main.py

if %errorlevel% neq 0 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ============================================
echo   打包完成! 正在生成发布包...
echo ============================================

mkdir release 2>nul
xcopy /E /Y "dist\DiscordAutoFriend\*" "release\" >nul
copy /Y "config.json" "release\" >nul
copy /Y "使用说明.txt" "release\" >nul
copy /Y "账号.xlsx" "release\" >nul 2>nul
copy /Y "好友列表.txt" "release\" >nul 2>nul
echo. > "release\已添加好友.txt"
echo   [完成] 请将发布包发送给朋友

echo.
echo   ========================================
echo     发布包已生成: release\
echo   ========================================
echo.
echo   release\
echo   ├── DiscordAutoFriend.exe
echo   ├── config.json
echo   ├── 使用说明.txt
echo   ├── 账号.xlsx
echo   ├── 好友列表.txt
echo   ├── 已添加好友.txt
echo   └── _internal\  (运行库)
echo.
echo   将 release\ 文件夹打包成 zip 发给朋友!
echo   ========================================
pause