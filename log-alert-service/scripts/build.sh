#!/bin/bash
# 设备监控服务构建脚本
# 用于构建前端和管理依赖

set -e  # 遇到错误立即退出

echo "========================================"
echo "设备监控服务构建脚本"
echo "========================================"

# 设置项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
cd "$PROJECT_ROOT"

# 1. 激活虚拟环境
echo "[1/4] 激活虚拟环境..."
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
else
    echo "错误: 虚拟环境不存在"
    echo "请先运行: python3 -m venv venv"
    exit 1
fi

# 2. 更新Python依赖
echo "[2/4] 更新Python依赖..."
pip install -r requirements.txt --upgrade

# 3. 构建前端
echo "[3/4] 构建前端..."
cd frontend

if [ -d node_modules ]; then
    echo "检测到node_modules，跳过npm install"
else
    echo "安装前端依赖..."
    npm install
fi

echo "构建前端..."
npm run build

cd "$PROJECT_ROOT"

# 4. 初始化数据库
echo "[4/4] 初始化数据库..."
python -c "from src.db.mysql import init_database; init_database()" || echo "警告: 数据库初始化失败（可能已存在）"

echo ""
echo "========================================"
echo "构建完成！"
echo "========================================"
echo ""
echo "启动服务:"
echo "  一体化启动: python main.py --web"
echo "  仅Web服务:  python run_web.py"
echo "  仅日志监控: python main.py"
echo ""
echo "停止服务: Ctrl+C"
echo ""
