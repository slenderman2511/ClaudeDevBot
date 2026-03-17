# .claudebot/api/server.py
"""FastAPI server for ClaudeDevBot Plugin"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import tasks, health

app = FastAPI(
    title="ClaudeDevBot Plugin API",
    description="REST API for AI-driven development workflows",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
