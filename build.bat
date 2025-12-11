@echo off
chcp 65001 >nul
echo ========================================
echo   PDF转Anki转换器 - 打包工具
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python
    pause
    exit /b 1
)

echo 正在打包，请稍候...
echo.

python build.py

echo.
pause
