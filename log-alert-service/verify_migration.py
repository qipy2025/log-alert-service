"""验证数据库迁移"""
from src.db.mysql import get_db_session
from sqlalchemy import text

if __name__ == "__main__":
    session = get_db_session()

    try:
        # 查看所有表
        print("=== 数据库表列表 ===")
        result = session.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result]
        for table in tables:
            print(f"  - {table}")

        # 查看 device_config 表结构
        print("\n=== device_config table structure ===")
        result = session.execute(text("DESCRIBE device_config"))
        for row in result:
            field = row[0] or "NULL"
            type_info = row[1] or "NULL"
            print(f"  {field}: {type_info}")

        # 查看 device_config 表数据
        print("\n=== device_config table data ===")
        result = session.execute(text("SELECT id, device_name, log_path, enabled, auto_notify FROM device_config"))
        rows = result.fetchall()
        if rows:
            for row in rows:
                print(f"  ID: {row[0]}, Device: {row[1]}, Path: {row[2]}, Enabled: {row[3]}, Auto Notify: {row[4]}")
        else:
            print("  (No data)")

        # 查看 alarm_records 表结构（检查 notified 字段）
        print("\n=== alarm_records table structure (notified field) ===")
        result = session.execute(text("SHOW COLUMNS FROM alarm_records WHERE Field = 'notified'"))
        notified_row = result.fetchone()
        if notified_row:
            print(f"  Field: {notified_row[0]}, Type: {notified_row[1]}, Default: {notified_row[4]}")
        else:
            print("  (notified field not found)")

        print("\n[OK] Migration verification completed")

    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
        raise
    finally:
        session.close()
