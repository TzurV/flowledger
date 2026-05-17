from app.models import Blocker, Note, Project, Task
from app.schemas import BlockerRead, NoteRead, ProjectRead, TaskRead


def project_dict(project: Project) -> dict:
    return ProjectRead.model_validate(project).model_dump(mode="json")


def task_dict(task: Task) -> dict:
    return TaskRead.model_validate(task).model_dump(mode="json")


def note_dict(note: Note) -> dict:
    return NoteRead.model_validate(note).model_dump(mode="json")


def blocker_dict(blocker: Blocker) -> dict:
    return BlockerRead.model_validate(blocker).model_dump(mode="json")
