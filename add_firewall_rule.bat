@echo off
echo ========================================
echo 添加防火墙规则 - 日志告警服务
echo ========================================
echo.

echo 正在添加防火墙规则，允许5000端口...
netsh advfirewall firewall add rule name="Log Alert Service 5000" dir=in action=allow protocol=TCP localport=5000 profile=any

if %errorlevel% == 0 (
    echo.
    echo ========================================
    echo ✅ 防火墙规则添加成功！
    echo ========================================
    echo.
    echo 现在可以从外部访问：http://10.148.98.100:5000
) else (
    echo.
    echo ========================================
    echo ❌ 添加失败，请确保以管理员身份运行
    echo ========================================
    echo.
    echo 右键点击此文件，选择"以管理员身份运行"
)

echo.
pause
