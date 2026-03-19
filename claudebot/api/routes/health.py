# .claudebot/api/routes/health.py
"""Health check endpoints"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List

router = APIRouter()

AGENT_META = {
    "spec":   {"description": "Generate specification documents"},
    "code":   {"description": "Generate code from descriptions"},
    "test":   {"description": "Generate tests"},
    "deploy": {"description": "Handle deployment workflows"},
    "debug":  {"description": "Analyze and suggest fixes for errors"},
}


class HealthResponse(BaseModel):
    status: str
    version: str


class AgentInfo(BaseModel):
    name: str
    description: str
    enabled: bool


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", version="0.1.0")


@router.get("/agents", response_model=List[AgentInfo])
async def list_agents(request: Request):
    """List available agents with dynamic enabled state from config."""
    config = getattr(request.app.state, "config", None)
    enabled = []
    if config and hasattr(config, "agents") and config.agents:
        enabled = config.agents.enabled or []
    else:
        enabled = ["spec", "code", "test", "deploy", "debug"]

    return [
        AgentInfo(
            name=name,
            description=meta["description"],
            enabled=name in enabled,
        )
        for name, meta in AGENT_META.items()
    ]
