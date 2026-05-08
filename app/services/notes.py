from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Note
from app.schemas import NoteCreate
from app.services.activity_log import log_activity


def list_notes(db: Session, project_id: int | None = None) -> list[Note]:
    stmt = select(Note)
    if project_id is not None:
        stmt = stmt.where(Note.project_id == project_id)
    return db.scalars(stmt).all()


def get_note(db: Session, note_id: int) -> Note | None:
    return db.get(Note, note_id)


def create_note(db: Session, payload: NoteCreate) -> Note:
    note = Note(**payload.model_dump())
    db.add(note)
    db.flush()
    log_activity(
        db,
        project_id=note.project_id,
        entity_type="note",
        entity_id=note.id,
        action="created",
        detail=note.content[:80],
    )
    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, note: Note) -> None:
    log_activity(
        db,
        project_id=note.project_id,
        entity_type="note",
        entity_id=note.id,
        action="deleted",
    )
    db.delete(note)
    db.commit()

