import asyncio
from datetime import datetime
from time import sleep
from sqlalchemy import func, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.database import SessionLocal
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationCreateRequest, ReservationResponse


def get_reservation_page_list(
    db: Session,
    current_user: User,
    page: int,
    page_size: int,
    status: int | None = None,
):
    """查询预约记录"""
    query = db.query(Reservation)
    if current_user.role != "admin":
        query = query.filter(Reservation.user_id == current_user.id)
    if status is not None:
        query = query.filter(Reservation.status == status)
    total = query.count()
    items = (
        query.order_by(Reservation.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    result = []
    for item in items:
        res = ReservationResponse.model_validate(item)
        res.user_name = item.user.name if item.user else None
        res.lab_name = item.lab.name if item.lab else None
        res.equipment_name = item.equipment.name if item.equipment else None
        res.type = "设备" if item.equipment_id else "实验室"
        result.append(res)
    return PageResponse(list=result, total=total)


def create_reservation(db: Session, current_user: User, data: ReservationCreateRequest):
    for attempt in range(3):
        try:
            _create_reservation(db, current_user, data)
            return
        except OperationalError as exc:
            db.rollback()
            error_code = exc.orig.args[0] if exc.orig.args else None
            # InnoDB 死锁需要重试整个事务，每次仍重新持锁并检查冲突。
            if error_code == 1213 and attempt < 2:
                sleep(0.01 * (attempt + 1))
                continue
            if error_code in (1205, 1213):
                raise BusinessException(
                    message="预约资源正忙，请稍后重试", code=409
                ) from exc
            raise
        except Exception:
            # 包括业务校验失败在内，及时释放本次事务持有的资源锁。
            db.rollback()
            raise


def _create_reservation(
    db: Session, current_user: User, data: ReservationCreateRequest
):
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.time().replace(second=0, microsecond=0)
    start_time = datetime.strptime(data.start_time, "%H:%M").time()
    end_time = datetime.strptime(data.end_time, "%H:%M").time()
    if data.date < current_date:
        raise BusinessException(message="预约日期不能小于当天的日期")
    if end_time < start_time:
        raise BusinessException(message="预约的结束时间不能小于预约的开始时间")
    if data.date == current_date and start_time < current_time:
        raise BusinessException(message="当天预约的开始时间不能小于当前的时间")
    # 先锁定稳定存在的实验室行，再检查冲突并提交，避免空时段无行可锁。
    # 无值变更的 UPDATE 在 MySQL/InnoDB 和 SQLite 中均能持有写锁；
    # 显式保留 update_time，避免预约操作修改实验室的更新时间。
    db.execute(
        update(Lab)
        .where(Lab.id == data.lab_id)
        .values(id=Lab.id, update_time=Lab.update_time)
        .execution_options(synchronize_session=False)
    )
    lab = (
        db.query(Lab)
        .filter(Lab.id == data.lab_id)
        .populate_existing()
        .with_for_update()
        .first()
    )
    if not lab:
        raise BusinessException(message="实验室不存在")
    if lab.status != 1:
        raise BusinessException(message="实验室已关闭")
    if lab.open_time and start_time < datetime.strptime(lab.open_time, "%H:%M").time():
        raise BusinessException(message="预约时间不能早于实验室的开放时间")
    if lab.close_time and end_time > datetime.strptime(lab.close_time, "%H:%M").time():
        raise BusinessException(message="预约时间不能晚于实验室的关闭时间")

    # equipment_id 不为空 则表示这次是预约的实验室设备
    if data.equipment_id is not None:
        equipment = (
            db.query(Equipment)
            .filter(Equipment.id == data.equipment_id)
            .populate_existing()
            .with_for_update()
            .first()
        )
        if not equipment:
            raise BusinessException(message="实验室设备不存在")
        if equipment.lab_id != lab.id:
            raise BusinessException(message="该设备不属于所选实验室", code=400)
        if equipment.status != 1:
            raise BusinessException(message="实验室设备正在维修")

    # 实验室或者设备是否是可预约的状态
    query = db.query(Reservation).filter(
        Reservation.date == data.date,
        Reservation.status.in_([0, 1]),  # 0表示待审核 1已通过
        func.time(Reservation.start_time) < end_time.strftime("%H:%M:%S"),
        func.time(Reservation.end_time) > start_time.strftime("%H:%M:%S"),
    )
    if data.equipment_id is not None:
        query = query.filter(
            Reservation.equipment_id == data.equipment_id
        )  # 预约实验室设备
    else:
        query = query.filter(
            Reservation.lab_id == lab.id, Reservation.equipment_id.is_(None)
        )  # 只预约实验室
    # InnoDB 默认 REPEATABLE READ 下使用当前读，避免复用认证查询建立的旧快照。
    if query.with_for_update().first():
        raise BusinessException(message="该时段已预约", code=409)

    reservation_model = Reservation(
        user_id=current_user.id,
        lab_id=data.lab_id,
        equipment_id=data.equipment_id,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        remark=data.remark,
        status=0,
    )
    db.add(reservation_model)
    db.commit()


def cancel_reservation(db: Session, current_user: User, reservation_id: int):
    item = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not item:
        raise BusinessException(message="预约记录不存在")
    if item.user_id != current_user.id:
        raise BusinessException(message="无权限", code=403)
    if item.status != 0:
        raise BusinessException(message="当前状态无法取消")
    item.status = 3
    db.commit()


def audit_reservation(db: Session, reservation_id: int, status: int):
    """管理员审核预约"""
    if status not in [1, 2]:
        raise BusinessException(message="审核状态错误")
    item = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not item:
        raise BusinessException(message="预约记录不存在")
    if item.status != 0:
        raise BusinessException(message="当前状态不支持审核")
    item.status = status
    db.commit()


def expire_pending_reservations():
    """批量取消过期的预约"""
    db = SessionLocal()
    try:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M")
        items = db.query(Reservation).filter(Reservation.status == 0).all()
        changed = False
        for item in items:
            if item.date < today or (item.date == today and item.end_time <= time):
                item.status = 3
                changed = True
        if changed:
            db.commit()
    finally:
        db.close()


async def run_expire_scan():
    """扫描执行业务"""
    try:
        while True:
            await asyncio.to_thread(expire_pending_reservations)
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        return
