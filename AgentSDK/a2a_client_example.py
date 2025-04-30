import asyncio
from trento_agent_sdk.a2a_client import A2AClient
from trento_agent_sdk.a2a.models.Task import TextPart, Message

async def main():
    # Create an A2A client
    async with A2AClient("http://localhost:8000") as client:
        # Get the agent card to see what the agent can do
        agent_card = await client.get_agent_card()
        print(f"Connected to agent: {agent_card.name}")
        print(f"Description: {agent_card.description}")
        
        if agent_card.skills:
            print("\nAgent skills:")
            for skill in agent_card.skills:
                print(f"- {skill.name}: {skill.description}")
                if skill.examples:
                    print("  Examples:")
                    for example in skill.examples:
                        print(f"  - {example}")
        
        # Send a task to the agent
        print("\nSending task to the agent 'What is 5 + 3?'")
        response = await client.send_task("What is 5 + 3?")
        
        # Access the result attribute instead of task
        task_id = response.result.id
        print(f"Task ID: {task_id}")
        
        # Wait for the task to complete
        print("Waiting for task to complete...")
        result = await client.wait_for_task_completion(task_id)
        
        # Print the result - also update to use result instead of task
        if result.result and result.result.status and result.result.status.message:
            message = result.result.status.message
            if message.parts:
                for part in message.parts:
                    if hasattr(part, 'text'):
                        print(f"\nAgent response: {part.text}")
        
        # Try another calculation
        print("\nSending another task...")
        response = await client.send_task("Calculate 10 - 7")
        task_id = response.result.id
        
        # Wait for the task to complete
        result = await client.wait_for_task_completion(task_id)
        
        # Print the result - also update to use result instead of task
        if result.result and result.result.status and result.result.status.message:
            message = result.result.status.message
            if message.parts:
                for part in message.parts:
                    if hasattr(part, 'text'):
                        print(f"\nAgent response: {part.text}")

if __name__ == "__main__":
    asyncio.run(main())