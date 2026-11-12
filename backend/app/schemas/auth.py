"""US-01·02·03 DTO — 필드명은 docs/api-contract.md 와 일치시킨다."""

from pydantic import BaseModel, EmailStr, Field

from app.models import Role
from app.schemas.common import ORMModel


class SignupRequest(BaseModel):
    student_no: str = Field(min_length=4, max_length=20, examples=["202202644"])
    email: EmailStr
    password: str = Field(examples=["Passw0rd!"])
    name: str | None = Field(default=None, max_length=50)
    # 비밀번호 강도(8자↑·영문·숫자·특수문자) 검증은 AuthService에서 → 규칙 안내 메시지 통일


class SignupResponse(BaseModel):
    user_id: int
    account_status: str
    message: str


class EmailVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class LoginRequest(BaseModel):
    login_id: str = Field(examples=["202202644"])  # 학번 또는 관리자 ID
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    expires_in: int  # 초


class MeResponse(ORMModel):
    id: int
    login_id: str
    student_no: str | None
    email: str | None
    name: str | None
    role: Role
    account_status: str
