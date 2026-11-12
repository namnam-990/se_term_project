"""공통 예외 — Service는 이 예외만 raise 하고, main.py 핸들러가 {code, message} JSON으로 변환한다.

설계서 4장: 200 성공·201 가입 / 400 입력·401 인증·403 권한·404 없음·409 충돌.
오류 code 목록은 docs/api-contract.md 에 정리하고, 새 코드를 추가하면 문서도 함께 수정한다.
"""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = 400
    default_code: str = "BAD_REQUEST"

    def __init__(self, message: str, code: str | None = None, extra: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.extra = extra or {}


class BadRequestError(AppError):
    status_code, default_code = 400, "BAD_REQUEST"


class UnauthorizedError(AppError):
    status_code, default_code = 401, "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code, default_code = 403, "FORBIDDEN"


class NotFoundError(AppError):
    status_code, default_code = 404, "NOT_FOUND"


class ConflictError(AppError):
    status_code, default_code = 409, "CONFLICT"


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    body = {"code": exc.code, "message": exc.message, **exc.extra}
    return JSONResponse(status_code=exc.status_code, content=body)


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    return JSONResponse(
        status_code=400,
        content={
            "code": "VALIDATION_ERROR",
            "message": f"{field}: {first.get('msg', '입력값이 올바르지 않습니다.')}",
        },
    )
