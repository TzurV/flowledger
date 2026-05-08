from sqlalchemy.orm import Session

from app.models import ActivityLog


def log_activity(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: str,
    project_id: int | None = None,
    detail: str | None = None,
) -> None:
    entry = ActivityLog(
        project_id=project_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        detail=detail,
    )
    db.add(entry)
    db.flush()
