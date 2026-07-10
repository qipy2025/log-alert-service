@echo off
REM 设备监控服务构建脚本
REM 用于构建前端和管理依赖

echo ========================================
echo 设备监控服务构建脚本
echo ========================================

REM 设置项目根目录
set PROJECT_ROOT=%~dp0
cd %PROJECT_ROOT%

REM 1. 激活虚拟环境
echo [1/4] 激活虚拟环境...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo 错误: 虚拟环境不存在
    echo 请先运行: python -m venv venv
    pause
    exit /b 1
)

REM 2. 更新Python依赖
echo [2/4] 更新Python依赖...
pip install -r requirements.txt --upgrade
if errorlevel 1 (
    echo 错误: 依赖安装失败
    pause
    exit /b 1
)

REM 3. 构建前端
echo [3/4] 构建前端...
cd frontend
if exist node_modules (
    echo 检测到node_modules，跳过npm install
) else (
    echo 安装前端依赖...
    call npm install
    if errorlevel 1 (
        echo 错误: 前端依赖安装失败
        cd %PROJECT_ROOT%
        pause
        exit /b 1
    )
)

echo 构建前端...
call npm run build
if errorlevel 1 (
    echo 错误: 前端构建失败
    cd %PROJECT_ROOT%
    pause
    exit /b 1
)

cd %PROJECT_ROOT%

REM 4. 初始化数据库
echo [4/4] 初始化数据库...
python -c "from src.db.mysql import init_database; init_database()"
if errorlevel 1 (
    echo 警告: 数据库初始化失败（可能已存在）
)

echo.
echo ========================================
echo 构建完成！
echo ========================================
echo.
echo 启动服务:
echo   一体化启动: python main.py --web
echo   仅Web服务:  python run_web.py
echo   仅日志监控: python main.py
echo.
echo 停止服务: Ctrl+C
echo.

pause
