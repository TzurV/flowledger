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

