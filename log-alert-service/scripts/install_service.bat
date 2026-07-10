@echo off
REM Windows服务安装脚本
REM 需要管理员权限运行
REM 需要NSSM工具：https://nssm.cc/download

echo ========================================
echo 设备监控服务安装脚本
echo ========================================

REM 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 错误: 需要管理员权限运行
    echo 请右键点击该文件，选择"以管理员身份运行"
    pause
    exit /b 1
)

REM 设置变量
set SERVICE_NAME=DeviceMonitoring
set PROJECT_ROOT=%~dp0..
set PYTHON_EXE=%PROJECT_ROOT%\venv\Scripts\python.exe
set MAIN_SCRIPT=%PROJECT_ROOT%\main.py
set CONFIG_FILE=%PROJECT_ROOT%\config.yaml

echo 服务名称: %SERVICE_NAME%
echo 项目路径: %PROJECT_ROOT%
echo Python路径: %PYTHON_EXE%
echo 主脚本: %MAIN_SCRIPT%
echo.

REM 检查NSSM
where nssm >nul 2>&1
if %errorLevel% neq 0 (
    echo 错误: 未找到NSSM工具
    echo 请从 https://nssm.cc/download 下载并安装NSSM
    echo 或将NSSM.exe放入PATH环境变量中
    pause
    exit /b 1
)

REM 检查文件
if not exist "%PYTHON_EXE%" (
    echo 错误: Python虚拟环境不存在
    echo 请先运行 scripts\build.bat
    pause
    exit /b 1
)

if not exist "%MAIN_SCRIPT%" (
    echo 错误: 主脚本不存在: %MAIN_SCRIPT%
    pause
    exit /b 1
)

REM 询问安装选项
echo 请选择安装模式:
echo   1. 一体化服务（日志监控 + Web服务）
echo   2. 仅Web服务
echo   3. 仅日志监控服务
set /p MODE="请输入选择 (1-3): "

if "%MODE%"=="1" (
    set SERVICE_ARGS=--web
    set SERVICE_DESC=设备监控服务（日志监控 + Web服务）
) else if "%MODE%"=="2" (
    set SERVICE_ARGS=--mode web
    set SERVICE_DESC=设备监控Web服务（API + WebSocket）
) else if "%MODE%"=="3" (
    set SERVICE_ARGS=--mode monitor
    set SERVICE_DESC=设备日志监控服务
) else (
    echo 无效的选择
    pause
    exit /b 1
)

echo.
echo 即将安装服务:
echo   名称: %SERVICE_NAME%
echo   描述: %SERVICE_DESC%
echo   参数: %SERVICE_ARGS%
echo.

REM 询问确认
set /p CONFIRM="确认安装? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo 安装已取消
    pause
    exit /b 0
)

REM 卸载已存在的服务
echo 检查已存在的服务...
sc query %SERVICE_NAME% >nul 2>&1
if %errorLevel% equ 0 (
    echo 服务已存在，正在卸载...
    nssm stop %SERVICE_NAME%
    nssm remove %SERVICE_NAME% confirm
)

REM 安装服务
echo 安装服务...
nssm install %SERVICE_NAME% "%PYTHON_EXE%" "%MAIN_SCRIPT%" %SERVICE_ARGS%

if %errorLevel% neq 0 (
    echo 错误: 服务安装失败
    pause
    exit /b 1
)

REM 配置服务
echo 配置服务参数...
nssm set %SERVICE_NAME% AppDirectory "%PROJECT_ROOT%"
nssm set %SERVICE_NAME% DisplayName "%SERVICE_DESC%"
nssm set %SERVICE_NAME% Description "%SERVICE_DESC%"
nssm set %SERVICE_NAME% Start SERVICE_AUTO_START
nssm set %SERVICE_NAME% AppEnvironmentExtra PYTHONUNBUFFERED=1

REM 配置日志重定向
nssm set %SERVICE_NAME% StdLogType "both"
nssm set %SERVICE_NAME% StdLog "service_output.log"
nssm set %SERVICE_NAME% StdErrLog "service_error.log"

REM 配置重启策略
nssm set %SERVICE_NAME% AppThrottle 1500 300000
nssm set %SERVICE_NAME% AppRestartDelay 5000
nssm set %SERVICE_NAME% AppExit Default Restart
nssm set %SERVICE_NAME% AppRestartDelay 5000

echo.
echo ========================================
echo 服务安装完成！
echo ========================================
echo.
echo 服务管理命令:
echo   启动服务: nssm start %SERVICE_NAME%
echo   停止服务: nssm stop %SERVICE_NAME%
echo   重启服务: nssm restart %SERVICE_NAME%
echo   查看状态: nssm status %SERVICE_NAME%
echo   编辑配置: nssm edit %SERVICE_NAME%
echo   卸载服务: nssm remove %SERVICE_NAME%
echo.

REM 询问是否立即启动
set /p START="是否立即启动服务? (Y/N): "
if /i "%START%"=="Y" (
    echo 启动服务...
    nssm start %SERVICE_NAME%
    timeout /t 3 >nul
    nssm status %SERVICE_NAME%
)

echo.
pause
