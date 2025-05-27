from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class AgentSkill(BaseModel):
    id: str
    name: str
    description: str | None = None
    tags: List[str] | None = None
    examples: List[str] | None = None
    inputModes: List[str] | None = None
    outputModes: List[str] | None = None


class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str
    skills: List[AgentSkill] | None = None
    default_input_modes: List[str] | None = None
    default_output_modes: List[str] | None = None
    provider: str | None = None
    documentation_url: str | None = None

    def to_dict(self):
        """Convert the AgentCard to a dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "skills": [skill.dict() for skill in self.skills] if self.skills else None,
            "defaultInputModes": self.default_input_modes,
            "defaultOutputModes": self.default_output_modes,
            "provider": self.provider,
            "documentationUrl": self.documentation_url,
        }

    authentication: Optional[str] = None
    capabilities: Dict[str, Any] = {
        "streaming": False,
        "pushNotifications": False,
        "stateTransitionHistory": False,
    }
    default_input_modes: List[str] = ["text/plain"]
    default_output_modes: List[str] = ["text/plain"]
    skills: List[AgentSkill] = None
    provider: Optional[str] = None
    documentation_url: Optional[str] = None
