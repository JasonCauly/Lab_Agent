from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, UniqueConstraint


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        {"comment": "用户信息表"},
    )

    username: Mapped[str] = mapped_column(String(50), comment="账号")
    password: Mapped[str] = mapped_column(String(255), comment="密码")
    name: Mapped[str] = mapped_column(String(50), comment="名称")
    role: Mapped[str] = mapped_column(
        String(50), comment="角色: student-学生, admin-管理员"
    )
    email: Mapped[str | None] = mapped_column(String(50), comment="邮箱", nullable=True)
    phone: Mapped[str | None] = mapped_column(
        String(50), comment="手机号", nullable=True
    )
    avatar: Mapped[str | None] = mapped_column(
        String(255), comment="头像", nullable=True
    )
    status: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="状态: True-启用, False-禁用"
    )
