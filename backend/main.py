"""
main.py — Agent World Lite

Business diagnosis and growth OS — the product, minus the platform.

Flow: intake → rule-based diagnosis → strategy → approval,
with an append-only JSONL audit trail.

The 8-agent swarm, 7-provider LLM router, ChromaDB, Redis, learning loops,
and the rest of the enterprise stack are intentionally absent — they were
infrastructure in search of a user. This is ~100 lines of glue around
3,200 lines of domain logic (business_models/).
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from diagnostic_routes import router as diagnostic_router, set_governance_system
from governance_lite import JSONLEventStream, LiteGovernance

APP_NAME = "Agent World Lite"
VERSION = "0.1.0"

app = FastAPI(
    title=APP_NAME,
    version=VERSION,
    description="Diagnosis-first business growth OS — lite build",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Audit trail ──────────────────────────────────────────────
os.makedirs("data", exist_ok=True)
event_stream = JSONLEventStream(os.getenv("AUDIT_LOG", "data/audit.jsonl"))
set_governance_system(LiteGovernance(event_stream=event_stream))


# ── Routes ───────────────────────────────────────────────────
@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": APP_NAME, "version": VERSION}


app.include_router(diagnostic_router, prefix="/api/v1")


# ── Optional: serve built frontend ───────────────────────────
frontend_dist = os.path.join(
    os.path.dirname(__file__), "..", "frontend-react", "dist"
)
if os.path.isdir(frontend_dist):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
    )
