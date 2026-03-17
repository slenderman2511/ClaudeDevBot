# .claudebot/api/routes/health.py
"""Health check endpoints"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()

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
async def list_agents():
    """List available agents"""
    return [
        AgentInfo(name="spec", description="Generate specification documents", enabled=True),
        AgentInfo(name="code", description="Generate code from descriptions", enabled=True),
        AgentInfo(name="test", description="Generate tests", enabled=True),
        AgentInfo(name="deploy", description="Handle deployment workflows", enabled=True),
        AgentInfo(name="debug", description="Analyze and suggest fixes for errors", enabled=True),
    ]
