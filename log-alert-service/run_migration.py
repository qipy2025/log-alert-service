"""执行数据库迁移"""
from src.db.mysql import get_db_session
from src.db.migrations.add_device_config_table import upgrade, import_existing_devices

if __name__ == "__main__":
    session = get_db_session()
    try:
        upgrade(session)
        print("[OK] Migration successful")

        # 导入现有设备配置
        count = import_existing_devices(session)
        print(f"[OK] Imported {count} device configurations")

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()
