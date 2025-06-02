import asyncio
import json
from trento_agent_sdk.a2a_client import A2AClient


async def main():
    # Create an A2A client
    async with A2AClient(
        "https://drive-organizer-595073969012.europe-west8.run.app"  # Update with your deployment URL in production
        # "http://localhost:8002",  # Use this for local testing
    ) as client:
        # Get the agent card to see what the agent can do
        agent_card = await client.get_agent_card()
        print(f"Connected to agent: {agent_card.name}")
        print(f"Description: {agent_card.description}")

        # Send an organization task to the agent
        print("\nSending folder organization task to the agent...")

        # Example course name and user ID
        course_name = "deep-learning"  # Using course name instead of folder ID
        user_id = "111369155660754322920"

        # Modified task text to use course name
        task_text = f"organize my course '{course_name}'\n\n  If you need this is my user id: {user_id}"

        # Add debug info
        print(f"Task: {task_text}")

        # Set debug mode to true to get detailed task execution
        response = await client.send_task(task_text)

        # Access the result attribute
        task_id = response.result.id
        print(f"Task ID: {task_id}")

        # Wait for the task to complete
        print("Waiting for task to complete...")
        result = await client.wait_for_task_completion(task_id)

        # Print the result and any debug information
        print("\n=== Task Execution Details ===")
        if hasattr(result, "debug_info") and result.debug_info:
            print(f"Debug info: {json.dumps(result.debug_info, indent=2)}")

        if result.result and result.result.status and result.result.status.message:
            message = result.result.status.message
            if message.parts:
                for part in message.parts:
                    if hasattr(part, "text"):
                        print(f"\nOrganization result: {part.text}")

        print("\nTask execution completed.")


if __name__ == "__main__":
    asyncio.run(main())
