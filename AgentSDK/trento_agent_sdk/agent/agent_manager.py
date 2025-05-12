import logging
from typing import Dict, Any, List, Optional

from ..a2a_client import A2AClient
from ..a2a.models.AgentCard import AgentCard
from ..a2a.models.Types import SendTaskResponse, GetTaskResponse

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Keeps track of remote A2A agents and offers convenience wrappers that the
    Agent‑side tools (`list_delegatable_agents_tool`, `delegate_task_to_agent_tool`)
    can call just like normal Python functions.
    """

    def __init__(self) -> None:
        # alias  →  {"server_url": str, "card": AgentCard}
        self._registry: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------ #
    # Discovery / registry
    # ------------------------------------------------------------------ #
    async def add_agent(self, alias: str, server_url: str) -> AgentCard:
        """
        Discover a remote agent (via its /.well‑known/agent.json) and cache
        the result under *alias*.

        Returns the fetched `AgentCard`.  If the alias already exists the
        cached card is returned and no network request is made.
        """
        if alias in self._registry:
            logger.info("Agent ‘%s’ already registered – using cached card", alias)
            return self._registry[alias]["card"]

        server_url = server_url.rstrip("/")
        async with A2AClient(server_url) as client:
            card = await client.get_agent_card()

        self._registry[alias] = {"server_url": server_url, "card": card}
        logger.info("Registered remote agent ‘%s’ (%s)", alias, card.name)
        return card

    def list_delegatable_agents(self) -> List[Dict[str, Any]]:
        """
        Return a JSON‑serialisable list describing every registered agent.
        Suitable for feeding straight into an LLM function call response.
        """
        result: List[Dict[str, Any]] = []
        for alias, data in self._registry.items():
            card: AgentCard = data["card"]
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
                    "url": data["server_url"],
                }
            )
        return result

    def get_agent_card(self, alias: str) -> AgentCard:
        """Convenience getter – raises if *alias* is unknown."""
        try:
            return self._registry[alias]["card"]
        except KeyError:
            raise ValueError(f"Unknown agent alias '{alias}'.") from None

    # ------------------------------------------------------------------ #
    # Delegation
    # ------------------------------------------------------------------ #
    async def delegate_task_to_agent(
        self,
        alias: str,
        message: str,
        *,
        polling_interval: float = 1.0,
        timeout: Optional[float] = None,
    ) -> GetTaskResponse:
        """
        Forward *message* to the chosen agent, wait for completion, and return
        the full `GetTaskResponse`.

        The caller can post‑process or just feed the object back into the chat
        history.  To extract plain text use `AgentManager.extract_text(...)`.
        """
        if alias not in self._registry:
            raise ValueError(
                f"Agent alias '{alias}' not found – call add_agent() first."
            )

        server_url = self._registry[alias]["server_url"]

        async with A2AClient(server_url) as client:
            # 1. send
            send_resp: SendTaskResponse = await client.send_task(message)
            task_id = send_resp.result.id
            logger.info("Sent task %s to agent ‘%s’", task_id, alias)

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

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def extract_text(response: GetTaskResponse) -> str:
        """
        Pull the plain‑text payload out of a `GetTaskResponse`.
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

