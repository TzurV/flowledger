# Step 6 — Assistant-Specific Configuration (Detailed Instructions)

This step wires the `mcp_server` from Step 5 into the **two AI assistants you use inside VS Code**:

- **Claude** — the Claude Code VS Code extension
- **ChatGPT Codex** — the Codex VS Code extension

When you finish, both assistants can read and update FlowLedger while you code.

## What you will learn in this step
- How a VS Code AI extension discovers and launches an MCP server
- The difference between project-scoped config and global config
- How to register `mcp_server` with the Claude Code extension
- How to register it with the Codex extension
- Why the VS Code workspace folder matters for the launch
- How to verify each connection and use the tools

This step writes almost no Python — it is configuration and verification. It is the payoff step: FlowLedger becomes usable from inside your editor.

---

## Background: how a VS Code assistant uses an MCP server

Neither extension "connects to a running server." Each one **launches the server itself** as a subprocess and talks to it over stdio. So all you give the assistant is:

1. A **command** to run (and its arguments)
2. The **working directory** it runs in (handled by VS Code — see below)

For FlowLedger the command points **directly at the project's virtual-environment Python interpreter**:

```
c:\work\Github\flowledger\.venv\Scripts\python.exe -m mcp_server.server
```

**Why not `poetry run python ...`?** It's tempting, since that's how you ran the server in Step 5. But `poetry run` resolves *which* virtual environment to use at launch time, and that resolution is fragile: Poetry honors a `VIRTUAL_ENV` environment variable if one is set. VS Code's Python extension often sets `VIRTUAL_ENV` — and if it points at a different project's venv, `poetry run` launches your server in the wrong environment and it fails with `ModuleNotFoundError`.

Pointing straight at `.venv\Scripts\python.exe` removes three failure modes at once: `VIRTUAL_ENV` interference, `poetry` not being on `PATH`, and Poetry's project-directory resolution. An MCP server only needs the **right Python interpreter** — it does not need Poetry. (Adjust the path if your repo lives elsewhere.)

### Where each assistant stores its config

| Assistant | Config file | Scope | Committed to git? |
|-----------|-------------|-------|-------------------|
| Claude (Claude Code extension) | `.mcp.json` in the repo root | Project — travels with the repo | **Yes** (no secrets in it) |
| ChatGPT Codex (Codex extension) | `~/.codex/config.toml` in your home folder | Global — all your projects | No (lives outside the repo) |

### The working-directory rule

The interpreter path takes care of *which Python* runs. One thing still depends on the working directory:

- **The server must find `.env`** — `pydantic-settings` reads `.env` relative to the current working directory; that's where `DATABASE_URL` and `MCP_DATABASE_URL` live. So the server must launch with **the repo root as the working directory**.

Good news: a VS Code extension launches its MCP server subprocesses from the **open workspace folder**. So as long as you open `c:\work\Github\flowledger` as your VS Code workspace (not a parent folder, not a multi-root workspace), the working directory is correct automatically — for both extensions.

This is also why the config files carry **no credentials** — the server reads them from `.env` (which stays gitignored).

---

## Sub-step 6.1 — Pre-flight check

### Goal
Confirm the moving parts work before wiring anything to the assistants.

### What to do

**(a)** Open the FlowLedger folder as your VS Code workspace:
`File → Open Folder… → c:\work\Github\flowledger`

**(b)** Start Postgres — the MCP server needs it for every tool call:

```bat
docker compose up -d
docker compose ps
```

You want `flowledger-db-1` showing `running (healthy)`.

**(c)** Confirm the server still launches, from the VS Code integrated terminal:

```bat
.venv\Scripts\python.exe -m mcp_server.server
```

Silence = good (the server is waiting for an MCP client). Press `Ctrl+C` to stop it.

### What to understand
**Operational habit:** the MCP server connects to Postgres on `localhost:5432`. Whenever you want the FlowLedger tools to work in an assistant, Postgres must be up (`docker compose up -d`). If it's down, the server still starts but every tool call fails with a connection error.

### Checkpoint
FlowLedger open as the workspace; Postgres healthy; server launches without error.

---

## Sub-step 6.2 — Configure Claude (Claude Code extension)

### Goal
Create a project-scoped `.mcp.json` so the Claude Code extension launches the FlowLedger server.

### What to do

Create a file named `.mcp.json` in the **repo root** (same folder as `pyproject.toml`):

```json
{
  "mcpServers": {
    "flowledger": {
      "command": "c:\\work\\Github\\flowledger\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"]
    }
  }
}
```

### What to understand

- **`mcpServers`** — a map of server name → launch config. You can register many; here there's one.
- **`flowledger`** — the name the extension shows for this server; it also prefixes the tool names.
- **`command`** — the absolute path to your FlowLedger venv's Python interpreter. The double backslashes are JSON string escaping for Windows paths. (See "Why not `poetry run`?" in the Background section.)
- **`args`** — `["-m", "mcp_server.server"]` tells that interpreter to run your server module.
- **No `env` block** — the server reads `DATABASE_URL` / `MCP_DATABASE_URL` from `.env`. Because `.mcp.json` holds no credentials, it is safe to commit. `.env` stays gitignored.
- **Project scope** — `.mcp.json` in the repo root is the project-scoped config; it travels with the repo. Caveat: the absolute interpreter path above is specific to *this* machine and location — on a different machine you would update it. That's an acceptable wart for a personal single-machine project; just be aware of it.

### Checkpoint
`.mcp.json` exists in the repo root with the structure above.

---

## Sub-step 6.3 — Verify and use it in Claude

### Goal
Confirm the Claude Code extension launches the server and can call the tools.

### What to do

**(a) Reload the VS Code window** so the extension picks up the new `.mcp.json`:
Command Palette (`Ctrl+Shift+P`) → **Developer: Reload Window**.

**(b) Approve the server.** Because `.mcp.json` is project-scoped, Claude Code treats it as untrusted until you approve it — you'll be prompted whether to enable the `flowledger` MCP server. Approve it. (This is a deliberate safety gate: project files can come from anywhere, so the extension won't auto-run them.)

**(c) Check it's connected.** In the Claude Code chat panel, run the slash command:

```
/mcp
```

You should see `flowledger` listed as **connected**, with its six tools: `get_projects`, `get_project_context`, `get_open_tasks`, `create_task`, `update_task_status`, `append_note`.

**(d) Functional test — reads.** Ask Claude, in plain language:

> List the FlowLedger projects.

It should call `get_projects` and return your projects. Then:

> What open tasks are there in project 1?

That should trigger `get_open_tasks`.

**(e) Functional test — writes.** Ask:

> Add a note to FlowLedger project 1 saying "configured MCP in Claude".

That triggers `append_note`. Confirm in DBeaver: a new `notes` row **and** a new `activity_log` row appear — the Step 4 service layer logging the write.

### What to understand
When you ask a plain-language question, the assistant sees the tool names and descriptions (your docstrings from Step 5), picks the tool that fits, calls it, and uses the result. The quality of those docstrings directly affects how well the assistant chooses — which is why Step 5 stressed writing them well.

### Checkpoint
`/mcp` shows `flowledger` connected; Claude can read and write FlowLedger data through the tools.

---

## Sub-step 6.4 — Configure ChatGPT Codex (Codex extension)

### Goal
Make the same server available to the Codex VS Code extension — your second assistant — proving FlowLedger is genuinely assistant-agnostic.

### What to do

The Codex extension shares its configuration with Codex CLI: a global config file at `~/.codex/config.toml` (on Windows, `C:\Users\<you>\.codex\config.toml`).

Create that file if it doesn't exist, and add:

```toml
[mcp_servers.flowledger]
command = "c:/work/Github/flowledger/.venv/Scripts/python.exe"
args = ["-m", "mcp_server.server"]
```

### What to understand

- `[mcp_servers.flowledger]` is TOML table syntax — the equivalent of the `"flowledger": { ... }` entry in Claude's JSON.
- This config is **global to Codex**, not part of the repo, so it is **not committed**. Each machine where you use Codex sets it up once.
- Same as for Claude: `command` points **directly at the FlowLedger venv's Python interpreter**, not at `poetry` — to avoid `VIRTUAL_ENV` interference. In TOML basic strings, forward slashes for Windows paths avoid escaping.
- The working directory: the Codex extension launches MCP servers from the open VS Code workspace folder, so with the FlowLedger folder open as your workspace (Sub-step 6.1a), the server finds `.env` correctly.

### A note on accuracy
Tool-using assistants and their config formats change quickly. Confirm the exact key names (`command`, `args`, and whether a working-directory key exists) against the current Codex documentation when you set this up.

### Checkpoint
`~/.codex/config.toml` has the `flowledger` MCP server entry.

---

## Sub-step 6.5 — Verify and use it in Codex

### Goal
Confirm the Codex extension launches the server and can call the tools.

### What to do

**(a) Reload the VS Code window** so the Codex extension re-reads `~/.codex/config.toml`:
Command Palette → **Developer: Reload Window**.

**(b) Check Codex sees the server.** In the Codex panel, look for an MCP / tools indicator showing the `flowledger` tools. If you're unsure where it appears, check the Codex extension's documentation for how it surfaces MCP servers — this UI varies across versions.

**(c) Functional test.** Ask Codex, in plain language:

> List the FlowLedger projects.

It should call `get_projects` and return your data. Then try a write:

> Add a note to FlowLedger project 1 saying "configured MCP in Codex".

Confirm the new `notes` row and `activity_log` row in DBeaver — exactly as you did for Claude.

### What to understand
This is the moment FlowLedger meets a **success criterion from the master plan**: "at least two different AI coding assistants can use it in practice." Claude and Codex both calling the same MCP server — backed by the same service layer and the same database — is that criterion satisfied.

### Checkpoint
The Codex extension lists the `flowledger` tools and can read/write FlowLedger data.

---

## Sub-step 6.6 — Commit

```bat
git add .mcp.json
git status
git commit -m "Add Claude Code MCP configuration for the FlowLedger server"
```

Note:
- `.mcp.json` **is** committed — it's project-scoped shared config and contains no secrets.
- `~/.codex/config.toml` is **not** committed — it lives in your home folder, outside the repo.
- `.env` remains gitignored.

---

## Troubleshooting (Windows / VS Code)

| Symptom | Likely cause / fix |
|---------|-------------------|
| `/mcp` shows `flowledger` as **failed** in Claude | Server can't start. Run `.venv\Scripts\python.exe -m mcp_server.server` in the VS Code terminal to see the real error. |
| Manual run gives `ModuleNotFoundError: No module named 'mcp'` (or `fastapi`, etc.) | The server launched in the **wrong Python environment**. Make sure `command` is the absolute path to the FlowLedger `.venv` Python (`...\.venv\Scripts\python.exe`) — not `poetry`. This usually happens because a stray `VIRTUAL_ENV` variable points Poetry at another project's venv. Confirm the correct path with `poetry env info --path` in a clean terminal at the repo root. |
| Tools listed but every call errors with a DB connection failure | Postgres isn't running. `docker compose up -d`. |
| Server errors about a missing `DATABASE_URL` / `MCP_DATABASE_URL` | It launched with the wrong working directory, so `.env` wasn't found. Make sure the FlowLedger folder itself is the open VS Code workspace. |
| Claude never prompts to enable the server | `.mcp.json` may be malformed JSON or not in the repo root. Validate the JSON and the file location, then reload the window. |
| Config change not taking effect | Reload the VS Code window after editing `.mcp.json` or `config.toml`. |

---

## Done criteria for Step 6

You are done when:
- `.mcp.json` exists in the repo root and is committed
- Claude's `/mcp` shows `flowledger` connected with all six tools
- Claude can list projects and create a note through the tools
- Codex is configured in `~/.codex/config.toml` and can call the same tools
- A write performed through either assistant produces an `activity_log` row
- You understand: how a VS Code assistant launches an MCP server, why you point at the venv interpreter directly instead of `poetry`, why the workspace folder matters, the difference between project and global config scope, and why `.mcp.json` carries no secrets

---

## What to watch/read while doing this
- **Claude Code MCP documentation** — the official guide to `.mcp.json`, scopes, and the `/mcp` command.
- **Codex documentation** — the current `config.toml` reference for MCP servers.
- Short videos on "adding an MCP server to Claude Code" — plenty exist; the flow matches yours.

---

## What comes after Step 6

**Step 7 — Decide on a UI.** With the API and MCP workflows genuinely useful, you can finally weigh a lightweight human-facing UI (NiceGUI, Streamlit, or another option). The master plan's decision rule applies: only choose a UI after the API and MCP workflows are real — which, after Step 6, they are. Step 7 is a decision step first, an implementation step second.
