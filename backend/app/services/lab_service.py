from operator import or_
from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.schemas.lab import (
    LabCreateRequest,
    LabResponse,
    LabUpdateRequest,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.utils.password import hash_password, verify_password


def get_lab_info(Lab: Lab) -> LabResponse:
    return LabResponse.model_validate(Lab)


def update_Lab_info(db: Session, Lab: Lab, data: LabUpdateRequest):
    Lab_dict = data.model_dump(
        exclude_none=True, exclude={"role", "status"}
    )  # pydantic对象转换成字典
    for field, value in Lab_dict.items():
        setattr(Lab, field, value)
    db.commit()
    db.refresh(Lab)
    return LabResponse.model_validate(Lab)


def get_lab_page_list(
    db: Session,
    page: int,
    page_size: int,
    keywords: str | None = None,
    status: bool | None = None,
):
    # select * from Lab where name like '%计算机实验室%'
    query = db.query(Lab)

    if keywords:
        query = query.filter(Lab.name.ilike(f"%{keywords}%"))
    if status:
        query = query.filter(Lab.status == status)
    total = query.count()
    items = (
        query.order_by(Lab.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[LabResponse.model_validate(item) for item in items], total=total
    )


def get_lab(db: Session, lab_id: int):
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    return LabResponse.model_validate(lab)


def create_lab(db: Session, data: LabCreateRequest):
    """新增"""

    exist = db.query(Lab).filter(Lab.name == data.name).first()
    if exist:
        raise BusinessException(message="实验室已存在")

    lab = Lab(
        **data.model_dump(exclude_none=True)
    )  # {"key1": "value1", "key2": "value2"} -> key1=value1, key2=value2
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


def update_lab(db: Session, Lab_id: int, data: LabUpdateRequest):
    """更新"""

    lab = db.query(Lab).filter(Lab.id == Lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    Lab_dict = data.model_dump(exclude_none=True)
    for field, value in Lab_dict.items():
        setattr(lab, field, value)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


def delete_lab(db: Session, Lab_id: int):
    """删除"""

    lab = db.query(Lab).filter(Lab.id == Lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")

    if db.query(Reservation.id).filter(Reservation.lab_id == Lab_id).first():
        raise BusinessException(
            message="该实验室存在预约记录，不能删除，可将实验室设为关闭状态", code=409
        )
    if db.query(Equipment.id).filter(Equipment.lab_id == Lab_id).first():
        raise BusinessException(
            message="该实验室下仍有设备，请先删除或转移设备", code=409
        )

    try:
        db.delete(lab)
        db.commit()
    except IntegrityError as exc:
        # 检查后仍可能新增关联记录，提交失败时回滚并返回业务提示。
        db.rollback()
        raise BusinessException(
            message="该实验室存在关联数据，无法删除", code=409
        ) from exc
