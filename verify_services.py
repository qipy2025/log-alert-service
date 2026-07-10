#!/usr/bin/env python
"""验证MySQL和Redis服务是否可用"""
import sys
import os

def check_mysql():
    """检查MySQL连接"""
    try:
        import pymysql
        from dotenv import load_dotenv
        load_dotenv()

        conn = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DATABASE', 'log_alert')
        )
        cursor = conn.cursor()
        cursor.execute('SELECT VERSION()')
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        print(f"✓ MySQL连接成功: {version}")
        return True
    except Exception as e:
        print(f"✗ MySQL连接失败: {e}")
        return False

def check_redis():
    """检查Redis连接"""
    try:
        import redis
        from dotenv import load_dotenv
        load_dotenv()

        client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD') or None,
            db=int(os.getenv('REDIS_DB', 0))
        )
        client.ping()
        print("✓ Redis连接成功")
        return True
    except Exception as e:
        print(f"✗ Redis连接失败: {e}")
        return False

def main():
    print("=" * 50)
    print("服务验证检查")
    print("=" * 50)

    # 检查Python依赖
    try:
        import pymysql
        import redis
        print("✓ Python依赖已安装")
    except ImportError as e:
        print(f"✗ Python依赖缺失: {e}")
        print("请运行: pip install pymysql redis")
        sys.exit(1)

    mysql_ok = check_mysql()
    redis_ok = check_redis()

    print("=" * 50)
    if mysql_ok and redis_ok:
        print("所有服务正常 ✓")
        return 0
    else:
        print("服务检查失败 ✗")
        print("\n请参考 SERVICES_INSTALLATION.md 安装和配置服务")
        return 1

if __name__ == '__main__':
    sys.exit(main())
