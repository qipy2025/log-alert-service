@echo off
REM 设备监控服务 - MySQL和Redis安装脚本
REM 此脚本将在Windows上安装MySQL和Redis

echo ============================================
echo 设备监控服务 - 环境安装
echo ============================================
echo.

echo [1/3] 检查必要工具...
where curl >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 需要curl工具。请确保Windows 10/11已安装。
    pause
    exit /b 1
)
echo ✓ curl工具可用

echo.
echo [2/3] MySQL 8.0 安装准备...
echo 请访问以下链接下载MySQL Installer:
echo https://dev.mysql.com/downloads/installer/
echo.
echo 选择 "mysql-installer-community-8.0.34.0.msi" 下载并安装
echo 安装时选择 "Developer Default" 或只安装 "MySQL Server"
echo 记住设置的root密码！
echo.
echo 按任意键继续下载MySQL便携版（推荐用于开发）...
pause >nul

REM 创建安装目录
set INSTALL_DIR=D:\MySQL
if not exist "%INSTALL_DIR%" (
    echo 创建安装目录: %INSTALL_DIR%
    mkdir "%INSTALL_DIR%"
)

REM 下载MySQL 8.0便携版（如果不存在）
set MYSQL_ZIP=%INSTALL_DIR%\mysql-8.0.34-winx64.zip
if not exist "%MYSQL_ZIP%" (
    echo 正在下载MySQL 8.0便携版（约250MB）...
    curl -L -o "%MYSQL_ZIP%" https://dev.mysql.com/get/Downloads/MySQL-8.0/mysql-8.0.34-winx64.zip
    if %ERRORLEVEL% NEQ 0 (
        echo 下载失败，请手动下载到: %MYSQL_ZIP%
        echo 下载地址: https://dev.mysql.com/downloads/mysql/
        pause
        exit /b 1
    )
) else (
    echo MySQL已下载: %MYSQL_ZIP%
)

REM 解压MySQL
set MYSQL_DIR=%INSTALL_DIR%\mysql-8.0.34-winx64
if not exist "%MYSQL_DIR%" (
    echo 正在解压MySQL...
    powershell -Command "Expand-Archive -Path '%MYSQL_ZIP%' -DestinationPath '%INSTALL_DIR%' -Force"
    echo ✓ MySQL解压完成
) else (
    echo MySQL已解压: %MYSQL_DIR%
)

echo.
echo [3/3] Redis 安装准备...
echo Redis没有官方Windows版本，有以下选项:
echo.
echo 选项A: 使用Memurai (Redis的Windows端口)
echo   访问: https://www.memurai.com/get-memurai-developer
echo   下载Memurai Developer版本（免费）
echo.
echo 选项B: 使用WSL (Windows Subsystem for Linux)
echo   在WSL中安装Redis: sudo apt-get install redis-server
echo.
echo 选项C: 使用Docker (推荐)
echo   运行: docker run -d -p 6379:6379 redis:latest
echo.

echo ============================================
echo MySQL后续配置步骤:
echo ============================================
echo.
echo 1. 创建MySQL配置文件 my.ini:
echo    [mysqld]
echo    basedir=%MYSQL_DIR%
echo    datadir=%MYSQL_DIR%\data
echo    port=3306
echo.
echo 2. 初始化数据库:
echo    cd %MYSQL_DIR%\bin
echo    mysqld --initialize --console
echo    (记住生成的临时密码)
echo.
echo 3. 安装MySQL服务:
echo    mysqld --install MySQL80
echo.
echo 4. 启动MySQL服务:
echo    net start MySQL80
echo.
echo 5. 修改root密码:
echo    mysql -u root -p
echo    ALTER USER 'root'@'localhost' IDENTIFIED BY 'your_password';
echo.
echo 6. 创建log_alert数据库:
echo    CREATE DATABASE log_alert;
echo.

pause
