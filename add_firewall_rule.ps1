# 自动请求管理员权限的PowerShell脚本

# 检查是否以管理员身份运行
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    # 不是管理员，请求提升权限
    Write-Host "正在请求管理员权限..." -ForegroundColor Yellow
    Start-Process PowerShell -Verb RunAs -ArgumentList "-File", $PSCommandPath
    exit
}

# 以管理员身份运行的代码
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "添加防火墙规则 - 日志告警服务" -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

Write-Host "正在添加防火墙规则，允许5000端口..." -ForegroundColor Green

try {
    # 使用PowerShell防火墙cmdlet
    New-NetFirewallRule -DisplayName 'Log Alert Service 5000' `
                       -Direction Inbound `
                       -Protocol TCP `
                       -LocalPort 5000 `
                       -Action Allow `
                       -Profile Any `
                       -ErrorAction Stop

    Write-Host ""
    Write-Host "========================================"  -ForegroundColor Green
    Write-Host "✅ 防火墙规则添加成功！" -ForegroundColor Green
    Write-Host "========================================"  -ForegroundColor Green
    Write-Host ""
    Write-Host "现在可以从外部访问：http://10.148.98.100:5000" -ForegroundColor Cyan
    Write-Host ""

    # 显示规则详情
    Write-Host "规则详情：" -ForegroundColor Yellow
    Get-NetFirewallRule -DisplayName 'Log Alert Service 5000' | Select-Object DisplayName, Direction, Action, Profile | Format-Table -AutoSize

} catch {
    Write-Host ""
    Write-Host "========================================"  -ForegroundColor Red
    Write-Host "❌ 添加失败：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host "========================================"  -ForegroundColor Red
    Write-Host ""
}

Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
