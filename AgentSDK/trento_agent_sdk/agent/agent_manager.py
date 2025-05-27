import logging
import aiohttp
from typing import Dict, Any, List, Optional
from urllib.parse import quote
from ..a2a_client import A2AClient
from ..a2a.models.AgentCard import AgentCard
from ..a2a.models.Types import SendTaskResponse, GetTaskResponse

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Manages remote A2A agents through an external agent-registry service.
    Offers convenience wrappers that the Agent-side tools
    (list_delegatable_agents_tool, delegate_task_to_agent_tool)
    can call just like normal Python functions.
    """

    def __init__(self, registry_url: str = "http://localhost:8080") -> None:
        """
        Initialize the AgentManager with an external registry service.

        Args:
            registry_url: URL of the agent-registry service (default: http://localhost:8080)
        """
        self.registry_url = registry_url.rstrip("/")


    async def _get_agent_from_registry(self, agent_url: str) -> AgentCard:
        """
        Fetch agent card from the external registry.
        """
        async with aiohttp.ClientSession() as session:
            encoded_url = quote(agent_url, safe="")
            async with session.get(
                f"{self.registry_url}/agents/{encoded_url}"
            ) as response:
                if response.status == 200:
                    card_data = await response.json()
                    return AgentCard(**card_data)
                else:
                    # If not found in registry, try direct connection
                    async with A2AClient(agent_url) as client:
                        return await client.get_agent_card()

    async def list_delegatable_agents(self) -> List[Dict[str, Any]]:
        """
        Return a JSON-serialisable list describing every registered agent.
        Fetches data from the external registry service.
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.registry_url}/agents") as response:
                    if response.status == 200:
                        response_data = await response.json()
                        agents_data = response_data.get("agents", [])
                        result = []

                        for agent_data in agents_data:
                            agent_url = agent_data.get("url")
                            # Use the URL as alias since we no longer maintain local aliases
                            alias = agent_url

                            card = AgentCard(**agent_data)
                            result.append(
                                {
                                    "alias": alias,
                                    "name": card.name,
                                    "description": card.description,
                                    "skills": [
                                        {
                                            "id": s.id,
                                            "name": s.name,
                                            "description": s.description,
                                        }
                                        for s in (card.skills or [])
                                    ],
                                    "url": agent_url,
                                }
                            )
                        return result
                    else:
                        logger.error(
                            f"Failed to fetch agents from registry: {response.status}"
                        )
                        return []

            except Exception as e:
                logger.error(f"Error fetching agents from registry: {e}")
                return []


    async def delegate_task_to_agent(
        self,
        agent_url: str,
        message: str,
        *,
        polling_interval: float = 1.0,
        timeout: Optional[float] = None,
    ) -> GetTaskResponse:
        """
        Forward message to the chosen agent, wait for completion, and return
        the full GetTaskResponse.

        The caller can post-process or just feed the object back into the chat
        history.  To extract plain text use AgentManager.extract_text(...).
        """
        async with A2AClient(agent_url) as client:
            # 1. send
            send_resp: SendTaskResponse = await client.send_task(message)
            task_id = send_resp.result.id
            logger.info("Sent task %s to agent '%s'", task_id, agent_url)

            # 2. wait until COMPLETED / FAILED / CANCELED (or timeout)
            final_resp: GetTaskResponse = await client.wait_for_task_completion(
                task_id, polling_interval=polling_interval, timeout=timeout
            )
            logger.info(
                "Task %s finished with state %s",
                task_id,
                final_resp.result.status.state,
            )
            return final_resp

    @staticmethod
    def extract_text(response: GetTaskResponse) -> str:
        """
        Pull the plain-text payload out of a GetTaskResponse.
        Safe even if the response shape evolves slightly.
        """
        if (
            response.result
            and response.result.status
            and response.result.status.message
            and response.result.status.message.parts
        ):
            texts = [
                part.text
                for part in response.result.status.message.parts
                if getattr(part, "text", None)
            ]
            return "\n".join(texts).strip()
        return ""
