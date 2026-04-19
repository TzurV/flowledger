# Step 2 — Database-First Design (Detailed Instructions)

## What you will learn in this step
- How Docker Compose orchestrates multiple services (Postgres + API)
- How a Dockerfile builds your Python app into a container
- How `.env` passes configuration into containers
- How SQL schema defines your data model
- How Postgres stores the truth for your system
- How to inspect your database with DBeaver

---

## Sub-step 2.1 — Create the `.env` file

### Goal
Move all environment-specific values out of code into one file. Docker Compose will read this file and inject the values as environment variables into your containers.

### What to do
Create `.env` in the repo root with this content:

```env
# Postgres
POSTGRES_USER=flowledger
POSTGRES_PASSWORD=flowledger_dev
POSTGRES_DB=flowledger

# Connection string used by the API to reach Postgres
# "db" is the Compose service name — inside the Docker network, services find each other by name
DATABASE_URL=postgresql://flowledger:flowledger_dev@db:5432/flowledger
```

### What to understand
- **These are not secrets for production.** This is your local dev environment. In production you would use a secrets manager.
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` are special variables that the official Postgres Docker image reads on first startup to create the database and user automatically.
- `DATABASE_URL` is a connection string your Python code will use later. The `@db` part is the hostname — inside Docker Compose, each service can reach another service by its service name. Your Postgres service will be named `db`.
- `.env` is already in your `.gitignore`, so it won't be committed. This is correct — config with passwords should not go into git.

### Checkpoint
You should have a `.env` file at the repo root. It won't do anything yet on its own.

---

## Sub-step 2.2 — Create the Postgres init schema

### Goal
Write the SQL that defines your data model. Postgres will run this automatically when the container starts for the first time.

### What to do

Create the folder structure:

```bat
mkdir docker
mkdir docker\postgres
mkdir docker\postgres\init
```

Then create the file `docker/postgres/init/001_schema.sql` with this content:

```sql
-- FlowLedger schema v1
-- This file runs automatically when the Postgres container starts for the first time.
-- The official Postgres Docker image looks for .sql files in /docker-entrypoint-initdb.d/
-- and executes them in alphabetical order. That is why the file is prefixed with 001_.

CREATE TABLE projects (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tasks (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    title       TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'todo',
    priority    TEXT NOT NULL DEFAULT 'medium',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notes (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE blockers (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    task_id     INTEGER REFERENCES tasks(id),
    description TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE activity_log (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER REFERENCES projects(id),
    entity_type TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    action      TEXT NOT NULL,
    detail      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### What to understand

**Table design:**
- `projects` — top-level container. Everything belongs to a project.
- `tasks` — work items. Each task belongs to one project (`project_id` is a foreign key). Status values like `todo`, `in_progress`, `done` will be enforced later in application code.
- `notes` — freeform text attached to a project. No status — just content and a timestamp.
- `blockers` — things preventing progress. Can optionally link to a specific task. Has its own status (`open`/`resolved`) and a `resolved_at` timestamp.
- `activity_log` — audit trail. Records what changed, when, and on which entity. This is write-only — you never update a log row.

**SQL concepts to notice:**
- `SERIAL PRIMARY KEY` — auto-incrementing integer ID. Postgres assigns the next number automatically on insert.
- `REFERENCES projects(id)` — foreign key constraint. Postgres will reject inserts if the referenced project doesn't exist. This protects data integrity at the database level.
- `NOT NULL` — the column must have a value. Postgres will reject inserts that leave it blank.
- `DEFAULT 'active'` — if you don't provide a value, Postgres fills in this default.
- `TIMESTAMPTZ` — timestamp with timezone. `now()` is a Postgres function that returns the current time.
- `UNIQUE` on `projects.name` — no two projects can have the same name.

**How it runs automatically:**
The official Postgres Docker image has a special behavior: on first startup (when the data directory is empty), it looks for `.sql` and `.sh` files in `/docker-entrypoint-initdb.d/` and executes them in alphabetical order. In your `compose.yaml` (next step), you will mount `docker/postgres/init/` to that path. The `001_` prefix lets you add more files later (`002_seed.sql`, etc.) and control the order.

### Checkpoint
You should have `docker/postgres/init/001_schema.sql`. It doesn't do anything yet — it needs Compose to mount it.

---

## Sub-step 2.3 — Create `compose.yaml`

### Goal
Define the local development stack: which services run, how they connect, and what data persists.

### What to do
Create `compose.yaml` in the repo root:

```yaml
services:
  db:
    image: postgres:17
    env_file: .env
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./docker/postgres/init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U flowledger"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build: .
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./app:/code/app

volumes:
  pgdata:
```

### What to understand

**The `db` service (Postgres):**
- `image: postgres:17` — pulls the official Postgres 17 image from Docker Hub. You don't build this yourself; you use the community-maintained image.
- `env_file: .env` — Compose reads your `.env` file and injects all variables as environment variables into the container. This is how Postgres gets `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`.
- `ports: "5432:5432"` — maps port 5432 inside the container to port 5432 on your machine. This is how DBeaver (running on your host) can connect.
- `volumes` — two mounts:
  - `pgdata:/var/lib/postgresql/data` — a **named volume**. Postgres stores all its data files here. Because it's a named volume, your data survives `docker compose down`. If you do `docker compose down -v`, the volume is deleted and the database starts fresh.
  - `./docker/postgres/init:/docker-entrypoint-initdb.d` — a **bind mount**. Maps your local `docker/postgres/init/` folder into the container path where Postgres looks for init scripts. This is how `001_schema.sql` gets executed on first startup.
- `healthcheck` — Compose runs `pg_isready` every 5 seconds inside the container. This checks if Postgres is actually accepting connections, not just that the container started. Other services can wait for this before starting.

**The `api` service (your FastAPI app):**
- `build: .` — tells Compose to build an image from the `Dockerfile` in the current directory (you'll create this next).
- `env_file: .env` — your API gets `DATABASE_URL` from here.
- `ports: "8000:8000"` — maps the API port so you can reach it from your browser.
- `depends_on` with `condition: service_healthy` — Compose will not start the API until the Postgres healthcheck passes. Without this, the API might start before Postgres is ready and fail to connect.
- `volumes: ./app:/code/app` — a bind mount that maps your local `app/` folder into the container. This means you can edit code on your machine and see changes without rebuilding the container. This is a **development convenience** — in production you would not do this.

**The `volumes:` section at the bottom:**
- `pgdata:` — declares the named volume. Docker manages where this is stored on disk. You don't need to know the exact path.

**How services find each other:**
Inside the Docker Compose network, each service is reachable by its service name as a hostname. Your API container can connect to Postgres at `db:5432` — that's why `DATABASE_URL` in `.env` uses `@db:5432`, not `@localhost:5432`. From your host machine (browser, DBeaver), you still use `localhost`.

### Checkpoint
You should have `compose.yaml` at the repo root. You can't run it yet — you need the Dockerfile first.

---

## Sub-step 2.4 — Create the `Dockerfile`

### Goal
Define how to build your API into a Docker container image.

### What to do
Create `Dockerfile` in the repo root:

```dockerfile
FROM python:3.12-slim

# Install Poetry
RUN pip install poetry

# Set working directory inside the container
WORKDIR /code

# Copy dependency files first (for better caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies without creating a virtualenv
# Inside a container there's only one Python, so a venv adds no value
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction

# Copy the application code
COPY app ./app

# Expose the port FastAPI will listen on
EXPOSE 8000

# Start the API server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### What to understand

**Why this file exists:**
A Dockerfile is a recipe for building a container image. Each line is an instruction. Docker executes them top-to-bottom, and each instruction creates a layer. Layers are cached — if a layer hasn't changed, Docker reuses the cached version. This is why the file is structured the way it is.

**Line by line:**
- `FROM python:3.12-slim` — start from an official Python image. `slim` is a smaller variant without build tools you don't need. This is your base operating system + Python.
- `RUN pip install poetry` — install Poetry inside the container so it can install your dependencies.
- `WORKDIR /code` — set the working directory. All subsequent commands run from `/code`. It's created automatically.
- `COPY pyproject.toml poetry.lock ./` — copy only the dependency files first. This is a deliberate ordering trick: Docker caches layers, so if your dependencies haven't changed, the next `RUN` step is cached and skips the slow install.
- `RUN poetry config virtualenvs.create false && poetry install --no-root` — install packages directly into the container's Python, not into a venv. Inside a container there's only one app running, so a venv adds no benefit. `--no-root` means "don't install the project itself as a package."
- `COPY app ./app` — copy your application code. This comes after dependency install so that code changes don't invalidate the dependency cache.
- `EXPOSE 8000` — documentation that this container listens on port 8000. It doesn't actually open the port — `ports:` in Compose does that.
- `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` — the command that runs when the container starts. `--host 0.0.0.0` means "listen on all network interfaces" so it's reachable from outside the container. In Step 1, `fastapi dev` used `127.0.0.1` which only works on the same machine.

**Why `uvicorn` directly instead of `fastapi dev`?**
`fastapi dev` is a convenience CLI for local development. In a container, you use Uvicorn directly because it gives you explicit control. In production you would also add `--workers` for multiple processes, but for dev this is fine.

### Checkpoint
You should have a `Dockerfile` at the repo root. Now you have everything to run the stack.

---

## Sub-step 2.5 — Start the stack

### Goal
Run everything and confirm it works.

### What to do

Open a terminal in the repo root and run:

```bat
docker compose up --build
```

**What `--build` does:** forces Docker to rebuild the API image. Without it, Docker uses a cached image if one exists, which would miss your code changes.

**What you should see:**
1. Docker pulls the `postgres:17` image (first time only, takes a minute)
2. Docker builds your API image from the Dockerfile
3. Postgres starts and runs `001_schema.sql`
4. The healthcheck passes
5. The API starts and shows Uvicorn logs

**Test in your browser:**
- `http://localhost:8000/health` — should return `{"status":"ok"}`
- `http://localhost:8000/docs` — Swagger UI should open

**To stop the stack:** press `Ctrl+C` in the terminal, then `docker compose down`.

**To nuke the database and start fresh:** `docker compose down -v` (the `-v` deletes the `pgdata` volume, so the init script runs again next time).

### Checkpoint
Both services running, API responding, Postgres healthy.

---

## Sub-step 2.6 — Connect DBeaver to Postgres

### Goal
See your tables in a GUI database tool to confirm the schema was created.

### What to do
1. Open DBeaver
2. Create a new connection: **PostgreSQL**
3. Use these settings:
   - Host: `localhost`
   - Port: `5432`
   - Database: `flowledger`
   - Username: `flowledger`
   - Password: `flowledger_dev`
4. Click "Test Connection" — should succeed
5. Navigate to: `flowledger` > `Schemas` > `public` > `Tables`

**You should see:**
- `projects`
- `tasks`
- `notes`
- `blockers`
- `activity_log`

Right-click any table > "View Table" or "Read Data" to see the structure. The tables will be empty, which is correct.

### What to understand
You're connecting from your host machine to the Postgres container through the port mapping (`5432:5432` in Compose). DBeaver uses `localhost` because you're outside the Docker network. Your API container uses `db` because it's inside the Docker network. Same database, two access paths.

### Checkpoint
DBeaver connected, five tables visible, all empty.

---

## Sub-step 2.7 — Insert seed data (optional but recommended)

### Goal
Put some example data in so you have something to look at and query.

### What to do
Create `docker/postgres/init/002_seed.sql`:

```sql
-- Seed data for local development

INSERT INTO projects (name, description) VALUES
    ('flowledger', 'Developer Project OS — the system itself'),
    ('investment-tool', 'Investment Management Assistant — future project');

INSERT INTO tasks (project_id, title, status, priority) VALUES
    (1, 'Set up Docker Compose', 'done', 'high'),
    (1, 'Design database schema', 'done', 'high'),
    (1, 'Build FastAPI CRUD routes', 'todo', 'high'),
    (1, 'Create MCP server', 'todo', 'medium');

INSERT INTO notes (project_id, content) VALUES
    (1, 'Using Postgres 17, Poetry for deps, FastAPI for the API layer.');

INSERT INTO blockers (project_id, task_id, description, status) VALUES
    (1, 3, 'Need to decide on SQLAlchemy vs raw SQL for data access', 'open');

INSERT INTO activity_log (project_id, entity_type, entity_id, action, detail) VALUES
    (1, 'project', 1, 'created', 'Project created'),
    (1, 'task', 1, 'created', 'Task: Set up Docker Compose'),
    (1, 'task', 1, 'status_changed', 'todo -> done');
```

**Important:** Because Postgres init scripts only run on first startup, you need to destroy the volume to re-run them:

```bat
docker compose down -v
docker compose up --build
```

Then check in DBeaver — the tables should now have data.

### What to understand
- `002_seed.sql` runs after `001_schema.sql` because of alphabetical order.
- The `project_id` values (1, 2) rely on `SERIAL` starting at 1. This is fine for seed data.
- `REFERENCES` constraints mean you must insert projects before tasks/notes/blockers that reference them.

### Checkpoint
DBeaver shows rows in all tables. You can write SQL queries against real data.

---

## Sub-step 2.8 — Commit this checkpoint

### What to do

```bat
git add compose.yaml Dockerfile docker/
git status
git commit -m "Add Docker Compose stack with Postgres and schema"
```

Note: `.env` is already in `.gitignore` so it won't be committed. This is correct.

### Optional: add `.env.example`

To let other developers (or your future self) know what values `.env` needs, you can create a `.env.example` file in the repo root:

```env
POSTGRES_USER=flowledger
POSTGRES_PASSWORD=flowledger_dev
POSTGRES_DB=flowledger
DATABASE_URL=postgresql://flowledger:flowledger_dev@db:5432/flowledger
```

If you create it, commit it separately:

```bat
git add .env.example
git commit -m "Add .env.example for reference"
```

This is a common pattern — the example file is committed, the real `.env` is not.

---

## Done criteria for Step 2

You are done when:
- `docker compose up --build` starts Postgres and the API without errors
- `http://localhost:8000/health` returns `{"status":"ok"}`
- DBeaver connects to Postgres and shows all five tables
- The schema matches the data model: projects, tasks, notes, blockers, activity_log
- You understand: what `compose.yaml` does, why the Dockerfile is ordered the way it is, how init scripts run, and how services find each other by name

---

## What to watch/read while doing this

In the order you'll need them:
1. **Docker Compose quickstart** — any short video showing a Python + Postgres setup
2. **Official Postgres Docker image docs** — specifically the "Initialization scripts" section to understand `/docker-entrypoint-initdb.d/`
3. **Dockerfile best practices** — focus on layer caching and the `COPY dependencies first` pattern
4. **DBeaver getting started** — a short walkthrough on connecting to Postgres

---

## What comes after Step 2

**Step 3 — FastAPI CRUD API.** You'll add `app/db.py` (database connection), `app/models.py` or `app/schemas.py` (Pydantic models for request/response), and `app/routers/` with actual routes to create, read, update, and delete projects, tasks, notes, and blockers through HTTP.
