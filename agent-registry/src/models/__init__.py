"""
Agent Registry Models

Pydantic models for AgentCard integration and API responses using trento-agent-sdk.
"""

from typing import List
from pydantic import BaseModel, Field

# Import from trento-agent-sdk
from trento_agent_sdk.a2a.models.AgentCard import AgentCard, AgentSkill

# Type aliases for compatibility
AgentCardModel = AgentCard
AgentSkillModel = AgentSkill


class AgentRegistrationRequest(BaseModel):
    """Simple request model for agent registration - just the URL."""

    url: str = Field(..., description="Base URL where the agent is accessible")


class AgentDiscoveryResponse(BaseModel):
    """Response model for agent discovery."""

    agents: List[AgentCard]
    total_count: int
