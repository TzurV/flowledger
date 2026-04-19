# Step 3 — FastAPI CRUD API (Detailed Instructions)

## What you will learn in this step
- How SQLAlchemy's ORM maps Python classes to database tables
- How FastAPI dependency injection provides a DB session per request
- How Pydantic schemas validate request/response data separately from ORM models
- How to build full CRUD endpoints (Create, Read, Update, Delete)
- How to use HTTP status codes correctly (200, 201, 204, 404, 422)
- Why you keep schemas and ORM models separate

## Key design choices
- **SQLAlchemy 2.0 ORM** — typed `Mapped[...]` annotations, modern style
- **Sync, not async** — simpler mental model for learning. FastAPI runs sync code in a threadpool automatically.
- **psycopg v3** — modern Postgres driver for Python
- **Pydantic v2** — for request/response validation
- **Schema managed by SQL init scripts, not Python** — the tables already exist from Step 2. SQLAlchemy just reads/writes them.

---

## Sub-step 3.1 — Add dependencies

### Goal
Install the packages the API needs to talk to Postgres.

### What to do

From the repo root:

```bat
poetry add sqlalchemy "psycopg[binary]" pydantic-settings
```

### What to understand

**Why each package:**
- **`sqlalchemy`** — the ORM. Lets you write `db.add(project)` instead of raw `INSERT INTO...`. Also provides a query builder, connection pooling, and transaction management.
- **`psycopg[binary]`** — the actual Postgres driver. SQLAlchemy talks to this; this talks to Postgres over the wire. The `[binary]` extra installs a pre-compiled version so you don't need a C compiler. This is **psycopg v3** (not the older `psycopg2`).
- **`pydantic-settings`** — reads configuration from environment variables / `.env` files into a typed Python object. Cleaner than scattered `os.environ.get(...)` calls.

**What happens when you run `poetry add`:**
1. Poetry resolves compatible versions
2. Adds them to `pyproject.toml` under `dependencies`
3. Updates `poetry.lock` with exact versions
4. Installs them into `.venv/`

After this, glance at `pyproject.toml` to see the new entries.

### Checkpoint
`pyproject.toml` lists the three new packages. `poetry.lock` is updated.

---

## Sub-step 3.2 — Update `DATABASE_URL` in `.env`

### Goal
Tell SQLAlchemy which database driver to use via the URL scheme.

### What to do

Open `.env` and change the `DATABASE_URL` line from:

```env
DATABASE_URL=postgresql://flowledger:flowledger_dev@db:5432/flowledger
```

to:

```env
DATABASE_URL=postgresql+psycopg://flowledger:flowledger_dev@db:5432/flowledger
```

### What to understand

The URL scheme has two parts separated by `+`:
- `postgresql` — the database kind
- `psycopg` — the driver SQLAlchemy should use to talk to it

Without the `+psycopg` suffix, SQLAlchemy defaults to the older `psycopg2` driver, which isn't installed. This single change is what connects SQLAlchemy to the modern psycopg v3 you just installed.

### Checkpoint
`.env` has the new URL. The Postgres credentials are unchanged — only the driver prefix is different.

---

## Sub-step 3.3 — Configuration (`app/core/config.py`)

### Goal
Load `DATABASE_URL` (and future config values) into a typed Settings object.

### What to do

Open `app/core/config.py` (it already exists but is empty) and paste:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str


settings = Settings()
```

### What to understand

**What this class does:**
- `BaseSettings` is a special Pydantic model that automatically reads values from environment variables.
- `database_url: str` — Pydantic looks for an environment variable named `DATABASE_URL` (case-insensitive) and assigns it to this field.
- `env_file=".env"` — if the environment doesn't have the variable, Pydantic reads it from `.env`.
- `extra="ignore"` — if there are extra variables in `.env` (like `POSTGRES_USER`), don't raise an error.
- `settings = Settings()` — instantiate once at import time. Other modules will `from app.core.config import settings` and use `settings.database_url`.

**Why this pattern instead of `os.environ.get("DATABASE_URL")`:**
- **Typed:** `settings.database_url` is a `str` — your editor autocompletes it.
- **Validated:** if `DATABASE_URL` is missing, you get a clear Pydantic error at startup instead of a mysterious `None` crashing your code later.
- **Centralized:** all config is in one place.

### Checkpoint
`app/core/config.py` has the Settings class. You can verify by opening a Python shell inside the container later — but for now, just trust it and move on.

---

## Sub-step 3.4 — Database setup (`app/db.py`)

### Goal
Create the SQLAlchemy engine, session factory, a declarative base, and a FastAPI dependency that yields a DB session per request.

### What to do

Open `app/db.py` and paste:

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, echo=False, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### What to understand

**The engine:**
- `create_engine(settings.database_url)` — creates a connection pool to Postgres. Not a single connection; a pool that's shared across requests.
- `echo=False` — if `True`, SQLAlchemy logs every SQL statement. Flip this to `True` when you want to see exactly what queries are running. Great for learning.
- `future=True` — opt into SQLAlchemy 2.0 behavior (now the default, but explicit is nice).

**The session factory:**
- `sessionmaker(bind=engine, ...)` returns a class you call to get a new session.
- `SessionLocal()` gives you a Session object. Think of a session as "a conversation with the database" — you stage changes in it, then commit.
- `autoflush=False` — SQLAlchemy won't automatically send pending changes before every query. Keeps behavior predictable.
- `autocommit=False` — changes aren't saved until you explicitly call `db.commit()`. This is what you want — it lets you roll back on errors.

**The Base class:**
- `DeclarativeBase` is the SQLAlchemy 2.0 parent for all your ORM models.
- Every model (Project, Task, etc.) inherits from `Base`. This is how SQLAlchemy knows they're mapped to tables.

**The `get_db` dependency:**
- FastAPI has a feature called "dependency injection." Any route can declare `db: Session = Depends(get_db)` as a parameter, and FastAPI will call `get_db()` to provide it.
- The `yield` pattern is important: FastAPI calls the function, receives the yielded session, runs the route handler, then the `finally` block runs and closes the session.
- **One session per request.** This is the standard pattern. Each HTTP request gets a fresh session, uses it, then it's closed. No session leaks, no shared state between requests.

### Checkpoint
`app/db.py` has the engine, SessionLocal, Base, and `get_db`. The app can't run yet — we haven't created models, but nothing should break on import.

---

## Sub-step 3.5 — ORM models (`app/models.py`)

### Goal
Define Python classes that mirror each of the 5 tables from `001_schema.sql`.

### What to do

Create `app/models.py`:

```python
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]
    status: Mapped[str] = mapped_column(server_default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str]
    description: Mapped[str | None]
    status: Mapped[str] = mapped_column(server_default="todo")
    priority: Mapped[str] = mapped_column(server_default="medium")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    content: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Blocker(Base):
    __tablename__ = "blockers"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))
    description: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="open")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    resolved_at: Mapped[datetime | None]


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    entity_type: Mapped[str]
    entity_id: Mapped[int]
    action: Mapped[str]
    detail: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

### What to understand

**`__tablename__`:**
Must match the table name in Postgres exactly. SQLAlchemy uses this to route reads/writes to the correct table.

**`Mapped[type]`:**
This is SQLAlchemy 2.0 syntax. `Mapped[int]` tells both SQLAlchemy and your type checker that this column holds an int. `Mapped[str | None]` means "nullable string."

**`mapped_column(...)`:**
- `primary_key=True` — this column is the primary key.
- `unique=True` — enforces uniqueness at the DB level (already in the SQL schema; this just mirrors it).
- `ForeignKey("projects.id")` — declares a foreign key relationship. SQLAlchemy uses this for joins and validation.
- `server_default="active"` — the **database** fills in this default. That matches the SQL schema. Without `server_default`, SQLAlchemy would try to fill the default itself or leave the column empty.

**`server_default=func.now()`:**
- `func.now()` is SQLAlchemy's way of saying "the Postgres `now()` function." At insert time, Postgres fills the column with the current timestamp. Your Python code never needs to set `created_at`.

**Important: we are NOT using `Base.metadata.create_all()`.**
The tables already exist (created by `001_schema.sql`). SQLAlchemy just needs to know how they're shaped so it can read and write them. If you later make schema changes, you'll do them in SQL (or with Alembic later) — **not** by regenerating from these models.

**No `relationship()` defined yet:**
You could add `tasks: Mapped[list["Task"]] = relationship(back_populates="project")` to navigate from a project to its tasks. We're skipping this for now to keep things simple. We can add relationships later if needed.

### Checkpoint
`app/models.py` has 5 classes. Nothing is wired into the API yet.

---

## Sub-step 3.6 — Pydantic schemas (`app/schemas.py`)

### Goal
Define the shape of data going into and out of your API. Separate from ORM models.

### What to do

Create `app/schemas.py`:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ---------- Project ----------

class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    status: str = "active"


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


# ---------- Task ----------

class TaskCreate(BaseModel):
    project_id: int
    title: str
    description: str | None = None
    status: str = "todo"
    priority: str = "medium"


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    description: str | None
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime


# ---------- Note ----------

class NoteCreate(BaseModel):
    project_id: int
    content: str


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    content: str
    created_at: datetime


# ---------- Blocker ----------

class BlockerCreate(BaseModel):
    project_id: int
    task_id: int | None = None
    description: str
    status: str = "open"


class BlockerUpdate(BaseModel):
    description: str | None = None
    status: str | None = None
    task_id: int | None = None


class BlockerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    task_id: int | None
    description: str
    status: str
    created_at: datetime
    resolved_at: datetime | None


# ---------- ActivityLog ----------

class ActivityLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    entity_type: str
    entity_id: int
    action: str
    detail: str | None
    created_at: datetime
```

### What to understand

**Why three classes per entity (Create / Update / Read):**
- **Create** — fields the client must/may send to create a new record. No `id`, no `created_at` — the database generates those.
- **Update** — all fields are optional. The client sends only what they want to change.
- **Read** — the shape of what the API returns. Includes `id`, timestamps, and read-only fields.

**Why separate from ORM models:**
- ORM models represent database rows. They have internal state, relationships, lazy-loaded columns, etc.
- Pydantic schemas represent API contracts — what goes over the wire as JSON.
- Keeping them separate means you can change one without breaking the other. For example, you might later want to hide a column from the API while keeping it in the DB.

**`ConfigDict(from_attributes=True)`:**
- By default, Pydantic reads from dicts. This tells it: "also accept objects with attributes." That's what lets you pass a SQLAlchemy `Project` instance to `ProjectRead.model_validate(...)` and have it pull `project.id`, `project.name`, etc.
- In FastAPI, when you declare `response_model=ProjectRead`, FastAPI does this conversion automatically.

**Defaults:**
- `status: str = "active"` means the API accepts requests that omit `status` and substitutes `"active"`. This mirrors the DB default but happens at the API boundary, not the DB.
- `description: str | None = None` — the field is optional and defaults to `None`.

### Checkpoint
`app/schemas.py` has all the Pydantic classes.

---

## Sub-step 3.7 — Projects router (`app/routers/projects.py`)

### Goal
Full CRUD for projects. This is the template you'll copy for the other entities.

### What to do

Replace the contents of `app/routers/projects.py` (create it if not present):

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Project
from app.schemas import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    return db.scalars(select(Project)).all()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
```

### What to understand

**`APIRouter(prefix="/projects", tags=["projects"])`:**
- `prefix="/projects"` — every route in this file is automatically prefixed with `/projects`. So `@router.get("")` becomes `GET /projects`.
- `tags=["projects"]` — groups these endpoints together in the `/docs` Swagger UI.

**The five endpoints:**

**`GET /projects` (list):**
- `select(Project)` — build a SELECT statement for the Project table.
- `db.scalars(...)` — execute it and return model instances (not tuples).
- `.all()` — materialize the result into a list.
- `response_model=list[ProjectRead]` — tell FastAPI to convert each Project to a ProjectRead.

**`POST /projects` (create):**
- `payload: ProjectCreate` — FastAPI parses the request JSON, validates it against ProjectCreate, and hands you a validated object. If validation fails, FastAPI automatically returns 422.
- `Project(**payload.model_dump())` — create an ORM instance from the payload's fields.
- `db.add(project)` — stage for insert.
- `db.commit()` — send to Postgres.
- `db.refresh(project)` — reload the object from the DB so `id`, `created_at`, and `updated_at` (filled in by the DB) are populated.
- `status_code=201` — "Created" is the correct status for a successful POST that created a resource.

**`GET /projects/{project_id}` (get one):**
- `{project_id}` in the URL becomes a function parameter of type `int`. FastAPI validates the conversion.
- `db.get(Project, project_id)` — shortcut for "fetch by primary key." Returns `None` if not found.
- If not found, raise `HTTPException(404)`. FastAPI converts it into a proper HTTP response.

**`PATCH /projects/{project_id}` (partial update):**
- `PATCH` (not `PUT`) because the client may send only some fields.
- `exclude_unset=True` — only include fields the client actually sent. Fields they omitted stay at the DB value.
- `setattr(project, key, value)` — SQLAlchemy tracks the changes automatically once the object is in the session.

**`DELETE /projects/{project_id}`:**
- `status_code=204` — "No Content." Successful deletes return an empty body.

### Checkpoint
`app/routers/projects.py` is ready. Nothing is wired to `main.py` yet, so the routes aren't live.

---

## Sub-step 3.8 — Tasks router (`app/routers/tasks.py`)

### Goal
Same CRUD pattern, but for tasks. Also: support filtering by project.

### What to do

Create `app/routers/tasks.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Task
from app.schemas import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(
    project_id: int | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Task)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if status_filter is not None:
        stmt = stmt.where(Task.status == status_filter)
    return db.scalars(stmt).all()


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
```

### What to understand

**Query parameters:**
- `project_id: int | None = None` — this is a **query parameter**, not a path parameter. Because it's not in the URL path, FastAPI pulls it from the query string.
- Usage: `GET /tasks?project_id=1&status_filter=todo`
- `status_filter` is named that way because `status` is already imported from `fastapi` — avoid shadowing it.

**Conditional query building:**
- Start with a base `select(Task)` statement.
- Chain `.where(...)` calls only when the client provided the filter.
- SQLAlchemy composes these into a single SQL query with the appropriate `WHERE ... AND ...` clauses.

### Checkpoint
`app/routers/tasks.py` is ready.

---

## Sub-step 3.9 — Notes router (`app/routers/notes.py`)

### Goal
Notes don't typically get updated — they're freeform append-only. So we offer Create, Read, List, and Delete, but no Update.

### What to do

Create `app/routers/notes.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Note
from app.schemas import NoteCreate, NoteRead

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=list[NoteRead])
def list_notes(project_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Note)
    if project_id is not None:
        stmt = stmt.where(Note.project_id == project_id)
    return db.scalars(stmt).all()


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, db: Session = Depends(get_db)):
    note = Note(**payload.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/{note_id}", response_model=NoteRead)
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
```

### What to understand
- **Not everything needs full CRUD.** Notes are append-only in spirit. Exposing a PATCH would let users rewrite history. Deliberately omitting endpoints is a design choice, not an oversight.
- The resulting Swagger docs will make it clear to API consumers that notes are immutable.

### Checkpoint
`app/routers/notes.py` is ready.

---

## Sub-step 3.10 — Blockers router (`app/routers/blockers.py`)

### Goal
Full CRUD for blockers. Add a small custom endpoint to mark a blocker as resolved.

### What to do

Create `app/routers/blockers.py`:

```python
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
```

### What to understand

**The `/resolve` custom endpoint:**
- Not every API action fits neatly into CRUD. "Mark as resolved" is a domain action with meaning beyond "update status field."
- Using `POST /blockers/{id}/resolve` makes the intent explicit in the URL and lets you centralize the logic (setting both `status` and `resolved_at` at once).
- This is a small taste of **actions/commands** vs pure CRUD. You'll see more of this in Step 4 (service layer).

### Checkpoint
`app/routers/blockers.py` is ready.

---

## Sub-step 3.11 — Activity log router (`app/routers/activity_log.py`)

### Goal
Read-only endpoint for the audit trail.

### What to do

Create `app/routers/activity_log.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ActivityLog
from app.schemas import ActivityLogRead

router = APIRouter(prefix="/activity-log", tags=["activity_log"])


@router.get("", response_model=list[ActivityLogRead])
def list_activity(
    project_id: int | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(ActivityLog).order_by(ActivityLog.created_at.desc())
    if project_id is not None:
        stmt = stmt.where(ActivityLog.project_id == project_id)
    return db.scalars(stmt).all()
```

### What to understand

**Read-only by design:**
- No POST/PATCH/DELETE. The activity log is supposed to be written by the system, not by API clients directly.
- In Step 4 (service layer), you'll add automatic logging — when a task is created, a row is added to activity_log.
- `.order_by(ActivityLog.created_at.desc())` — newest first. Audit logs are most useful when you see the latest activity at the top.

### Checkpoint
`app/routers/activity_log.py` is ready.

---

## Sub-step 3.12 — Wire routers into `app/main.py`

### Goal
Tell FastAPI to include all the new routers.

### What to do

Replace `app/main.py` with:

```python
from fastapi import FastAPI

from app.routers import activity_log, blockers, notes, projects, tasks

app = FastAPI(
    title="FlowLedger API",
    version="0.1.0",
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "FlowLedger API is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(notes.router)
app.include_router(blockers.router)
app.include_router(activity_log.router)
```

### What to understand

**`app.include_router(...)`:**
- Each router is registered. All its endpoints become live at the prefix they declared.
- Order doesn't matter for routing, but it does affect the order of sections in Swagger UI (`/docs`).

**`/health` stays in `main.py`:**
- We created `app/routers/health.py` earlier as a placeholder, but leaving the health check at `/health` directly in `main.py` is fine. You can move it later if you prefer.

### Checkpoint
`app/main.py` includes all 5 routers.

---

## Sub-step 3.13 — Rebuild and test

### Goal
Run the updated stack and test every endpoint from Swagger UI.

### What to do

```bat
docker compose up --build
```

`--build` is required because you added new dependencies — the API image needs to be rebuilt so the new packages are installed inside the container.

Open in your browser:

```
http://localhost:8000/docs
```

You should see endpoints grouped by tag: **projects**, **tasks**, **notes**, **blockers**, **activity_log**.

### Test walkthrough

Do this in order from Swagger UI:

1. **`GET /projects`** → should return the two projects seeded from `002_seed.sql`.
2. **`POST /projects`** → create a new project with name `"test-project"`. Response: 201 + the full project with `id`, `created_at`, etc.
3. **`GET /projects/{id}`** → use the id from step 2. Should return the project.
4. **`PATCH /projects/{id}`** → send `{"description": "updated"}`. Response shows the updated description, other fields unchanged.
5. **`POST /tasks`** → create a task with `project_id` pointing to your test project.
6. **`GET /tasks?project_id={your_project_id}`** → should return only your task.
7. **`POST /blockers`** → create a blocker.
8. **`POST /blockers/{id}/resolve`** → watch `status` flip to "resolved" and `resolved_at` get filled in.
9. **`DELETE /projects/{id}`** → 204 response. Now the project is gone.
   - **Expected wrinkle:** if you created tasks/notes/blockers under this project, the delete will fail with a foreign key error. This is Postgres protecting you from orphaned data. We'll add cascade handling in a later step.

Open DBeaver and confirm your data matches what the API says.

### Troubleshooting

- **Container fails to start with "ModuleNotFoundError: No module named 'sqlalchemy'":** you forgot `--build`.
- **"Could not parse SQLAlchemy URL":** `.env` still has `postgresql://...` without `+psycopg`.
- **"connection refused":** Postgres isn't up yet. Check `docker compose logs db`.
- **Pydantic error on read:** a field type mismatch. Often a nullable column needs `| None`.

### Checkpoint
- `/docs` shows all routes
- You can create, read, update, delete through Swagger
- DBeaver confirms the data actually landed in Postgres

---

## Sub-step 3.14 — Commit

```bat
git add pyproject.toml poetry.lock app/
git status
git commit -m "Add FastAPI CRUD API with SQLAlchemy ORM"
```

If you changed `.env` as part of sub-step 3.2, it won't be staged (it's in `.gitignore`) — that's correct.

---

## Done criteria for Step 3

You are done when:
- `docker compose up --build` runs without errors
- `http://localhost:8000/docs` shows CRUD endpoints for projects, tasks, notes, blockers, and a read endpoint for activity_log
- You can create, read, update, delete data through Swagger UI
- DBeaver confirms changes are persisted in Postgres
- You understand: what the engine/session/dependency pattern does, why Pydantic schemas are separate from ORM models, why we use `server_default` for DB-managed values, and what each HTTP status code means (200, 201, 204, 404, 422)

---

## What to watch/read while doing this

In the order you'll need them:
1. **FastAPI SQL (Relational) Databases** tutorial — the official walkthrough of this exact pattern
2. **SQLAlchemy 2.0 ORM Quickstart** — focus on the Declarative + Mapped style
3. **Pydantic v2 overview** — focus on `BaseModel`, validators, and `from_attributes`
4. **Any "FastAPI + SQLAlchemy + Postgres" video tutorial** for a visual overview

---

## What comes after Step 3

**Step 4 — Shared service layer.** Right now, business logic lives in the route handlers. That works for simple CRUD but breaks down when you want to:
- automatically log to `activity_log` whenever something changes
- reuse logic between the HTTP API and the MCP server (Step 5)
- enforce business rules (e.g., "can't resolve a blocker on a resolved project")

Step 4 extracts logic into `app/services/` so both FastAPI routers and MCP tools can call the same underlying functions.
