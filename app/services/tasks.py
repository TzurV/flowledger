from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Task
from app.schemas import TaskCreate, TaskUpdate
from app.services.activity_log import log_activity


def list_tasks(
    db: Session,
    project_id: int | None = None,
    status_filter: str | None = None,
) -> list[Task]:
    stmt = select(Task)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if status_filter is not None:
        stmt = stmt.where(Task.status == status_filter)
    return db.scalars(stmt).all()


def get_task(db: Session, task_id: int) -> Task | None:
    return db.get(Task, task_id)


def create_task(db: Session, payload: TaskCreate) -> Task:
    task = Task(**payload.model_dump())
    db.add(task)
    db.flush()
    log_activity(
        db,
        project_id=task.project_id,
        entity_type="task",
        entity_id=task.id,
        action="created",
        detail=task.title,
    )
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, task: Task, payload: TaskUpdate) -> Task:
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(task, key, value)
    detail = ", ".join(f"{k}={v}" for k, v in changes.items())
    log_activity(
        db,
        project_id=task.project_id,
        entity_type="task",
        entity_id=task.id,
        action="updated",
        detail=detail,
    )
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task) -> None:
    log_activity(
        db,
        project_id=task.project_id,
        entity_type="task",
        entity_id=task.id,
        action="deleted",
        detail=task.title,
    )
    db.delete(task)
    db.commit()
