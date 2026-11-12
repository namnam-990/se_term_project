from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """SQLAlchemy 객체를 그대로 반환해도 응답 DTO로 변환되도록 from_attributes 활성화."""

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    code: str
    message: str


class MessageResponse(BaseModel):
    message: str
