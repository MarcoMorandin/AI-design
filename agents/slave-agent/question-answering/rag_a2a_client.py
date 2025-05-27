import asyncio
from trento_agent_sdk.a2a_client import A2AClient


async def main():
    # Create an A2A client
    async with A2AClient(
        "https://ai-design-rag-agent-595073969012.europe-west8.run.app",
    ) as client:
        # Get the agent card to see what the agent can do
        agent_card = await client.get_agent_card()
        print(f"Connected to agent: {agent_card.name}")
        print(f"Description: {agent_card.description}")

        # Send a summarization task to the agent
        print("\nSending task to the agent...")

        # Example of question
        text_to_summarize = """
        SigLIP
        """

        response = await client.send_task(text_to_summarize)

        # Access the result attribute
        task_id = response.result.id
        print(f"Task ID: {task_id}")

        # Wait for the task to complete
        print("Waiting for task to complete...")
        result = await client.wait_for_task_completion(task_id)

        # Print the result
        if result.result and result.result.status and result.result.status.message:
            message = result.result.status.message
            if message.parts:
                for part in message.parts:
                    if hasattr(part, "text"):
                        print(f"\nRAG result: {part.text}")


if __name__ == "__main__":
    asyncio.run(main())
