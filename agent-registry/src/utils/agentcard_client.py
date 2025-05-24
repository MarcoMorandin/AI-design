"""
AgentCard Client

Client for fetching AgentCard data from agent endpoints.
"""

import logging
from typing import Optional
import aiohttp

from ..models import AgentCardModel, AgentSkillModel
from ..config import AGENTCARD_TIMEOUT

logger = logging.getLogger(__name__)


async def fetch_agent_card(url: str) -> Optional[AgentCardModel]:
    """Fetch AgentCard data from an agent's /.well-known/agent.json endpoint."""
    try:
        full_url = f"{url.rstrip('/')}/.well-known/agent.json"
        logger.info(f"Fetching agent card from: {full_url}")

        # Create timeout for aiohttp
        timeout = aiohttp.ClientTimeout(total=AGENTCARD_TIMEOUT)

        try:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(full_url, timeout=timeout) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                logger.debug(f"Agent card data received: {data}")

                                # Validate required fields
                                if not data.get("name"):
                                    logger.warning(
                                        f"Agent card missing required 'name' field: {full_url}"
                                    )
                                    return None

                                if not data.get("description"):
                                    logger.warning(
                                        f"Agent card missing required 'description' field: {full_url}"
                                    )
                                    return None

                                # Convert skills if present
                                skills = None
                                if "skills" in data and data["skills"]:
                                    try:
                                        skills = [
                                            AgentSkillModel(**skill)
                                            for skill in data["skills"]
                                        ]
                                    except Exception as e:
                                        logger.warning(
                                            f"Failed to parse skills data: {e}"
                                        )
                                        # Continue without skills if parsing fails
                                        skills = None

                                # Create AgentCardModel
                                agent_card = AgentCardModel(
                                    name=data.get("name", ""),
                                    description=data.get("description", ""),
                                    url=data.get("url", url),
                                    version=data.get("version", "1.0.0"),
                                    skills=skills,
                                    provider=data.get("provider"),
                                )

                                logger.info(
                                    f"Successfully fetched agent card for: {agent_card.name}"
                                )
                                return agent_card
                            except Exception as e:
                                logger.warning(f"Failed to parse agent card JSON: {e}")
                                return None
                        else:
                            logger.warning(
                                f"Failed to fetch agent card: HTTP {response.status} - {response.reason}"
                            )
                            return None
                except aiohttp.ClientConnectorError as e:
                    logger.warning(f"Connection error to {full_url}: {e}")
                    return None
                except aiohttp.ClientResponseError as e:
                    logger.warning(f"Response error from {full_url}: {e}")
                    return None
                except aiohttp.ClientError as e:
                    logger.warning(f"Client error with {full_url}: {e}")
                    return None
        except aiohttp.ClientError as e:
            logger.warning(f"Failed to create client session: {e}")
            return None
    except Exception as e:
        logger.warning(f"Error fetching agent card from {url}: {str(e)}")
        return None
