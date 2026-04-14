"""
Agent World — Main Application Entry Point

This is the NEW main app that wires together:
  - Auto-Spawner (natural language → agent team)
  - AgentBrain + Executor (agents that think + act)
  - MCP Tool Layer (web search, HTTP, file ops, memory, room broadcast)
  - WebSocket live dashboard

Run with:
  uvicorn app:app --reload --port 8001

Environment variables (copy .env.example → .env):
  DATABASE_URL  = postgresql://user:pass@localhost/agentworld
  LLM_PROVIDER  = ollama | openai | anthropic
  LLM_MODEL     = llama3.2 | gpt-4o | claude-3-5-sonnet-20241022
  LLM_API_KEY   = your-key (or "ollama" for local)
  LLM_BASE_URL  = http://localhost:11434/v1   (Ollama only)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from spawn_routes import router as spawn_router, on_startup
from models import Base
from sqlalchemy import create_engine
import os

logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# DB Init                                                              #
# ------------------------------------------------------------------ #

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/agentworld")

def _init_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")


# ------------------------------------------------------------------ #
# App                                                                  #
# ------------------------------------------------------------------ #

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    _init_db()
    await on_startup()   # starts executor + broadcast drain
    logger.info("Agent World started ✅")
    yield
    # Shutdown
    from agent_executor import stop_executor
    stop_executor()
    logger.info("Agent World stopped.")


app = FastAPI(
    title       = "Agent World",
    description = "Autonomous multi-agent business engine",
    version     = "3.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(spawn_router)


@app.get("/health")
def health():
    return {"status": "healthy", "version": "3.0.0"}


@app.get("/")
def root():
    return {
        "name":    "Agent World",
        "version": "3.0.0",
        "docs":    "/docs",
        "endpoints": {
            "spawn":      "POST /api/v1/spawn",
            "rooms":      "GET  /api/v1/rooms",
            "room_detail":"GET  /api/v1/rooms/{room_id}",
            "tools":      "GET  /api/v1/tools",
            "websocket":  "WS   /api/v1/ws/spawn/{room_id}",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)
