"""数据层：SQLAlchemy 模型与会话（对应开题报告模块3「数据库表结构设计」）。

- 开发期默认 SQLite（零配置）；部署切换 MySQL 只需修改 .env 的 DATABASE_URL；
- 表结构：users（手机号用户）/ tasks（创作任务，持久化：刷新/关页/重启不丢）/
  works（作品，媒体文件存路径）/ work_likes（点赞关系）。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .. import config

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    """手机号用户：phone 唯一，nickname 用于展示（默认「戏迷+尾号」）。"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(11), unique=True, index=True, nullable=False)
    nickname = Column(String(64), default="")
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    """创作任务（持久化）：刷新页面 / 关闭网页 / 重启服务均不丢失。

    - kind: image | costume | text | video
    - status: pending | running | succeeded | failed
    - remote_task_id: 方舟等平台的异步任务ID（视频），重启后可续查
    - result: JSON字符串 {files: [本地文件名], urls: [...], text: ...}
    """

    __tablename__ = "tasks"

    id = Column(String(16), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    kind = Column(String(16), nullable=False)
    status = Column(String(16), default="pending", index=True)
    prompt = Column(Text, default="")
    provider = Column(String(64), default="")
    model = Column(String(64), default="")
    params = Column(Text, default="{}")
    remote_task_id = Column(String(128))
    result = Column(Text)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Work(Base):
    """生成作品：媒体文件（png/mp4）存 data/works/ 只存路径；文案存文本。"""

    __tablename__ = "works"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    kind = Column(String(16), nullable=False)  # image | costume | text | video
    title = Column(String(128), default="")
    prompt = Column(Text, default="")
    provider = Column(String(64), default="")
    model = Column(String(64), default="")
    media_file = Column(String(256))  # data/works/ 下的文件名（png/mp4）
    remote_url = Column(String(512))
    text_content = Column(Text)
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkLike(Base):
    __tablename__ = "work_likes"
    __table_args__ = (UniqueConstraint("user_id", "work_id", name="uq_user_work"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    work_id = Column(Integer, ForeignKey("works.id"), index=True)


def init_db() -> None:
    """建表（已存在则跳过）。"""
    config.WORKS_DIR.mkdir(parents=True, exist_ok=True)
    config.TASK_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    config.KNOWLEDGE_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def get_db():
    """FastAPI 依赖：请求级数据库会话。"""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
