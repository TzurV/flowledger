# Step 5 — Separate MCP Server (Detailed Instructions)

## What you will learn in this step
- What MCP (Model Context Protocol) is and why it exists
- How an AI coding assistant calls "tools" exposed by a server
- How to build an MCP server in Python with the official SDK (`FastMCP`)
- How the MCP server reuses your Step 4 service layer — zero logic duplication
- Why the MCP server runs on the host (not in Docker) and what that means for the database connection
- How to validate an MCP server before wiring it into an assistant

---

## Background: what is MCP?

**MCP (Model Context Protocol)** is an open standard that lets AI assistants talk to external systems through a uniform interface. Instead of every assistant inventing its own plugin format, MCP defines one protocol.

An **MCP server** exposes capabilities. The main kind you'll use:
- **Tools** — functions the assistant can call (e.g. `create_task`, `get_projects`). Each tool has a name, a description, typed inputs, and a return value.

An **MCP client** is the assistant (Claude Code, etc.). It launches the server, asks "what tools do you have?", and calls them when useful.

**Transport** — how client and server talk. The standard for local tools is **stdio**: the assistant launches the server as a subprocess and exchanges JSON-RPC messages over standard input/output. That is what you'll use.

### The big picture for FlowLedger

```
Claude Code  ──stdio──>  mcp_server  ──>  app.services.*  ──>  Postgres
(MCP client)             (MCP server)     (Step 4 layer)       (localhost:5432)
```

The key insight: **the MCP server contains almost no logic of its own.** It just exposes your Step 4 service functions as tools. This is exactly why you built the service layer first — both FastAPI and MCP call the same `app.services.*` functions.

---

## Two important decisions before you start

### Decision 1 — The folder is named `mcp_server/`, not `mcp/`

The original plan reserved a folder called `mcp/`. There is a problem: **the official Python SDK's package is also named `mcp`.** If you name your folder `mcp/` and make it a Python package, `import mcp` becomes ambiguous — Python may find your folder instead of the SDK, and `from mcp.server.fastmcp import FastMCP` breaks.

To avoid this name collision, the server lives in **`mcp_server/`**. You will also delete the old empty `mcp/` folder.

This is a real, common lesson: **don't name your own packages the same as a library you depend on.**

### Decision 2 — The MCP server runs on the host, not in Docker

Your API runs inside Docker. The MCP server is different: the coding assistant **launches it as a subprocess** on your machine. So it runs on the host (Windows), not in a container.

That changes the database address:
- Inside Docker, the API reaches Postgres at `db:5432` (the Compose service name).
- On the host, the MCP server reaches Postgres at `localhost:5432` (the published port).

So the MCP server needs its **own** database URL. You'll add `MCP_DATABASE_URL` for that.

**Prerequisite for everything below:** Postgres must be running. Start the stack if it isn't:

```bat
docker compose up -d
```

---

## Sub-step 5.1 — Add the MCP dependency

### Goal
Install the official MCP Python SDK.

### What to do

From the repo root:

```bat
poetry add "mcp[cli]"
```

### What to understand
- `mcp` is the official Model Context Protocol SDK for Python. It includes `FastMCP`, a high-level way to build servers by decorating functions.
- The `[cli]` extra adds the `mcp` command-line tool, which includes **MCP Inspector** — a browser-based UI for testing your server. You'll use it for validation in Sub-step 5.9.
- Poetry adds the package to `pyproject.toml` and pins it in `poetry.lock`.

### Validate this stage

```bat
poetry run python -c "from mcp.server.fastmcp import FastMCP; print('mcp SDK ok')"
```

Expected output: `mcp SDK ok`. If you get an `ImportError`, the install didn't complete.

---

## Sub-step 5.2 — Add the host-facing database URL

### Goal
Give the MCP server its own connection string pointing at `localhost`.

### What to do

**(a)** Open `.env` and add this line at the bottom:

```env
# Connection string used by the MCP server, which runs on the host (not in Docker).
# It reaches Postgres through the published port on localhost.
MCP_DATABASE_URL=postgresql+psycopg://flowledger:flowledger_dev@localhost:5432/flowledger
```

**(b)** Open `app/core/config.py` and add the new field:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    mcp_database_url: str


settings = Settings()
```

### What to understand
- `database_url` (`@db:5432`) is used by code running **inside Docker** — the API.
- `mcp_database_url` (`@localhost:5432`) is used by code running **on the host** — the MCP server.
- Both live in the same `.env`. The same `Settings` class loads both. Each consumer picks the one it needs.
- The API container will also load `mcp_database_url` into its environment — it simply never uses it. That's harmless.

### Validate this stage

```bat
poetry run python -c "from app.core.config import settings; print(settings.mcp_database_url)"
```

Expected output: `postgresql+psycopg://flowledger:flowledger_dev@localhost:5432/flowledger`

If you see a `ValidationError`, the `.env` line is missing or misspelled.

---

## Sub-step 5.3 — Create the `mcp_server` package and its database session

### Goal
Make `mcp_server/` a Python package and give it a database engine + session factory pointed at the host URL.

### What to do

**(a)** Remove the stale empty folder and create the new structure:

```bat
rmdir mcp
mkdir mcp_server
mkdir mcp_server\tools
type nul > mcp_server\__init__.py
type nul > mcp_server\tools\__init__.py
```

**(b)** Create `mcp_server/db.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# The MCP server runs on the host (the coding assistant launches it as a
# subprocess), so it reaches Postgres through the published port on localhost,
# NOT through the Docker network name "db".
engine = create_engine(settings.mcp_database_url, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
```

### What to understand

**Why a separate `db.py` instead of reusing `app/db.py`:**
- `app/db.py` builds its engine from `settings.database_url` — the `@db:5432` URL. That only resolves inside Docker.
- The MCP server needs an engine built from `settings.mcp_database_url` — the `@localhost:5432` URL.
- So `mcp_server/db.py` has its own `engine` and `SessionLocal`.

**Why the service layer still works unchanged:**
Your Step 4 service functions all take `db: Session` as a parameter. They don't care which engine the session came from. The MCP server creates a `Session` from *its* `SessionLocal` and passes it in. This is the payoff of dependency injection — the service layer is decoupled from any specific database connection.

**A subtle detail:** importing `app.services.*` transitively imports `app.db`, which builds the `@db:5432` engine. That engine is created but never *connected* (SQLAlchemy engines are lazy). The MCP server simply ignores it and uses `mcp_server/db.py`'s engine instead. No error, no connection attempt.

### Validate this stage

Make sure Postgres is running (`docker compose up -d`), then:

```bat
poetry run python -c "from sqlalchemy import text; from mcp_server.db import engine; print(engine.connect().execute(text('SELECT 1')).scalar())"
```

Expected output: `1`

This proves the host can reach Postgres on `localhost:5432`. If it hangs or errors:
- `docker compose ps` — is the `db` service up?
- Is port `5432` published? (Check `compose.yaml` has `"5432:5432"`.)

---

## Sub-step 5.4 — Create the serialization helpers

### Goal
Convert SQLAlchemy model objects into plain JSON-serializable dictionaries. MCP tools must return JSON-friendly data, not ORM objects.

### What to do

Create `mcp_server/serialize.py`:

```python
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
```

### What to understand

- A SQLAlchemy `Project` object is not JSON-serializable — it has internal state and a `datetime` field.
- You already have Pydantic schemas (`ProjectRead`, etc.) from Step 3. They were built for exactly this: turning model objects into clean output.
- `ProjectRead.model_validate(project)` — reads the model's attributes into a Pydantic object (this works because the schemas have `from_attributes=True`).
- `.model_dump(mode="json")` — converts to a dict, and crucially `mode="json"` turns `datetime` values into ISO-8601 strings so the result is fully JSON-serializable.
- Reusing the API schemas means the MCP output and the HTTP API output have the **same shape**. One source of truth for "what a project looks like."

**Important — serialize while the session is open.** You must call these helpers *before* the database session closes. After the session closes, accessing model attributes raises `DetachedInstanceError`. Every tool below does its serialization inside the `with SessionLocal() as db:` block.

### Validate this stage

```bat
poetry run python -c "from mcp_server import serialize; print('serialize ok')"
```

Expected output: `serialize ok`

---

## Sub-step 5.5 — Project tools (`mcp_server/tools/projects.py`)

### Goal
Two tools: list all projects, and get a full snapshot of one project.

### What to do

Create `mcp_server/tools/projects.py`:

```python
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
```

### What to understand

**The `register(mcp)` pattern:**
Each tool module defines a `register` function that takes the `FastMCP` instance and decorates tools onto it. `server.py` (Sub-step 5.8) creates the instance and calls every module's `register`. This keeps tools organized by topic in separate files instead of one giant file.

**`@mcp.tool()`:**
- This decorator registers the function as an MCP tool.
- FastMCP reads the function **signature** to build the tool's input schema. `project_id: int` becomes a required integer input.
- FastMCP reads the **docstring** to build the tool's description — this is what the assistant sees when deciding whether to call the tool. Write docstrings as if explaining the tool to the assistant, because that's literally what they are.

**`with SessionLocal() as db:`:**
- Opens a database session, and closes it automatically when the block ends.
- Each tool call gets its own short-lived session — the same "one unit of work" idea as the API's `get_db` dependency.

**Raising `ValueError`:**
- When a project isn't found, the tool raises `ValueError`. FastMCP catches exceptions and reports them back to the assistant as a tool error. The assistant sees a clear message instead of a crash.

**No logic duplication:**
Look at the tool bodies — they only call `app.services.*` functions and serialize the result. All the real work (queries, activity logging, transactions) lives in the service layer you built in Step 4.

### Validate this stage

```bat
poetry run python -c "from mcp_server.tools import projects; print('project tools ok')"
```

Expected output: `project tools ok` (this checks the file imports cleanly — it can't run the tools yet because there's no `FastMCP` instance until Sub-step 5.8).

---

## Sub-step 5.6 — Task tools (`mcp_server/tools/tasks.py`)

### Goal
Three tools: list open tasks, create a task, update a task's status.

### What to do

Create `mcp_server/tools/tasks.py`:

```python
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
```

### What to understand

**`get_open_tasks` filters in Python:**
The service's `list_tasks` can filter by one exact status, but "open" means "any status except done." So the tool fetches the tasks and filters `t.status != "done"` in Python. Filtering happens inside the `with` block — the session must still be open to read `t.status`.

**Building schema objects:**
`create_task` constructs a `TaskCreate` from the tool's arguments, then hands it to `task_svc.create_task`. The Pydantic schema validates the data the same way it would for an HTTP request. The MCP path and the HTTP path converge on the same validation and the same service function.

**`update_task_status` is fetch → check → act:**
Exactly the pattern your routers use. Fetch the task, raise if missing, call the service. The service function also writes to `activity_log` automatically (Step 4), so MCP-driven changes are audited just like API-driven ones.

**Default arguments become optional inputs:**
`description: str | None = None` and `priority: str = "medium"` have defaults, so FastMCP marks them as optional inputs in the tool schema. The assistant can omit them.

### Validate this stage

```bat
poetry run python -c "from mcp_server.tools import tasks; print('task tools ok')"
```

Expected output: `task tools ok`

---

## Sub-step 5.7 — Note tools (`mcp_server/tools/notes.py`)

### Goal
One tool: append a note to a project.

### What to do

Create `mcp_server/tools/notes.py`:

```python
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
```

### What to understand
- This mirrors the notes router from Step 3: notes are append-only, so there's a create tool but no update tool.
- `note_svc.create_note` writes the note **and** an `activity_log` row, in one transaction (Step 4).

### Validate this stage

```bat
poetry run python -c "from mcp_server.tools import notes; print('note tools ok')"
```

Expected output: `note tools ok`

---

## Sub-step 5.8 — The server entrypoint (`mcp_server/server.py`)

### Goal
Create the `FastMCP` instance, register all tools, and run the server.

### What to do

Create `mcp_server/server.py`:

```python
from mcp.server.fastmcp import FastMCP

from mcp_server.tools import notes, projects, tasks

mcp = FastMCP("flowledger")

projects.register(mcp)
tasks.register(mcp)
notes.register(mcp)


def main() -> None:
    # FastMCP.run() defaults to the stdio transport: it reads JSON-RPC
    # messages from stdin and writes responses to stdout. That is exactly
    # what a coding assistant expects when it launches the server.
    mcp.run()


if __name__ == "__main__":
    main()
```

### What to understand

**`FastMCP("flowledger")`:**
Creates the server. `"flowledger"` is the server's name — the assistant sees it as the identity of this tool source.

**Registration order:**
Calling each module's `register(mcp)` is what actually attaches the six tools to the server. The decorators inside `register` run at this point.

**`mcp.run()` and stdio:**
With no arguments, `run()` uses the **stdio transport**. The server reads requests from standard input and writes responses to standard output. This is why **you must never `print()` to stdout** in an MCP server — stdout is the protocol channel. If you need to debug-log, log to stderr (FastMCP already does this correctly).

**`if __name__ == "__main__"`:**
Lets you run the file directly. The assistant will launch it with `python -m mcp_server.server`, which also triggers `main()`.

### Validate this stage

**Import check:**

```bat
poetry run python -c "from mcp_server.server import mcp; print('server imports ok')"
```

Expected: `server imports ok`

**List the registered tools:**

```bat
poetry run python -c "import asyncio; from mcp_server.server import mcp; print([t.name for t in asyncio.run(mcp.list_tools())])"
```

Expected output (order may vary):

```
['get_projects', 'get_project_context', 'get_open_tasks', 'create_task', 'update_task_status', 'append_note']
```

If all six tool names appear, the server is correctly assembled.

---

## Sub-step 5.9 — Validate the server end-to-end

### Goal
Confirm the server actually starts and that tools return real data.

### Option A — Run the server directly

```bat
poetry run python -m mcp_server.server
```

The server starts and then sits silently, waiting for JSON-RPC input on stdin. **Silence is success** — it means no import or startup errors. Press `Ctrl+C` to stop it.

If it instead prints a traceback and exits, fix the error before continuing.

### Option B — MCP Inspector (recommended, interactive)

The Inspector is a browser UI for poking at your tools manually. Run:

```bat
poetry run mcp dev mcp_server/server.py
```

This launches the Inspector (it uses Node's `npx` under the hood — if you don't have Node installed, use Option A plus the Step 6 live test instead).

In the Inspector:
1. Click **Connect**.
2. Open the **Tools** tab — you should see all six tools with their descriptions.
3. Run **`get_projects`** — it should return the seed projects (`flowledger`, `investment-tool`).
4. Run **`get_project_context`** with `project_id = 1` — you should get the project plus its tasks, notes, and blockers.
5. Run **`append_note`** with `project_id = 1` and some content — then check DBeaver: the note row and an `activity_log` row should both appear.

### What this proves
- The server speaks MCP correctly.
- Tools reach Postgres on the host and return real data.
- Writes go through the Step 4 service layer, so `activity_log` is updated automatically.

### Checkpoint
Server starts cleanly; the Inspector (or Option A) confirms the six tools are present and `get_projects` returns data.

---

## Sub-step 5.10 — Commit

```bat
git add pyproject.toml poetry.lock app/core/config.py mcp_server/
git status
git commit -m "Add MCP server exposing FlowLedger tools via the service layer"
```

`.env` is in `.gitignore`, so your new `MCP_DATABASE_URL` line is not committed — correct. (If you keep a `.env.example`, add the `MCP_DATABASE_URL` line there too.)

---

## Done criteria for Step 5

You are done when:
- `mcp_server/` exists with `db.py`, `serialize.py`, `server.py`, and `tools/` (`projects.py`, `tasks.py`, `notes.py`)
- `poetry run python -m mcp_server.server` starts without errors
- Listing tools shows all six: `get_projects`, `get_project_context`, `get_open_tasks`, `create_task`, `update_task_status`, `append_note`
- A tool call (via the Inspector) returns real data from Postgres
- A write tool (`append_note` / `create_task`) produces an `activity_log` row
- You understand: what MCP is, why the server runs on the host with a `localhost` DB URL, why the folder is `mcp_server` not `mcp`, and how the tools reuse the Step 4 service layer with no duplicated logic

---

## What to watch/read while doing this
- **MCP introduction** — search for "Model Context Protocol explained" for a short conceptual video.
- **Official MCP Python SDK docs** — the `FastMCP` quickstart shows the `@mcp.tool()` pattern you used here.
- **"Build an MCP server" walkthrough videos** — several exist for Python; focus on ones using `FastMCP` and stdio.

---

## What comes after Step 5

**Step 6 — Assistant-specific configuration.** The server works, but no assistant is using it yet. Step 6 wires `mcp_server` into Claude Code (via a project-scoped `.mcp.json` or `claude mcp add`), so that Claude Code can call `get_open_tasks`, `create_task`, and the rest while you work. You'll then do the same for other assistants to prove FlowLedger is genuinely assistant-agnostic.
