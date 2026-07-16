@echo off
echo 正在请求管理员权限添加防火墙规则...
echo 请在弹出的UAC对话框中点击"是"
echo.

netsh advfirewall firewall add rule name="Log Alert Service 5000" dir=in action=allow protocol=TCP localport=5000 profile=any

if %errorlevel% == 0 (
    echo.
    echo ✅ 防火墙规则添加成功！
    echo 现在可以访问：http://10.148.98.100:5000
) else (
    echo.
    echo ❌ 添加失败
)

echo.
pause
