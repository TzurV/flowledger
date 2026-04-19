from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Blocker
from app.schemas import BlockerCreate, BlockerRead, BlockerUpdate

router = APIRouter(prefix="/blockers", tags=["blockers"])


@router.get("", response_model=list[BlockerRead])
def list_blockers(
    project_id: int | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Blocker)
    if project_id is not None:
        stmt = stmt.where(Blocker.project_id == project_id)
    if status_filter is not None:
        stmt = stmt.where(Blocker.status == status_filter)
    return db.scalars(stmt).all()


@router.post("", response_model=BlockerRead, status_code=status.HTTP_201_CREATED)
def create_blocker(payload: BlockerCreate, db: Session = Depends(get_db)):
    blocker = Blocker(**payload.model_dump())
    db.add(blocker)
    db.commit()
    db.refresh(blocker)
    return blocker


@router.get("/{blocker_id}", response_model=BlockerRead)
def get_blocker(blocker_id: int, db: Session = Depends(get_db)):
    blocker = db.get(Blocker, blocker_id)
    if blocker is None:
        raise HTTPException(status_code=404, detail="Blocker not found")
    return blocker


@router.patch("/{blocker_id}", response_model=BlockerRead)
def update_blocker(
    blocker_id: int, payload: BlockerUpdate, db: Session = Depends(get_db)
):
    blocker = db.get(Blocker, blocker_id)
    if blocker is None:
        raise HTTPException(status_code=404, detail="Blocker not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(blocker, key, value)
    db.commit()
    db.refresh(blocker)
    return blocker


@router.post("/{blocker_id}/resolve", response_model=BlockerRead)
def resolve_blocker(blocker_id: int, db: Session = Depends(get_db)):
    blocker = db.get(Blocker, blocker_id)
    if blocker is None:
        raise HTTPException(status_code=404, detail="Blocker not found")
    blocker.status = "resolved"
    blocker.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(blocker)
    return blocker


@router.delete("/{blocker_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_blocker(blocker_id: int, db: Session = Depends(get_db)):
    blocker = db.get(Blocker, blocker_id)
    if blocker is None:
        raise HTTPException(status_code=404, detail="Blocker not found")
    db.delete(blocker)
    db.commit()
