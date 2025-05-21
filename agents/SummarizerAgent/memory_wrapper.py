import logging
import json
import asyncio
from typing import Optional, Dict, Any, List
import traceback

logger = logging.getLogger(__name__)


class MemoryWrapper:
    """
    A wrapper for the LongMemory class from the trento_agent_sdk.
    Provides safer access to the memory functionality with robust error handling.
    """

    def __init__(self, memory_instance=None):
        """
        Initialize the memory wrapper with an optional memory instance.

        Args:
            memory_instance: An instance of LongMemory or None
        """
        self.memory = memory_instance
        self.enabled = memory_instance is not None
        logger.info(f"Memory wrapper initialized. Enabled: {self.enabled}")

    def get_memories(
        self, query: str, top_k: int = 5, max_cosine_distance: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Safely get memories from the underlying memory instance, with error handling.

        Args:
            query: The query to search for related memories
            top_k: Maximum number of results to return
            max_cosine_distance: Maximum cosine distance for search

        Returns:
            A list of memory items or an empty list if errors occur
        """
        if not self.enabled:
            logger.info("Memory access attempted but memory is disabled")
            return []

        try:
            results = self.memory.get_memories(query, top_k, max_cosine_distance)
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}")
            logger.debug(traceback.format_exc())
            return []

    async def add_memory(
        self, topic: str, description: str, memory_id: Optional[str] = None
    ) -> bool:
        """
        Safely add a memory, with error handling.

        Args:
            topic: The topic of the memory
            description: The description of the memory
            memory_id: Optional ID to update an existing memory

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.info("Memory add attempted but memory is disabled")
            return False

        try:
            if hasattr(self.memory, "add_memory"):
                # Handle both sync and async implementations
                if asyncio.iscoroutinefunction(self.memory.add_memory):
                    await self.memory.add_memory(topic, description, memory_id)
                else:
                    self.memory.add_memory(topic, description, memory_id)
                return True
            else:
                logger.warning("Memory instance does not have add_memory method")
                return False
        except Exception as e:
            logger.error(f"Error adding memory: {str(e)}")
            logger.debug(traceback.format_exc())
            return False

    def update_memories_from_chat(self, chat_history: str) -> bool:
        """
        Update memories based on chat history, with error handling.

        Args:
            chat_history: The chat history to extract memories from

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.info("Memory update attempted but memory is disabled")
            return False

        try:
            if hasattr(self.memory, "update_memories_from_chat"):
                result = self.memory.update_memories_from_chat(chat_history)
                return bool(result)
            elif hasattr(self.memory, "_extract_memories"):
                # Try to use the internal method if available
                existing_memories = self.get_memories("", top_k=100)
                result = self.memory._extract_memories(chat_history, existing_memories)
                if (
                    result
                    and result != "NO_MEMORIES_TO_ADD"
                    and isinstance(result, list)
                ):
                    for memory in result:
                        memory_id = memory.get("id")
                        topic = memory.get("topic", "unknown")
                        description = memory.get("description", "")
                        if asyncio.get_event_loop().is_running():
                            asyncio.create_task(
                                self.add_memory(topic, description, memory_id)
                            )
                        else:
                            asyncio.run(self.add_memory(topic, description, memory_id))
                return True
            else:
                logger.warning(
                    "Memory instance does not have methods to update from chat"
                )
                return False
        except Exception as e:
            logger.error(f"Error updating memories from chat: {str(e)}")
            logger.debug(traceback.format_exc())
            return False

    async def close(self):
        """
        Safely close any resources used by the memory system.
        """
        if not self.enabled:
            return

        try:
            # Close any client sessions in the memory instance
            if hasattr(self.memory, "embedding_client") and hasattr(
                self.memory.embedding_client, "close"
            ):
                await self.memory.embedding_client.close()

            if hasattr(self.memory, "openai_client") and hasattr(
                self.memory.openai_client, "close"
            ):
                await self.memory.openai_client.close()

            logger.info("Memory resources closed successfully")
        except Exception as e:
            logger.error(f"Error closing memory resources: {str(e)}")
            logger.debug(traceback.format_exc())
