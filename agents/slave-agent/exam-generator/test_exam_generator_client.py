import asyncio
from trento_agent_sdk.a2a_client import A2AClient


async def main():
    # Create an A2A client
    async with A2AClient(
        "http://localhost:8003"  # Update with your deployment URL in production
    ) as client:
        # Get the agent card to see what the agent can do
        agent_card = await client.get_agent_card()
        print(f"Connected to agent: {agent_card.name}")
        print(f"Description: {agent_card.description}")

        # Send an exam generation task to the agent
        print("\nSending exam generation task to the agent...")

        # Example Google Drive ID - replace with an actual ID from your MongoDB collection
        document_id = "1MU5Lg_7H1OtNYm2N9qRH5mIwFqKg-ceN"

        # Task text - modify as needed
        task_text = f"Generate a quiz from document ID {document_id}. Make it moderate difficulty with 10 questions and include answers in markdown format."

        # Debug info
        print(f"Task: {task_text}")

        # Send the task
        response = await client.send_task(task_text)

        # Access the task ID from the result attribute
        task_id = response.result.id
        print(f"Task ID: {task_id}")

        # Wait for the task to complete and get the final result
        while True:
            task_response = await client.get_task(task_id)
            task_status = task_response.result.status.state

            if task_status in ["RUNNING", "QUEUED"]:
                print(f"Task status: {task_status}")
                await asyncio.sleep(2)  # Poll every 2 seconds
            elif task_status == "SUCCEEDED":
                # Display the result message
                print("\nTask Completed Successfully!")
                print("=" * 40)
                print(task_response.result.status.message.parts[0].text)
                break
            else:
                print(f"Task failed with status: {task_status}")
                if hasattr(task_response.result.status, "message"):
                    print(f"Message: {task_response.result.status.message}")
                break


if __name__ == "__main__":
    asyncio.run(main())
