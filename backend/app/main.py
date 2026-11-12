"""FastAPI 앱 진입점 — 라우터·예외 핸들러 등록만 한다."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.exceptions import AppError, app_error_handler, validation_error_handler
from app.routers import auth, pages, reservations, seats

app = FastAPI(title="LSRS — 도서관 좌석 예약 시스템", version="0.1.0")

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)


@app.exception_handler(NotImplementedError)
async def not_implemented_handler(_: Request, exc: NotImplementedError):
    """스켈레톤 단계: 아직 구현 안 된 기능은 501로 표시 (구현 완료 후에도 남겨둬도 무방)."""
    return JSONResponse(status_code=501, content={"code": "NOT_IMPLEMENTED", "message": str(exc)})


app.include_router(auth.router)
app.include_router(seats.router)
app.include_router(reservations.router)
app.include_router(pages.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}
