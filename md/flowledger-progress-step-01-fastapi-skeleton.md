*Task*
Create app/main.py with a FastAPI app and one route like /health, then run it locally with fastapi dev so you can confirm the Python side is alive before adding containers. FastAPI’s official first-steps flow is exactly: create the app instance, add a path operation, and run it locally; their docs also recommend splitting bigger apps into multiple files as the project grows, so it is worth creating app/routers/ now even if it is almost empty.

Yes. Do this now as a **small, clean checkpoint**.

I’ll assume you are on **Windows** and the repo root is already created. I’ll use **CMD** commands. Where editing is easier in VS Code, I’ll say “open the file and paste this”.

FastAPI’s current docs recommend installing `fastapi[standard]`, using `fastapi dev` for local development, and—when your app lives in a package like `app/main.py`—setting the app entrypoint in `pyproject.toml` so the CLI can find it reliably. FastAPI also creates interactive docs at `/docs` and alternative docs at `/redoc`. Poetry’s docs confirm `poetry add` installs dependencies and `virtualenvs.in-project = true` puts the venv in `.venv`. ([FastAPI][1])

## 1) Make sure you are in the repo root

In CMD:

```bat
cd C:\path\to\flowledger
dir
```

You should already see at least:

```text
pyproject.toml
```

If you configured Poetry to use an in-project virtualenv, you can confirm where the current env lives with:

```bat
poetry env info --path
```

Poetry documents that command, and also notes that `virtualenvs.in-project = true` uses `.venv` inside the project root. ([python-poetry.org][2])

## 2) Add FastAPI

Install the minimal local dependency for this step:

```bat
poetry add "fastapi[standard]"
```

Why this exact package:

* FastAPI’s docs install `fastapi[standard]`
* that includes the `fastapi` CLI command and Uvicorn for serving locally
* `poetry add` writes the dependency into `pyproject.toml` and installs it. ([FastAPI][1])

After it finishes, glance at:

* `pyproject.toml`
* `poetry.lock`

You should now see FastAPI added as a dependency. Poetry’s lock file pins exact versions for reproducible installs. ([python-poetry.org][3])

## 3) Create the initial folders

Run:

```bat
mkdir app
mkdir app\core
mkdir app\routers
mkdir tests
mkdir mcp
```

Now create the Python package marker files:

```bat
type nul > app\__init__.py
type nul > app\core\__init__.py
type nul > app\routers\__init__.py
```

Why these matter:

* FastAPI’s “bigger applications” docs use `app/main.py` inside an `app` package
* `__init__.py` makes those directories Python packages, so `app.main` is importable. ([FastAPI][4])

## 4) Create `app/main.py`

Create the file:

```bat
type nul > app\main.py
```

Open `app\main.py` in VS Code and paste this:

```python
from fastapi import FastAPI

app = FastAPI(
    title="FlowLedger API",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

This is your smallest useful app:

* one FastAPI application object
* one route
* one JSON response

It follows the same pattern as FastAPI’s first-steps example: create `app = FastAPI()` and add a path operation. ([FastAPI][1])

## 5) Tell FastAPI CLI where your app lives

Because your app is in `app/main.py`, add this block to `pyproject.toml`:

```toml
[tool.fastapi]
entrypoint = "app.main:app"
```

Where to put it:

* at the bottom of `pyproject.toml` is fine

Why this is worth doing now:

* FastAPI CLI docs recommend defining the entrypoint in `pyproject.toml`
* that avoids having to pass the file path every time
* it also helps tools find the app cleanly. ([FastAPI][5])

Your `pyproject.toml` will end up looking roughly like this shape:

```toml
[project]
name = "flowledger"
version = "0.1.0"
description = ""
authors = [
    {name = "Your Name", email = "you@example.com"}
]
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard] (>=...)", 
]

[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.fastapi]
entrypoint = "app.main:app"
```

Do not worry if your exact Poetry-generated format differs slightly. The important addition is:

```toml
[tool.fastapi]
entrypoint = "app.main:app"
```

That exact style is what FastAPI documents for packaged apps. ([FastAPI][5])

## 6) Run the API locally

Now start the dev server:

```bat
poetry run fastapi dev
```

Because you added the entrypoint, FastAPI CLI should find `app.main:app` automatically. FastAPI documents that `fastapi dev` runs the app in development mode with auto-reload and uses Uvicorn underneath. ([FastAPI][5])

If you did **not** add the `[tool.fastapi]` block yet, use this instead:

```bat
poetry run fastapi dev app\main.py
```

FastAPI CLI supports passing the file path directly, but recommends the `pyproject.toml` entrypoint for repeatability. ([FastAPI][5])

## 7) Test it in the browser

Open these URLs:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```

What you should see:

* `/health` returns JSON like `{"status":"ok"}`
* `/docs` shows Swagger UI
* `/redoc` shows ReDoc

FastAPI documents `/docs` and `/redoc` as the automatic documentation endpoints, and `fastapi dev` listens on `127.0.0.1:8000` by default in development mode. ([FastAPI][1])

## 8) Add the next placeholder files now

These are not used yet, but create the structure so the repo starts clean:

```bat
type nul > app\db.py
type nul > app\core\config.py
type nul > README.md
type nul > .gitignore
```

Also make a first router file:

```bat
type nul > app\routers\health.py
```

You do **not** need to wire it in yet. For this checkpoint, keeping the route directly in `app/main.py` is fine.

## 9) Put something useful in `.gitignore`

Open `.gitignore` and add:

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.idea/
.vscode/
.env
```

You may choose to keep `.vscode/` tracked later, but for now ignoring it is simpler.

## 10) Commit this checkpoint

```bat
git add .
git commit -m "Create minimal FastAPI app skeleton"
```

## What you should understand after doing this

You want to understand the plumbing, so focus on these specific observations:

**Poetry side**

* `pyproject.toml` is the project manifest
* `poetry add` changed both `pyproject.toml` and `poetry.lock`
* the interpreter should come from `.venv` if you configured in-project envs. ([python-poetry.org][6])

**FastAPI side**

* `app/main.py` exposes a Python object named `app`
* `fastapi dev` imports that object and starts Uvicorn
* the route decorator `@app.get("/health")` registers an HTTP GET endpoint. ([FastAPI][5])

**Project structure side**

* `app/` is a Python package
* `app.main` is the module import path
* `entrypoint = "app.main:app"` means “import `app` from module `app.main`”. ([FastAPI][4])

## What to read or watch while doing this

Read these two first, while the code is fresh:

* FastAPI First Steps
* FastAPI CLI

Then skim:

* Bigger Applications / Multiple Files
* Poetry Basic Usage

Those docs match exactly what you’re doing here: first app, CLI run, packaged app layout, and dependency management. ([FastAPI][1])

## Done criteria for this checkpoint

You are done when all of these are true:

* `poetry run fastapi dev` starts without errors
* `http://127.0.0.1:8000/health` returns JSON
* `http://127.0.0.1:8000/docs` opens
* `app/main.py` is running through the Poetry environment
* the repo now has `app/`, `app/core/`, `app/routers/`, `tests/`, and `mcp/`

After that, the next step is to create **`compose.yaml` + Postgres service** and keep this same app running inside Docker.

[1]: https://fastapi.tiangolo.com/ "FastAPI"
[2]: https://python-poetry.org/docs/configuration/ "
Configuration | Documentation | Poetry - Python dependency management and packaging made easy
"
[3]: https://python-poetry.org/docs/cli/ "
Commands | Documentation | Poetry - Python dependency management and packaging made easy
"
[4]: https://fastapi.tiangolo.com/tutorial/bigger-applications/?utm_source=chatgpt.com "Bigger Applications - Multiple Files"
[5]: https://fastapi.tiangolo.com/fastapi-cli/ "FastAPI CLI - FastAPI"
[6]: https://python-poetry.org/docs/basic-usage/ "
Basic usage | Documentation | Poetry - Python dependency management and packaging made easy
"
