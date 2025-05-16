import asyncio
from trento_agent_sdk.a2a_client import A2AClient

'''
async def main():
    # Create an A2A client
    async with A2AClient(
        "https://ai-design-855231674152.europe-west8.run.app"
    ) as client:
        # Get the agent card to see what the agent can do
        agent_card = await client.get_agent_card()
        print(f"Connected to agent: {agent_card.name}")
        print(f"Description: {agent_card.description}")

        # Send a summarization task to the agent
        print("\nSending summarization task to the agent...")

        # Example Google Drive ID to summarize
        # Replace this with an actual Google Drive ID from your MongoDB collection
        google_drive_id = "YOUR_GOOGLE_DRIVE_ID_HERE"

        text_to_summarize = f"""
        Please summarize the document with Google Drive ID: {google_drive_id}
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
                        print(f"\nSummarization result: {part.text}")
'''

async def main():
    # 8000 → no orchestrator, 8000 → with orchestrator
    async with A2AClient("http://localhost:8000") as client:
        agent_card = await client.get_agent_card()
        print(f"Connected to orchestrator: {agent_card.name}")
        print(f"Description: {agent_card.description}")
        
        # Send a summarization task to the agent
        print("\nSending orchestrator task to the agent...")

        # Example text to summarize
        text_to_summarize = """
        What Studies using Large Eddy Simulations proved?
        """
        #text_to_summarize = """
        #summarize the content of the following video: /Users/marcomorandin/Desktop/AI-Design/AI-design/SummarizationAgent/intervista.mov
        #"""
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
                        print(f"\n{part.text}")

if __name__ == "__main__":
    asyncio.run(main())
