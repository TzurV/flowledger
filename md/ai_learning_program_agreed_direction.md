# AI Learning Program — Agreed Direction

## Goal
Build a **hands-on personal learning program** for AI engineering that is centered on **real projects**, mainly developed in **VS Code**, while learning how to work effectively with **multiple AI services** rather than relying on a single one.

## Constraints and Preferences
- Time budget: about **4 hours per week**
- Preferred format: **watch / see / run / modify**, not long reading
- Learning style: **project-first**, with courses and examples supporting the work
- Tools should stay **generic and reusable**, not tied to one assistant or vendor

## Agreed Direction
### Phase 1 project: **Developer Project OS**
This will be the first project.

It should act as a **central system for tasks, progress, notes, blockers, and context** across coding projects.

It should be:
- usable from a **web interface**
- usable from **VS Code** through AI assistants
- built as an **API-first** system
- designed so different assistants can **read and update it**
- generic enough to support later projects, especially the investment tool

### Phase 2 project: **Investment Management Assistant**
Once the Developer Project OS is in place, it will be used as the working environment and workflow backbone for building the investment tool.

## Why this order
Starting with the Developer Project OS gives:
- a smaller, cleaner first build
- faster feedback loops
- direct learning about agent workflows, tools, integrations, and task orchestration
- a reusable foundation for the more valuable but more complex investment project

## High-Level Design Principles for Project A
The Developer Project OS should be built around these principles:

1. **One source of truth**
   - central backend/service for tasks, notes, progress, status, and metadata

2. **Multi-surface access**
   - web UI for humans
   - API access for tools and automations
   - AI-accessible interface for coding assistants

3. **Assistant-agnostic design**
   - should work with ChatGPT, Claude Code, Gemini Code Assist, and other compatible tools
   - avoid building core workflows that depend on one single chat product

4. **MCP / tool-based integration mindset**
   - expose functionality in a way that AI coding assistants can consume through tools or MCP-style access

5. **Small but real product**
   - not a toy demo
   - should be useful in daily coding work

## Recommended AI Service Roles
The plan is not to use every AI chat equally, but to assign roles.

### Core stack
- **Primary coding agent:** Claude Code
- **Secondary coding agent / comparison:** ChatGPT tools or GitHub Copilot / Codex
- **Third perspective / diversity:** Gemini Code Assist
- **Research / up-to-date lookup:** Perplexity or equivalent search-grounded tool
- **Optional model-agnostic workflow tool:** Cline or Aider

### Principle
Use more than one service, but avoid unnecessary switching. Each service should have a role.

## Learning Sources — Preferred Types
Because the preferred style is visual and hands-on, learning sources should be selected in this order:

1. **Video-led practical courses**
2. **Interactive tutorials / built-in lessons**
3. **Example repos / cookbooks / working demos**
4. **Docs only as reference when needed**

## High-Level Learning Program Structure
### Stage 1 — Environment and workflow setup
Focus on:
- setting up the working environment in VS Code
- deciding which assistants are in the core toolchain
- defining how Project OS will be accessed from web and from code assistants

### Stage 2 — Build the minimum useful Project OS
Focus on:
- tasks
- project notes
- progress tracking
- blocker tracking
- basic web access
- basic API access

### Stage 3 — Add AI-facing integrations
Focus on:
- allowing assistants to read project state
- allowing assistants to update tasks and progress
- making the system assistant-agnostic
- shaping workflows that work across more than one LLM/service

### Stage 4 — Improve usability and reliability
Focus on:
- better organization
- clearer workflow patterns
- small automations
- logging, traceability, and useful guardrails

### Stage 5 — Use Project OS to build the Investment Management Assistant
Once the Project OS is functional, use it as the coordination layer for the investment tool work.

## Success Criteria for Project A
Project A is successful when:
- it is genuinely useful during coding work
- it can be opened in the browser and updated there
- it can be read and updated from VS Code workflows
- at least two different AI coding assistants can use it in practice
- it becomes the place where Project B is managed

## What comes later
After Project A is in place, the next major build is:
- the **Investment Management Assistant**
- using the Project OS as the planning, task, and progress system for that work

## Summary of the Agreed Plan
- Start with **Developer Project OS**
- Keep it **generic, web-accessible, and assistant-agnostic**
- Use it to learn AI engineering through building
- Use multiple AI services with **clear roles**, not randomly
- Prefer **video/lab/example-based learning** over long reading
- After Project A is useful, use it to build **Investment Management Assistant**

## Revised Implementation Direction for Project A
### Chosen v1 stack
- **FastAPI** for backend and API
- **Postgres from day one**
- **Docker Compose from day one**
- **Separate MCP server** for coding assistants
- **Web UI deferred** until API and MCP are working
- **Poetry** for dependency management and virtual environments

### Explicitly deferred for now
- **Alembic** migrations
- choosing a UI framework such as **NiceGUI** or **Streamlit**
- richer in-app LLM behavior beyond tool access

## Revised Build Order
### Step 1 — Repo and runtime skeleton
Goal:
- make the system runnable end-to-end with containers
- understand what runs where

Main topics:
- Docker Compose
- environment variables
- service boundaries
- Poetry project structure

Planned artifacts:
- `compose.yaml`
- `.env`
- `pyproject.toml`
- `app/`
- `mcp/`
- `docker/postgres/init/`
- `tests/`

Learning source types:
- Docker Compose walk-throughs
- Postgres-in-Docker demos
- Poetry setup/tutorial videos

### Step 2 — Database-first design
Goal:
- understand exactly what the system stores and how Postgres fits in

Main topics:
- tables
- relationships
- SQL schema
- inspecting data with DBeaver

Initial tables:
- `projects`
- `tasks`
- `notes`
- `blockers`
- `activity_log`

Planned artifacts:
- `docker/postgres/init/001_schema.sql`
- optional seed SQL

Learning source types:
- hands-on Postgres schema tutorials
- Docker Postgres examples
- DBeaver walkthroughs

### Step 3 — FastAPI CRUD API
Goal:
- expose the data through a clean backend API

Main topics:
- routes
- request/response schemas
- validation
- API docs
- HTTP basics

Planned artifacts:
- `app/main.py`
- `app/db.py`
- `app/models.py`
- `app/schemas.py`
- `app/routers/`

Learning source types:
- FastAPI project videos
- example repos
- short API testing demos

### Step 4 — Shared service layer
Goal:
- separate transport from business logic

Main topics:
- service functions
- business rules
- reuse between API and MCP

Planned artifacts:
- `app/services/`

Key principle:
- FastAPI and MCP should both call the same service logic

Learning source types:
- backend architecture videos
- practical clean-architecture examples

### Step 5 — Separate MCP server
Goal:
- let coding assistants read and update Project OS directly

Main topics:
- MCP concepts
- tool definitions
- assistant-facing interfaces
- safe tool boundaries

Planned artifacts:
- `mcp/server.py`
- `mcp/tools/`

Example tools:
- `get_projects`
- `get_open_tasks`
- `create_task`
- `update_task_status`
- `append_note`
- `get_project_context`

Learning source types:
- MCP walkthrough videos
- Claude Code MCP examples
- hands-on tutorials

### Step 6 — Assistant-specific configuration
Goal:
- understand how assistants actually connect to your tools

Main topics:
- config files
- MCP server registration
- project-level vs user-level setup

Examples to explore:
- Claude Code
- ChatGPT / Codex workflows
- Gemini Code Assist later if useful

Learning source types:
- configuration walkthroughs
- product-specific MCP setup demos

### Step 7 — Decide on UI later
Goal:
- add convenience only after the backend and MCP foundation are real

Options to revisit later:
- NiceGUI
- Streamlit
- another lightweight frontend if needed

Decision rule:
- only choose UI after the API and MCP workflows are genuinely useful

## Technology Understanding Focus
This project is meant to teach not just "how to get code written" but what exists beneath the hood:
- where the data lives
- how Postgres stores the truth
- how Docker Compose runs the services
- how FastAPI exposes the system through HTTP
- how MCP exposes tools to coding assistants
- how configuration files connect assistants to those tools
- how Poetry manages dependencies and environments

## Expected v1 File/Folder View
- `pyproject.toml`
- `poetry.lock`
- `compose.yaml`
- `.env`
- `docker/postgres/init/`
- `app/`
- `app/routers/`
- `app/services/`
- `mcp/`
- `mcp/tools/`
- `tests/`

## Working Rule Going Forward
For each implementation step, discuss:
1. **goal**
2. **main technologies involved**
3. **key files/folders**
4. **what happens under the hood**
5. **best learning sources in video / demo / example form**

## Step 1 — Repo and Runtime Skeleton (Detailed Breakdown)
### Step 1 goal
The goal of Step 1 is not to build features yet.
It is to make the project **runnable, understandable, and inspectable**:
- one repo
- one command to start the local stack
- clear separation between app code, database, config, and later MCP
- Poetry managing Python dependencies and the virtual environment
- Docker Compose managing runtime services

By the end of this step, the aim is to understand:
- what runs on the host machine vs inside containers
- where dependencies live
- where environment variables are read from
- how the API process finds Postgres
- what files define the project shape

### Step 1 expected output
Suggested initial repo skeleton:
- `pyproject.toml`
- `poetry.lock`
- `.env`
- `compose.yaml`
- `Dockerfile`
- `app/main.py`
- `app/__init__.py`
- `app/core/config.py`
- `app/db.py`
- `app/routers/__init__.py`
- `mcp/`
- `tests/`
- `README.md`
- `.gitignore`

### Key files and what they are for
#### `pyproject.toml`
- Python project manifest
- managed by Poetry
- defines metadata, Python version, and dependencies

#### `poetry.lock`
- exact resolved dependency versions
- supports repeatable installs

#### `.env`
- runtime configuration
- database host, port, name, username, password
- environment-specific settings

#### `compose.yaml`
- defines the local multi-container stack
- initial services: `postgres` and `api`
- later can include `mcp`

#### `Dockerfile`
- defines how the API container is built
- base Python image
- installs dependencies
- copies project files
- starts FastAPI / Uvicorn

#### `app/main.py`
- FastAPI entrypoint
- creates the app object
- registers initial routes

#### `app/core/config.py`
- central settings/config access
- loads environment-driven configuration

#### `app/db.py`
- database connectivity setup
- later hosts SQLAlchemy engine/session wiring

#### `app/routers/`
- home for API route modules as the app grows

#### `mcp/`
- reserved home for the future separate MCP server
- keeps AI-facing integration as a first-class architectural boundary

#### `tests/`
- reserved home for automated tests
- included from day one to make testing part of the design

### Poetry-specific decision
Use an **in-project virtual environment** so the environment lives inside the repo as `.venv/`.

Why:
- easier to see which interpreter belongs to the project
- easier for VS Code to pick up
- less confusion when switching projects

### What happens under the hood
#### When Poetry runs
- Poetry reads `pyproject.toml`
- resolves dependencies
- creates or uses a virtual environment
- installs packages into that environment

#### When Docker Compose runs
- Compose reads `compose.yaml`
- starts each service as its own container
- creates a local network between services
- each service can reach the others by service name

In this setup:
- `postgres` container runs PostgreSQL
- `api` container runs FastAPI
- the API connects to Postgres using the Compose service name, not localhost, from inside the container network

From the host machine:
- DBeaver connects to Postgres through the exposed port
- browser/Postman/curl connects to FastAPI through its exposed port
- later, coding assistants connect to the MCP server through its configured transport

### Main concepts to understand in Step 1
1. **Project manifest**
   - `pyproject.toml`
   - declares the Python project and dependencies

2. **Runtime config**
   - `.env`
   - provides the running app with environment-specific values

3. **Service orchestration**
   - `compose.yaml`
   - defines which services exist and how they connect

4. **Application entrypoint**
   - `app/main.py`
   - the Python process that becomes the API server

5. **Future AI tool boundary**
   - `mcp/`
   - dedicated space for the separate MCP server

### Suggested sub-steps inside Step 1
#### 1. Create the Poetry project
Goal:
- get `pyproject.toml`, local `.venv`, and dependency management in place

#### 2. Add the FastAPI skeleton
Goal:
- create a tiny API app with one simple route such as `/health`

#### 3. Add `compose.yaml`
Goal:
- define `postgres` and `api` as separate services

#### 4. Add the API Dockerfile
Goal:
- make the API container buildable and runnable

#### 5. Add `.env`
Goal:
- move configuration out of code

#### 6. Add empty `mcp/` and `tests/`
Goal:
- lock in the architecture from the start

### Definition of done for Step 1
Step 1 is done when:
- `poetry install` works
- the correct Python interpreter is used
- `docker compose up` starts Postgres and the API
- opening the API URL returns a response
- DBeaver can connect to the Postgres container
- the repo structure clearly shows where API, DB, tests, and MCP code will live

### Best source types for Step 1
Use:
- Poetry setup videos
- FastAPI “first API” videos
- Docker Compose Python walkthroughs
- official docs only as reference when needed

