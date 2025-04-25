from agent.agent import Agent, Swarm, pretty_print_messages
from tool.tool_manager import ToolManager
import asyncio

def add_numbers(a: int, b: int) -> int:
        #"""Add two numbers together."""
        return a + b

def subtract_numbers(a: int, b: int) -> int:
        #"""Subtract two numbers together."""
        return a - b

manager = ToolManager()
manager.add_tool(add_numbers, "add_numbers", "add two numbers")
manager.add_tool(subtract_numbers, "subtract_numbers", "subtract two numbers")

weather_agent = Agent(
    name="Sum agent",
    instructions="You are an agent that do sums.",
    tool_manager=manager
)

client = Swarm()
print("Starting Single Agent - Weather Agent")
print('Any sums?')

async def main():
    messages = []
    agent = weather_agent

    while True:
        user_input = input("\033[90mUser\033[0m: ")
        messages.append({"role": "user", "content": user_input})

        response = await client.run(agent=agent, messages=messages)
        pretty_print_messages(response.messages)

        messages.extend(response.messages)
        agent = response.agent

if __name__ == "__main__":
    asyncio.run(main())