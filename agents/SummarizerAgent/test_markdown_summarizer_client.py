import json
import asyncio
import os
from dotenv import load_dotenv

from trento_agent_sdk.a2a_client import A2AClient

# Load environment variables
load_dotenv()

# Get API key from environment variable
API_KEY = os.getenv("GEMINI_API_KEY")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8002")


async def test_markdown_summarizer():
    """
    Test the Markdown Summarizer Agent with a document ID.
    """

    # Initialize the A2A client
    client = A2AClient(SERVER_URL)

    # Choose summary style
    style = "technical"  # Can be: technical, bullet-points, standard, concise, detailed
    document_id = "1UBJJQ0V07DA92rtrT1CqI-nBwaVmCEXG"  # Example document ID

    print(f"Testing with document ID: {document_id}")
    print(f"Sending request to {SERVER_URL}...")
    print(f"Requesting a {style} summary...")

    text_content = f"Please retrieve and summarize document with ID '{document_id}' in {style} style"

    # Option 1: Let A2AClient handle the request creation (recommended)
    response = await client.send_task(text_content)

    # Access the result attribute to get the task ID
    task_id = response.result.id
    print(f"Task ID: {task_id}")

    # Wait for the task to complete
    print("Waiting for task to complete...")
    result = await client.wait_for_task_completion(task_id)

    # Print the response
    print("\n----- Summary Result -----\n")

    if result.result and result.result.status and result.result.status.message:
        message = result.result.status.message
        if message.parts:
            for part in message.parts:
                if hasattr(part, "text"):
                    print(part.text)
    else:
        print("No response or empty response received.")


# Run the test
if __name__ == "__main__":

    asyncio.run(test_markdown_summarizer())
