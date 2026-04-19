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
