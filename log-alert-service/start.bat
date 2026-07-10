@echo off
REM 设备监控服务快速启动脚本

echo ========================================
echo 设备监控服务启动脚本
echo ========================================

REM 检查虚拟环境
if not exist venv\Scripts\activate.bat (
    echo 虚拟环境不存在，正在创建...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM 检查配置文件
if not exist config.yaml (
    echo 错误: config.yaml 不存在
    echo 请创建配置文件后再启动服务
    pause
    exit /b 1
)

REM 启动选项
echo 请选择启动模式:
echo   1. 一体化启动（日志监控 + Web服务）推荐
echo   2. 仅Web服务（API + WebSocket）
echo   3. 仅日志监控
echo   4. 自定义启动
set /p MODE="请输入选择 (1-4): "

if "%MODE%"=="1" (
    echo 启动一体化服务...
    python main.py --web
) else if "%MODE%"=="2" (
    echo 启动Web服务...
    python run_web.py
) else if "%MODE%"=="3" (
    echo 启动日志监控服务...
    python main.py
) else if "%MODE%"=="4" (
    echo 可用命令:
    echo   python main.py --help
    echo   python run_web.py --help
    echo   python test_websocket.py
    echo.
    set /p CUSTOM="请输入自定义命令: "
    %CUSTOM%
) else (
    echo 无效的选择
    pause
    exit /b 1
)

pause
