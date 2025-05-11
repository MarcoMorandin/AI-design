import asyncio
import logging
from typing import Dict, List, Optional, Union

from ..a2a.models.AgentCard import AgentCard
from ..a2a.models.Types import Message, SendTaskResponse, GetTaskResponse
from ..a2a_client import A2AClient

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Manages a collection of remote A2A agents.
    """

    def __init__(self, warn_on_duplicate: bool = True):
        # mapping from your chosen alias → agent base-URL
        self._agents: Dict[str, str] = {}
        # cache of last-fetched AgentCard for each alias
        self._cards: Dict[str, AgentCard] = {}
        self.warn_on_duplicate = warn_on_duplicate

    async def add_agent(self, alias: str, server_url: str) -> AgentCard:
        """
        Register a new agent under `alias`, fetching its card immediately.
        If `alias` already exists you’ll get back the old card (and a warning).
        """
        if alias in self._agents:
            if self.warn_on_duplicate:
                logger.warning(f"Agent alias already registered: {alias}")
            return self._cards[alias]

        # normalize URL
        server_url = server_url.rstrip("/")
        # probe its .well-known/agent.json
        async with A2AClient(server_url) as client:
            card = await client.get_agent_card()

        self._agents[alias] = server_url
        self._cards[alias] = card
        logger.info(f"Registered agent {alias}@{server_url}")
        return card

    def list_agents(self) -> List[str]:
        """Return all registered aliases."""
        return list(self._agents.keys())

    def get_agent_card(self, alias: str) -> AgentCard:
        """Get the last‐known AgentCard for `alias` (error if unknown)."""
        if alias not in self._cards:
            raise KeyError(f"No such agent registered: {alias}")
        return self._cards[alias]

    async def call_agent(
        self,
        alias: str,
        message: Union[str, Message],
        session_id: Optional[str] = None,
        task_id:    Optional[str] = None,
        wait:       bool = True,
        polling_interval: float = 1.0,
        timeout:    Optional[float] = None,
    ) -> Union[SendTaskResponse, GetTaskResponse]:
        """
        Send `message` to the agent `alias`. If `wait` is True, polls
        until the task finishes and returns the final GetTaskResponse;
        otherwise returns the initial SendTaskResponse.
        """
        if alias not in self._agents:
            raise KeyError(f"No such agent registered: {alias}")

        server_url = self._agents[alias]
        async with A2AClient(server_url) as client:
            send_resp = await client.send_task(
                message=message, task_id=task_id, session_id=session_id
            )

            if not wait:
                return send_resp

            # figure out the real task ID
            task_id = send_resp.result.id

            # wait for it to complete
            result = await client.wait_for_task_completion(
                task_id, polling_interval=polling_interval, timeout=timeout
            )

            if result.result and result.result.status and result.result.status.message:
                message = result.result.status.message
                if message.parts:
                    return result

    async def cancel_agent_task(self, alias: str, task_id: str):
        """
        Cancel an in-flight task on `alias`.
        """
        if alias not in self._agents:
            raise KeyError(f"No such agent registered: {alias}")

        server_url = self._agents[alias]
        async with A2AClient(server_url) as client:
            return await client.cancel_task(task_id)
