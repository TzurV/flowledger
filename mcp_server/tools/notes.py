from app.schemas import NoteCreate
from app.services import notes as note_svc
from mcp_server.db import SessionLocal
from mcp_server.serialize import note_dict


def register(mcp):
    @mcp.tool()
    def append_note(project_id: int, content: str) -> dict:
        """Add a note to a project.

        Notes are append-only freeform text — useful for recording context,
        decisions, or observations. Returns the created note.
        """
        with SessionLocal() as db:
            payload = NoteCreate(project_id=project_id, content=content)
            note = note_svc.create_note(db, payload)
            return note_dict(note)
