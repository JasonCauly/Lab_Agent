from pydantic import BaseModel, ConfigDict, Field


class LabResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    location: str | None = None
    img: str | None = None
    capacity: int
    open_time: str | None = None
    close_time: str | None = None
    status: bool

    model_config = ConfigDict(from_attributes=True)


class LabCreateRequest(BaseModel):
    name: str
    description: str | None = None
    img: str | None = None
    location: str | None = None
    capacity: int = Field(gt=0)
    open_time: str | None = None
    close_time: str | None = None
    status: bool = True


class LabUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    location: str | None = None
    img: str | None = None
    capacity: int | None = Field(default=None, gt=0)
    open_time: str | None = None
    close_time: str | None = None
    status: bool | None = None
