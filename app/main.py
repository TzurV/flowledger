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
