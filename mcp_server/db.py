from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# The MCP server runs on the host (the coding assistant launches it as a
# subprocess), so it reaches Postgres through the published port on localhost,
# NOT through the Docker network name "db".
engine = create_engine(settings.mcp_database_url, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
