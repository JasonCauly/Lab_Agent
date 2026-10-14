from operator import or_
from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.lab import Lab
from app.schemas.lab import (
    LabCreateRequest,
    LabResponse,
    LabUpdateRequest,
)
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
    db: Session, page: int, page_size: int, keywords: str | None = None
):
    # select * from Lab where name like '%计算机实验室%'
    query = db.query(Lab)

    if keywords:
        query = query.filter(Lab.name.ilike(f"%{keywords}%"))
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

    db.delete(lab)
    db.commit()
