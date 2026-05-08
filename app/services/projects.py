from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project
from app.schemas import ProjectCreate, ProjectUpdate
from app.services.activity_log import log_activity


def list_projects(db: Session) -> list[Project]:
    return db.scalars(select(Project)).all()


def get_project(db: Session, project_id: int) -> Project | None:
    return db.get(Project, project_id)


def create_project(db: Session, payload: ProjectCreate) -> Project:
    project = Project(**payload.model_dump())
    db.add(project)
    db.flush()
    log_activity(
        db,
        project_id=project.id,
        entity_type="project",
        entity_id=project.id,
        action="created",
        detail=project.name,
    )
    db.commit()
    db.refresh(project)
    return project


def update_project(
    db: Session, project: Project, payload: ProjectUpdate
) -> Project:
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(project, key, value)
    detail = ", ".join(f"{k}={v}" for k, v in changes.items())
    log_activity(
        db,
        project_id=project.id,
        entity_type="project",
        entity_id=project.id,
        action="updated",
        detail=detail,
    )
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    log_activity(
        db,
        project_id=project.id,
        entity_type="project",
        entity_id=project.id,
        action="deleted",
        detail=project.name,
    )
    db.delete(project)
    db.commit()
