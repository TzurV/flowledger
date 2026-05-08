# Step 4 — Shared Service Layer (Detailed Instructions)

## What you will learn in this step
- Why separating business logic from HTTP routes matters
- How to structure service functions so both FastAPI and MCP can call them
- The difference between `db.flush()` and `db.commit()` — and why it matters for transactions
- How to write to `activity_log` automatically on every change
- What "HTTP-agnostic" service code looks like

## The core problem Step 4 solves

Right now your routers do two things at once: they handle HTTP (parse the request, return a response) **and** they contain all the business logic (DB inserts, updates, deletes).

That's fine for a simple CRUD app, but it breaks down in two important ways:

1. **Step 5 (MCP server)** will need to do the same operations — create tasks, update blockers, append notes — but it has no HTTP layer. If the logic lives in the router, MCP can't reuse it.
2. **Cross-cutting concerns** like writing to `activity_log` on every change need to happen in one place. If they're scattered across 5 routers, you'll forget them.

The fix: move all business logic into `app/services/`. Routers become thin — they parse HTTP, call a service function, return the result. MCP will do the same, just without the HTTP part.

```
Before:              After:
Router               Router
  └── DB logic         └── calls Service
                               └── DB logic
                               └── activity_log
```

---

## Sub-step 4.1 — Create the services folder

### What to do

```bat
mkdir app\services
type nul > app\services\__init__.py
```

### What to understand
`__init__.py` makes `app/services/` a Python package so you can do `from app.services import projects`.

### Checkpoint
`app/services/__init__.py` exists.

---

## Sub-step 4.2 — Activity log helper (`app/services/activity_log.py`)

### Goal
A single function that writes a row to `activity_log`. Every other service will call this.

### What to do

Create `app/services/activity_log.py`:

```python
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
```

### What to understand

**`db.flush()` vs `db.commit()`:**

This is an important concept. SQLAlchemy sessions have two stages:

- **`db.add(...)`** — tells the session "track this object, include it in the next flush."
- **`db.flush()`** — sends the pending SQL to Postgres **within the current transaction**, but does NOT commit. The row exists in the DB temporarily, but only within this transaction. If you roll back, it disappears.
- **`db.commit()`** — finalizes the transaction. All flushed changes become permanent.

Why `flush()` inside `log_activity` and not `commit()`?

Because the log entry should be **part of the same transaction** as the main change. If you're creating a project and then logging it, both should commit together — or neither should. Using `flush()` here (instead of `commit()`) means:
- The log entry is staged in the transaction
- The calling service function does `db.commit()` at the end
- Both the change and the log entry land in Postgres atomically
- If anything fails before commit, both are rolled back

**Keyword-only arguments (`*`):**

The `*` after `db: Session` forces all following arguments to be passed by name:

```python
log_activity(db, entity_type="project", entity_id=1, action="created")  # correct
log_activity(db, "project", 1, "created")  # TypeError — not allowed
```

This prevents bugs where you accidentally pass arguments in the wrong order.

### Checkpoint
`app/services/activity_log.py` is ready.

---

## Sub-step 4.3 — Projects service (`app/services/projects.py`)

### Goal
Move all project business logic into functions that take `db` + data, and return results — no HTTP concerns.

### What to do

Create `app/services/projects.py`:

```python
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
```

### What to understand

**`db.flush()` before logging:**
In `create_project`, the project is flushed before calling `log_activity`. Why? Because after `flush()`, Postgres has assigned an `id` to the project row. Without the flush, `project.id` would still be `None` (SQLAlchemy hasn't sent the INSERT yet). The flush gives you the id so you can reference it in the log entry.

**`update_project` and `delete_project` receive the already-fetched object:**
Notice these functions take a `Project` object, not a `project_id`. The router is responsible for fetching the object and checking it's not `None` — that's the one HTTP-facing concern that stays in the router. The service assumes it gets a valid object.

**Why this design:**
- `get_project` returning `None` (not raising `HTTPException`) keeps the service HTTP-agnostic.
- The router does: fetch → check None → raise 404 or call service.
- The MCP server will do the same: fetch → check None → return error to assistant.

### Checkpoint
`app/services/projects.py` is ready.

---

## Sub-step 4.4 — Tasks service (`app/services/tasks.py`)

### What to do

Create `app/services/tasks.py`:

```python
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
```

### Checkpoint
`app/services/tasks.py` is ready.

---

## Sub-step 4.5 — Notes service (`app/services/notes.py`)

### What to do

Create `app/services/notes.py`:

```python
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
```

### What to understand

**`note.content[:80]`:**
The activity log `detail` column is free text. Truncating note content to 80 characters keeps logs readable without storing the full note text twice.

### Checkpoint
`app/services/notes.py` is ready.

---

## Sub-step 4.6 — Blockers service (`app/services/blockers.py`)

### What to do

Create `app/services/blockers.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Blocker
from app.schemas import BlockerCreate, BlockerUpdate
from app.services.activity_log import log_activity


def list_blockers(
    db: Session,
    project_id: int | None = None,
    status_filter: str | None = None,
) -> list[Blocker]:
    stmt = select(Blocker)
    if project_id is not None:
        stmt = stmt.where(Blocker.project_id == project_id)
    if status_filter is not None:
        stmt = stmt.where(Blocker.status == status_filter)
    return db.scalars(stmt).all()


def get_blocker(db: Session, blocker_id: int) -> Blocker | None:
    return db.get(Blocker, blocker_id)


def create_blocker(db: Session, payload: BlockerCreate) -> Blocker:
    blocker = Blocker(**payload.model_dump())
    db.add(blocker)
    db.flush()
    log_activity(
        db,
        project_id=blocker.project_id,
        entity_type="blocker",
        entity_id=blocker.id,
        action="created",
        detail=blocker.description,
    )
    db.commit()
    db.refresh(blocker)
    return blocker


def update_blocker(db: Session, blocker: Blocker, payload: BlockerUpdate) -> Blocker:
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(blocker, key, value)
    detail = ", ".join(f"{k}={v}" for k, v in changes.items())
    log_activity(
        db,
        project_id=blocker.project_id,
        entity_type="blocker",
        entity_id=blocker.id,
        action="updated",
        detail=detail,
    )
    db.commit()
    db.refresh(blocker)
    return blocker


def resolve_blocker(db: Session, blocker: Blocker) -> Blocker:
    blocker.status = "resolved"
    blocker.resolved_at = datetime.now(timezone.utc)
    log_activity(
        db,
        project_id=blocker.project_id,
        entity_type="blocker",
        entity_id=blocker.id,
        action="resolved",
        detail=blocker.description,
    )
    db.commit()
    db.refresh(blocker)
    return blocker


def delete_blocker(db: Session, blocker: Blocker) -> None:
    log_activity(
        db,
        project_id=blocker.project_id,
        entity_type="blocker",
        entity_id=blocker.id,
        action="deleted",
    )
    db.delete(blocker)
    db.commit()
```

### Checkpoint
`app/services/blockers.py` is ready.

---

## Sub-step 4.7 — Update the routers to use service functions

### Goal
Make routers thin: parse HTTP → call service → return result. Remove all direct DB logic from routers.

### `app/routers/projects.py`

Replace the full file contents with:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import projects as svc

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    return svc.list_projects(db)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    return svc.create_project(db, payload)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = svc.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)
):
    project = svc.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return svc.update_project(db, project, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = svc.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    svc.delete_project(db, project)
```

### `app/routers/tasks.py`

Replace with:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import TaskCreate, TaskRead, TaskUpdate
from app.services import tasks as svc

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(
    project_id: int | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    return svc.list_tasks(db, project_id=project_id, status_filter=status_filter)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    return svc.create_task(db, payload)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = svc.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = svc.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return svc.update_task(db, task, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = svc.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    svc.delete_task(db, task)
```

### `app/routers/notes.py`

Replace with:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import NoteCreate, NoteRead
from app.services import notes as svc

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=list[NoteRead])
def list_notes(project_id: int | None = None, db: Session = Depends(get_db)):
    return svc.list_notes(db, project_id=project_id)


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, db: Session = Depends(get_db)):
    return svc.create_note(db, payload)


@router.get("/{note_id}", response_model=NoteRead)
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = svc.get_note(db, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = svc.get_note(db, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    svc.delete_note(db, note)
```

### `app/routers/blockers.py`

Replace with:

```python
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
```

### What to understand about the refactored routers

Each route handler now follows the same three-line pattern:
1. Call `svc.get_X()` to fetch the object
2. Check for `None` → raise 404
3. Call the appropriate service function and return the result

The routers no longer touch `db.add()`, `db.commit()`, `db.flush()`, or `db.refresh()`. All of that lives in the service layer. Routers only know about HTTP.

### Checkpoint
All four routers updated. No route handler imports SQLAlchemy operations directly.

---

## Sub-step 4.8 — Rebuild and test

### What to do

The stack is already running in detached mode. Because you changed Python source files (which are bind-mounted into the container), you do **not** need to rebuild the image. Restart the API container to pick up the changes:

```bat
docker compose restart api
```

Then open `http://localhost:8000/docs` and test:

**Create something and check the activity log:**

1. `POST /projects` — create a project named `"step-4-test"`
2. `GET /activity-log` — you should see a new row with `entity_type="project"`, `action="created"`, `detail="step-4-test"`
3. `PATCH /projects/{id}` — send `{"status": "paused"}`
4. `GET /activity-log` — a new row with `action="updated"`, `detail="status=paused"`
5. `POST /tasks` — create a task under that project
6. `GET /activity-log` — another row with `entity_type="task"`, `action="created"`
7. `POST /blockers/{id}/resolve` on an existing blocker
8. `GET /activity-log` — row with `entity_type="blocker"`, `action="resolved"`

**Confirm in DBeaver:**
Open the `activity_log` table — you should see all the rows that the API created. The `project_id`, `entity_type`, `entity_id`, `action`, and `detail` columns should all be populated correctly.

### Troubleshooting

- **Import error on restart:** check that `app/services/__init__.py` exists.
- **`project.id` is `None` after create:** you likely missed `db.flush()` before calling `log_activity`.
- **Activity log rows not appearing:** check the service function — did you call `db.flush()` before `log_activity` and `db.commit()` after?

### Checkpoint
- All CRUD operations work as before
- Every create/update/delete/resolve action produces a row in `activity_log`
- DBeaver confirms the data

---

## Sub-step 4.9 — Commit

```bat
git add app/services/ app/routers/
git status
git commit -m "Add shared service layer with automatic activity logging"
```

---

## Done criteria for Step 4

You are done when:
- `app/services/` exists with 5 files: `activity_log.py`, `projects.py`, `tasks.py`, `notes.py`, `blockers.py`
- All routers delegate to service functions — no `db.add/commit/flush` in router files
- Every create, update, delete, and resolve action writes a row to `activity_log`
- The API behaviour from the outside is identical to before (same endpoints, same responses)
- You understand: why service functions are HTTP-agnostic, what `flush()` vs `commit()` means, and why the log entry and the main change commit together

---

## What to watch/read while doing this

- **"Clean Architecture" short explanations** — search YouTube for "clean architecture Python" or "service layer pattern Python". You don't need the full book; a 10–15 minute video on separating concerns is enough.
- **SQLAlchemy Sessions docs** — specifically the "flushing" section. It explains the flush/commit lifecycle clearly.

---

## What comes after Step 4

**Step 5 — Separate MCP server.** You'll create `mcp/server.py` with tool definitions that AI coding assistants (Claude Code, ChatGPT, Gemini) can call. Because the service layer is now HTTP-agnostic, MCP tools will call the exact same service functions the routers do — no duplication of logic. This is why you built the service layer first.
