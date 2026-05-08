from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import BlockerCreate, BlockerRead, BlockerUpdate
from app.services import blockers as svc

router = APIRouter(prefix="/blockers", tags=["blockers"])


@router.get("", response_model=list[BlockerRead])
def list_blockers(
    project_id: int | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    return svc.list_blockers(db, project_id=project_id, status_filter=status_filter)


@router.post("", response_model=BlockerRead, status_code=status.HTTP_201_CREATED)
def create_blocker(payload: BlockerCreate, db: Session = Depends(get_db)):
    return svc.create_blocker(db, payload)


@router.get("/{blocker_id}", response_model=BlockerRead)
def get_blocker(blocker_id: int, db: Session = Depends(get_db)):
    blocker = svc.get_blocker(db, blocker_id)
    if blocker is None:
        raise HTTPException(status_code=404, detail="Blocker not found")
    return blocker


@router.patch("/{blocker_id}", response_model=BlockerRead)
def update_blocker(
    blocker_id: int, payload: BlockerUpdate, db: Session = Depends(get_db)
):
    blocker = svc.get_blocker(db, blocker_id)
    if blocker is None:
        raise HTTPException(status_code=404, detail="Blocker not found")
    return svc.update_blocker(db, blocker, payload)


@router.post("/{blocker_id}/resolve", response_model=BlockerRead)
def resolve_blocker(blocker_id: int, db: Session = Depends(get_db)):
    blocker = svc.get_blocker(db, blocker_id)
    if blocker is None:
        raise HTTPException(status_code=404, detail="Blocker not found")
    return svc.resolve_blocker(db, blocker)


@router.delete("/{blocker_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_blocker(blocker_id: int, db: Session = Depends(get_db)):
    blocker = svc.get_blocker(db, blocker_id)
    if blocker is None:
        raise HTTPException(status_code=404, detail="Blocker not found")
    svc.delete_blocker(db, blocker)
