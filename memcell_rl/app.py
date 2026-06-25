"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from memcell_rl.api.routes_cells import router as cells_router
from memcell_rl.api.routes_decide import router as decide_router
from memcell_rl.api.routes_events import router as events_router
from memcell_rl.api.routes_feedback import router as feedback_router
from memcell_rl.api.routes_rl import router as rl_router
from memcell_rl.db import init_db


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


app = FastAPI(
    title="memcell-rl",
    description="RL-native memory control engine for LLM agents",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


app.include_router(cells_router)
app.include_router(decide_router)
app.include_router(feedback_router)
app.include_router(events_router)
app.include_router(rl_router)
