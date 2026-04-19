from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ActivityLog
from app.schemas import ActivityLogRead

router = APIRouter(prefix="/activity-log", tags=["activity_log"])


@router.get("", response_model=list[ActivityLogRead])
def list_activity(
    project_id: int | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(ActivityLog).order_by(ActivityLog.created_at.desc())
    if project_id is not None:
        stmt = stmt.where(ActivityLog.project_id == project_id)
    return db.scalars(stmt).all()
