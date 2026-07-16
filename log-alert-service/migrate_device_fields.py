#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""补全 device_config 表字段（SQLite/MySQL 兼容）

背景：当前环境 MySQL 不可用，manager 回退到 SQLite（data/sqlite.db）。
该 SQLite 库的 device_config 表是早期版本，缺少 auto_notify 以及本次新增的
网络共享/日志模式字段。本脚本用与业务代码相同的连接（manager.get_session）
幂等补全这些字段，使 add_device 等操作能正常工作。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except Exception:
    pass

from sqlalchemy import text
from src.db.manager import get_session

# device_config 需确保存在的列：(列名, 类型定义)
DEVICE_COLUMNS = [
    ("auto_notify", "BOOLEAN DEFAULT 0"),
    ("log_name_mode", "VARCHAR(20) DEFAULT 'date_subdir'"),
    ("smb_username", "VARCHAR(100)"),
    ("smb_password", "VARCHAR(200)"),
    ("monitor_days", "INTEGER DEFAULT 1"),
]


def get_columns(s, table):
    # 兼容 MySQL(SHOW COLUMNS) / SQLite(PRAGMA)
    try:
        return [c[0] for c in s.execute(text(f"SHOW COLUMNS FROM {table}")).fetchall()]
    except Exception:
        return [c[1] for c in s.execute(text(f"PRAGMA table_info({table})")).fetchall()]


def ensure_columns(s, table, columns):
    existing = get_columns(s, table)
    for col, defn in columns:
        if col in existing:
            print(f"[SKIP] {table}.{col} 已存在")
            continue
        try:
            s.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {defn}"))
            print(f"[OK]   已添加 {table}.{col}")
        except Exception as e:
            if "duplicate" in str(e).lower():
                print(f"[SKIP] {table}.{col} 已存在")
            else:
                print(f"[ERR]  {table}.{col}: {e}")


def main():
    s = get_session()
    try:
        print("现有 device_config 列:", get_columns(s, "device_config"))
        ensure_columns(s, "device_config", DEVICE_COLUMNS)
        s.commit()

        # alarm_records.notified 幂等补全（可能已存在）
        try:
            ar = get_columns(s, "alarm_records")
            if "notified" not in ar:
                s.execute(text("ALTER TABLE alarm_records ADD COLUMN notified BOOLEAN DEFAULT 0"))
                s.commit()
                print("[OK]   已添加 alarm_records.notified")
            else:
                print("[SKIP] alarm_records.notified 已存在")
        except Exception as e:
            print(f"[WARN] alarm_records.notified: {e}")

        print()
        print("最终 device_config 列:", get_columns(s, "device_config"))
        print("迁移完成")
    finally:
        s.close()


if __name__ == "__main__":
    main()
