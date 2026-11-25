"""Admin Router — US-11 ~ 17 (Sprint 2). 설계서 4장 /api/admin/* — 전부 관리자 전용.

담당은 엔드포인트마다 다름 (sprint2-plan.md). Router는 HTTP 입출력만, 판단은 Service에서.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.csrf import verify_csrf
from app.core.database import get_db
from app.core.deps import require_admin
from app.models import User
from app.schemas.admin import (
    AdminCancelRequest,
    AdminUserItem,
    AdminUserListResponse,
    DashboardResponse,
    PolicyUpdateRequest,
    RestrictionSetRequest,
    RoleChangeRequest,
    StatisticsResponse,
)
from app.schemas.reservation import ReservationResponse
from app.schemas.seat import PolicyView
from app.services.admin_service import (
    AdminDashboardService,
    AdminReservationService,
    AdminUserService,
    StatisticsService,
)
from app.services.no_show_service import NoShowService
from app.services.policy_service import PolicyService
from app.services.restriction_service import RestrictionService

router = APIRouter(prefix="/api/admin", tags=["admin"])
csrf = [Depends(verify_csrf)]


# ───────────── US-11 강제 취소 ─────────────
@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=ReservationResponse,
    dependencies=csrf,
)
def admin_cancel(
    reservation_id: int,
    req: AdminCancelRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    return AdminReservationService(db, clock).cancel(admin, reservation_id, req)


# ───────────── US-12 대시보드 ─────────────
@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    return AdminDashboardService(db, clock).dashboard()


# ───────────── US-13 학생 목록·검색 ─────────────
@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    student_no: str | None = Query(default=None),
    seat_number: str | None = Query(default=None),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    return AdminUserService(db, clock).list_users(student_no=student_no, seat_number=seat_number)


# ───────────── US-14 이용 제한·노쇼 초기화 ─────────────
@router.put("/users/{user_id}/restriction", response_model=AdminUserItem, dependencies=csrf)
def set_restriction(
    user_id: int,
    req: RestrictionSetRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    user = RestrictionService(db, clock).set_manual(admin, user_id, req.until, req.reason)
    return AdminUserService(db, clock).to_item(user)


@router.delete("/users/{user_id}/restriction", response_model=AdminUserItem, dependencies=csrf)
def release_restriction(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    user = RestrictionService(db, clock).release(admin, user_id)
    return AdminUserService(db, clock).to_item(user)


@router.post("/users/{user_id}/no-shows/reset", response_model=AdminUserItem, dependencies=csrf)
def reset_no_shows(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    user = NoShowService(db, clock).reset(admin, user_id)
    return AdminUserService(db, clock).to_item(user)


# ───────────── US-15 운영 정책 ─────────────
# 화면 초기값은 기존 GET /api/policies/current(설계서: 인증 사용자 / US-04·15)를 그대로 쓴다.
@router.put("/policies/current", response_model=PolicyView, dependencies=csrf)
def update_policy(
    req: PolicyUpdateRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return PolicyService(db).update(req)


# ───────────── US-16 통계 (Could) ─────────────
@router.get("/statistics", response_model=StatisticsResponse)
def statistics(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    return StatisticsService(db, clock).statistics(from_date, to_date)


# ───────────── US-17 관리자 권한 (Could) ─────────────
@router.put("/users/{user_id}/role", response_model=AdminUserItem, dependencies=csrf)
def change_role(
    user_id: int,
    req: RoleChangeRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    return AdminUserService(db, clock).change_role(admin, user_id, req.role)
