from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.reservation import ReservationCreateRequest
from app.services import reservation_service

router = APIRouter(prefix="/reservation", tags=["预约服务接口"])


@router.post("")
def create_reservation(
    data: ReservationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reservation_service.create_reservation(data=data, current_user=current_user, db=db)
    return Response.success()
