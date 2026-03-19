# .claudebot/api/server.py
"""FastAPI server for ClaudeDevBot Plugin"""

import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .routes import tasks, health, telegram, websocket
from .rate_limit import rate_limit_middleware
from ..orchestrator.task_manager import TaskManager
from ..config import load_config


# Global task manager instance
task_manager: TaskManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global task_manager

    # Load config
    config = load_config()

    # Initialize task manager
    task_manager = TaskManager(config.__dict__)
    await task_manager.start()

    # Set task manager in routes
    tasks.set_task_manager(task_manager)

    # Store repo path in app state
    app.state.repo_path = Path(".")
    app.state.config = config

    yield

    # Cleanup on shutdown
    # (add cleanup logic if needed)


app = FastAPI(
    title="ClaudeDevBot Plugin API",
    description="REST API for AI-driven development workflows",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    return await rate_limit_middleware(request, call_next)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(telegram.router, prefix="/api", tags=["telegram"])
app.include_router(websocket.router, tags=["websocket"])
