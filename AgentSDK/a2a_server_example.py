from google import genai
import asyncio
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv

from trento_agent_sdk.agent.agent import Agent
from trento_agent_sdk.agent.swarm import Swarm
from trento_agent_sdk.tool.tool_manager import ToolManager
from trento_agent_sdk.a2a.models.AgentCard import AgentCard, AgentSkill
from trento_agent_sdk.a2a.models.Task import TaskState, Message, TextPart, Task, TaskStatus
from trento_agent_sdk.a2a.TaskManager import TaskManager
from trento_agent_sdk.a2a_server import A2AServer

# Load environment variables from .env file
load_dotenv()

# Define some tools for our agent
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

def subtract_numbers(a: int, b: int) -> int:
    """Subtract two numbers together."""
    return a - b

def multiply_numbers(a: int, b: int) -> int:
    """Multiply two numbers together."""
    return a * b

# Initialize the Google Generative AI client
# Get API key from environment variable
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is not set. Please create a .env file with your API key.")

client = genai.Client(api_key=api_key)

# Create a tool manager and register tools
tool_manager = ToolManager()
tool_manager.add_tool(add_numbers, "add_numbers", "Add two numbers together")
tool_manager.add_tool(subtract_numbers, "subtract_numbers", "Subtract second number from first")
tool_manager.add_tool(multiply_numbers, "multiply_numbers", "Multiply two numbers together")

# Create an agent with the tools
calculator_agent = Agent(
    name="Calculator Agent",
    instructions="""You are a helpful calculator agent that can perform basic arithmetic operations.
When asked to perform calculations, ALWAYS use the appropriate tool.
For addition, use add_numbers.
For subtraction, use subtract_numbers.
For multiplication, use multiply_numbers.
Always respond with the calculation result in a clear format like: 'The result is: {result}'.""",
    tool_manager=tool_manager,
    model="gemini-2.0-flash"  # Specify the model to use
)

# Create a swarm to manage the agent
swarm = Swarm(client)

# Define the agent's capabilities as an AgentCard
agent_card = AgentCard(
    name="Calculator Agent",
    description="A helpful agent that can perform basic arithmetic operations",
    url="http://localhost:8000",
    version="1.0.0",
    skills=[
        AgentSkill(
            id="arithmetic",
            name="Arithmetic Operations",
            description="Can perform addition, subtraction, and multiplication",
            examples=[
                "What is 5 + 3?",
                "Calculate 10 - 7",
                "Multiply 4 and 6"
            ]
        )
    ],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    provider="Trento AI",
    documentation_url="https://example.com/docs"
)

# Create a task manager to handle task lifecycle
task_manager = TaskManager()

# Create the A2A server
a2a_server = A2AServer(
    agent=calculator_agent,
    swarm=swarm,
    agent_card=agent_card,
    task_manager=task_manager,
    host="0.0.0.0",
    port=8000
)

# Run the server
if __name__ == "__main__":
    a2a_server.run()
