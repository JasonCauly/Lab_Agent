from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class ReservationCreateRequest(BaseModel):
    lab_id: int
    equipment_id: int | None = None
    date: str
    start_time: str
    end_time: str
    remark: str | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def normalize_time(cls, value: str) -> str:
        try:
            # 接受 9:00 等输入，统一为 09:00 后再交给业务层。
            return datetime.strptime(value, "%H:%M").strftime("%H:%M")
        except ValueError:
            raise ValueError("时间格式应为 HH:MM, 例如 09:00") from None


class ReservationResponse(BaseModel):
    id: int
    user_id: int
    user_name: str | None = None
    lab_id: int
    lab_name: str | None = None
    equipment_id: int | None = None
    equipment_name: str | None = None
    type: str | None = None
    date: str
    start_time: str
    end_time: str
    remark: str | None = None
    status: int

    model_config = ConfigDict(from_attributes=True)


class AuditReservationRequest(BaseModel):
    status: int  # 1 or 2
