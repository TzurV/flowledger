from app.services import blockers as blocker_svc
from app.services import notes as note_svc
from app.services import projects as project_svc
from app.services import tasks as task_svc
from mcp_server.db import SessionLocal
from mcp_server.serialize import blocker_dict, note_dict, project_dict, task_dict


def register(mcp):
    @mcp.tool()
    def get_projects() -> list[dict]:
        """List all projects in FlowLedger.

        Returns each project's id, name, description, status, and timestamps.
        """
        with SessionLocal() as db:
            projects = project_svc.list_projects(db)
            return [project_dict(p) for p in projects]

    @mcp.tool()
    def get_project_context(project_id: int) -> dict:
        """Get a complete snapshot of one project.

        Returns the project's details plus all of its tasks, notes, and
        blockers. Use this to understand the current state of a project
        before planning or working on it.
        """
        with SessionLocal() as db:
            project = project_svc.get_project(db, project_id)
            if project is None:
                raise ValueError(f"Project {project_id} not found")

            tasks = task_svc.list_tasks(db, project_id=project_id)
            notes = note_svc.list_notes(db, project_id=project_id)
            blockers = blocker_svc.list_blockers(db, project_id=project_id)

            return {
                "project": project_dict(project),
                "tasks": [task_dict(t) for t in tasks],
                "notes": [note_dict(n) for n in notes],
                "blockers": [blocker_dict(b) for b in blockers],
            }
