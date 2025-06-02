import asyncio
from trento_agent_sdk.a2a_client import A2AClient

async def main():
    async with A2AClient(
        "https://orchestrator-595073969012.europe-west8.run.app",
        # "http://localhost:8080",
    ) as client:
        agent_card = await client.get_agent_card()
        print(f"Connected to orchestrator: {agent_card.name}")
        print(f"Description: {agent_card.description}")

        # Send a summarization task to the agent
        print("\nSending orchestrator task to the agent...")

        # Example text to summarize
        user_question_test = """
        summarize this document: 18-KxLZ42dLf7lMtF0_qWQsvPRc5A6lXC
        """
        response = await client.send_task(user_question_test)

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
                        print(f"\n{part.text}")


if __name__ == "__main__":
    asyncio.run(main())
