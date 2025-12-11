@echo off
chcp 65001 >nul
title PDF转Anki转换器

echo ========================================
echo        PDF转Anki转换器 v1.0
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.9+
    echo 请访问 https://www.python.org/downloads/ 下载安装
    echo.
    pause
    exit /b 1
)

echo [信息] 正在检查Python环境...
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [信息] Python版本: %PYTHON_VERSION%
echo.

REM 检查并安装依赖
echo [信息] 正在检查依赖包...

pip show PyMuPDF >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装 PyMuPDF...
    pip install -q PyMuPDF
)

pip show genanki >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装 genanki...
    pip install -q genanki
)

echo [信息] 依赖检查完成
echo.
echo [启动] 正在启动PDF转Anki转换器...
echo ========================================
echo.

REM 运行主程序
python main.py %*

if errorlevel 1 (
    echo.
    echo [错误] 程序运行出错，请检查错误信息
    pause
)
