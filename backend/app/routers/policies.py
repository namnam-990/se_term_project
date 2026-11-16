"""Policy Router — 설계서 4장 GET /api/policies/current (인증 사용자, US-04 FR-R-03)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.seat import PolicyView
from app.services.policy_service import PolicyService

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("/current", response_model=PolicyView)
def current_policy(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PolicyService(db).current_view()
