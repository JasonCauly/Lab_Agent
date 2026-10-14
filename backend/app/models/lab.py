from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, Integer, String


class Lab(Base):
    __tablename__ = "lab"
    __table_args__ = {"comment": "实验室信息"}

    name: Mapped[str] = mapped_column(String(50), comment="名称", nullable=False)
    description: Mapped[str] = mapped_column(String(500), comment="简介")
    img: Mapped[str] = mapped_column(String(100), comment="封面")
    location: Mapped[str] = mapped_column(String(100), comment="位置")
    capacity: Mapped[int] = mapped_column(Integer, comment="容量", default=0)
    open_time: Mapped[str] = mapped_column(String(20), comment="开放的开始时间")
    close_time: Mapped[str] = mapped_column(String(20), comment="开放的结束时间")
    status: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="状态: True-启用, False-禁用"
    )
