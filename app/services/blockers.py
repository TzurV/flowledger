from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Blocker
from app.schemas import BlockerCreate, BlockerUpdate
from app.services.activity_log import log_activity


def list_blockers(
    db: Session,
    project_id: int | None = None,
    status_filter: str | None = None,
) -> list[Blocker]:
    stmt = select(Blocker)
    if project_id is not None:
        stmt = stmt.where(Blocker.project_id == project_id)
    if status_filter is not None:
        stmt = stmt.where(Blocker.status == status_filter)
    return db.scalars(stmt).all()


def get_blocker(db: Session, blocker_id: int) -> Blocker | None:
    return db.get(Blocker, blocker_id)


def create_blocker(db: Session, payload: BlockerCreate) -> Blocker:
    blocker = Blocker(**payload.model_dump())
    db.add(blocker)
    db.flush()
    log_activity(
        db,
        project_id=blocker.project_id,
        entity_type="blocker",
        entity_id=blocker.id,
        action="created",
        detail=blocker.description,
    )
    db.commit()
    db.refresh(blocker)
    return blocker


def update_blocker(db: Session, blocker: Blocker, payload: BlockerUpdate) -> Blocker:
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(blocker, key, value)
    detail = ", ".join(f"{k}={v}" for k, v in changes.items())
    log_activity(
        db,
        project_id=blocker.project_id,
        entity_type="blocker",
        entity_id=blocker.id,
        action="updated",
        detail=detail,
    )
    db.commit()
    db.refresh(blocker)
    return blocker


def resolve_blocker(db: Session, blocker: Blocker) -> Blocker:
    blocker.status = "resolved"
    blocker.resolved_at = datetime.now(timezone.utc)
    log_activity(
        db,
        project_id=blocker.project_id,
        entity_type="blocker",
        entity_id=blocker.id,
        action="resolved",
        detail=blocker.description,
    )
    db.commit()
    db.refresh(blocker)
    return blocker


def delete_blocker(db: Session, blocker: Blocker) -> None:
    log_activity(
        db,
        project_id=blocker.project_id,
        entity_type="blocker",
        entity_id=blocker.id,
        action="deleted",
        detail=blocker.description,
    )
    db.delete(blocker)
    db.commit()
