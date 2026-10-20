"""运行方式：在 backend 目录执行 python -m app.migrations.add_username_unique。"""

from sqlalchemy import Index, MetaData, Table, func, inspect, select
from sqlalchemy.engine import Connection

from app.database import engine


def upgrade(connection: Connection) -> bool:
    """为已有 users 表添加唯一索引；有重复账号时停止，不改动账号数据。"""
    inspector = inspect(connection)
    unique_keys = inspector.get_unique_constraints("users") + inspector.get_indexes(
        "users"
    )
    if any(
        key.get("column_names") == ["username"] and key.get("unique", True)
        for key in unique_keys
    ):
        return False

    users = Table("users", MetaData(), autoload_with=connection)
    duplicate = connection.execute(
        select(users.c.username)
        .group_by(users.c.username)
        .having(func.count() > 1)
        .limit(1)
    ).first()
    if duplicate:
        raise RuntimeError(
            "users 表存在重复账号，请先核实账号及其预约归属，处理重复数据后重试；"
            "本脚本不会自动删除或合并账号。"
        )

    Index("uq_users_username", users.c.username, unique=True).create(connection)
    return True


if __name__ == "__main__":
    with engine.begin() as connection:
        changed = upgrade(connection)
    print("用户名唯一索引已创建" if changed else "用户名唯一约束已存在，无需修改")
