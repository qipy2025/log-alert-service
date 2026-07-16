"""
数据库模型基类 - 统一的ORM基类
"""
from sqlalchemy.orm import declarative_base

# 创建统一的Base类
Base = declarative_base()

__all__ = ['Base']
