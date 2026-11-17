"""US-01·02·03 DTO — 필드명은 docs/api-contract.md 와 일치시킨다."""

from pydantic import BaseModel, EmailStr, Field, model_validator

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
    """링크 인증: token만 / 코드 인증: email + code (D-03). 둘 중 하나는 반드시 있어야 함."""

    token: str | None = Field(default=None, description="메일 링크에 포함된 토큰")
    email: EmailStr | None = None
    code: str | None = Field(default=None, min_length=6, max_length=6)

    @model_validator(mode="after")
    def _token_or_code(self):
        if not self.token and not (self.email and self.code):
            raise ValueError("인증 링크 토큰 또는 이메일과 6자리 코드를 입력하세요.")
        return self


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
