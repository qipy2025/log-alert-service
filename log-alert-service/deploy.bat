@echo off
REM 一键部署脚本 - Windows版本

echo ========================================
echo 设备监控服务一键部署脚本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo 1. 检查Python环境...
python --version

echo.
echo 2. 运行自动化部署脚本...
echo.

REM 运行Python部署脚本
python auto_deploy.py %*

if %errorlevel% neq 0 (
    echo.
    echo 部署失败！请检查错误信息。
    pause
    exit /b 1
)

echo.
echo 部署完成！
pause