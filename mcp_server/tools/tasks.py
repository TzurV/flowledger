from app.schemas import TaskCreate, TaskUpdate
from app.services import tasks as task_svc
from mcp_server.db import SessionLocal
from mcp_server.serialize import task_dict


def register(mcp):
    @mcp.tool()
    def get_open_tasks(project_id: int | None = None) -> list[dict]:
        """List tasks that are not yet done (status is not 'done').

        Pass project_id to limit the result to a single project, or omit it
        to get open tasks across all projects.
        """
        with SessionLocal() as db:
            tasks = task_svc.list_tasks(db, project_id=project_id)
            return [task_dict(t) for t in tasks if t.status != "done"]

    @mcp.tool()
    def create_task(
        project_id: int,
        title: str,
        description: str | None = None,
        priority: str = "medium",
    ) -> dict:
        """Create a new task in a project.

        priority is one of 'low', 'medium', or 'high'. Returns the new task.
        """
        with SessionLocal() as db:
            payload = TaskCreate(
                project_id=project_id,
                title=title,
                description=description,
                priority=priority,
            )
            task = task_svc.create_task(db, payload)
            return task_dict(task)

    @mcp.tool()
    def update_task_status(task_id: int, status: str) -> dict:
        """Update the status of a task.

        status is typically 'todo', 'in_progress', or 'done'. Returns the
        updated task.
        """
        with SessionLocal() as db:
            task = task_svc.get_task(db, task_id)
            if task is None:
                raise ValueError(f"Task {task_id} not found")
            updated = task_svc.update_task(db, task, TaskUpdate(status=status))
            return task_dict(updated)
