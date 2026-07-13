#!/bin/bash
# 一键部署脚本 - Linux/Mac版本

set -e  # 遇到错误立即退出

echo "========================================"
echo "设备监控服务一键部署脚本"
echo "========================================"
echo

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.8+"
    exit 1
fi

echo "1. 检查Python环境..."
python3 --version

echo
echo "2. 运行自动化部署脚本..."
echo

# 运行Python部署脚本
python3 auto_deploy.py "$@"

echo
echo "部署完成！"