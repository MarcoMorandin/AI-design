"""
AgentCard Client

Client for fetching AgentCard data from agent endpoints using trento-agent-sdk.
"""

import logging
from typing import Optional
from trento_agent_sdk.a2a_client import A2AClient
from trento_agent_sdk.a2a.models.AgentCard import AgentCard

logger = logging.getLogger(__name__)


async def fetch_agent_card(url: str) -> Optional[AgentCard]:
    """Fetch AgentCard data from an agent's /.well-known/agent.json endpoint using A2A client."""
    try:
        logger.info(f"Fetching agent card from: {url}")

        # Use A2AClient from trento-agent-sdk
        async with A2AClient(url) as client:
            agent_card = await client.get_agent_card()

            logger.info(f"Successfully fetched agent card for: {agent_card.name}")
            return agent_card

    except Exception as e:
        logger.warning(f"Error fetching agent card from {url}: {str(e)}")
        return None
