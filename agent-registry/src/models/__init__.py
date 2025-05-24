"""
Agent Registry Models

Pydantic models for AgentCard integration and API responses.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AgentSkillModel(BaseModel):
    """Agent skill model based on AgentCard spec."""

    id: str
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    examples: Optional[List[str]] = None


class AgentCardModel(BaseModel):
    """Agent card model based on AgentCard spec."""

    name: str
    description: str
    url: str
    version: str
    skills: Optional[List[AgentSkillModel]] = None
    provider: Optional[str] = None


class AgentRegistrationRequest(BaseModel):
    """Simple request model for agent registration - just the URL."""

    url: str = Field(..., description="Base URL where the agent is accessible")
    agent_id: Optional[str] = Field(None, description="Optional custom agent ID")


class AgentInfo(BaseModel):
    """Agent information."""

    agent_id: str
    name: str
    description: str
    url: str
    version: str
    skills: Optional[List[AgentSkillModel]] = None
    provider: Optional[str] = None
    registered_at: datetime
    last_seen: Optional[datetime] = None
    status: str = "active"


class AgentDiscoveryResponse(BaseModel):
    """Response model for agent discovery."""

    agents: List[AgentInfo]
    total_count: int
