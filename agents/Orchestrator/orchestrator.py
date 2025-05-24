import os
import asyncio
from dotenv import load_dotenv

from trento_agent_sdk.agent.agent import Agent
from trento_agent_sdk.a2a.models.AgentCard import AgentCard, AgentSkill
from trento_agent_sdk.a2a.TaskManager import TaskManager
from trento_agent_sdk.a2a_server import A2AServer
from trento_agent_sdk.tool.tool_manager import ToolManager
from trento_agent_sdk.agent.agent_manager import (
    AgentManager,
)  # <- make sure this path matches your package
from trento_agent_sdk.memory.memory import LongMemory

# from ..services.RAG.rag import RAG

# 1) Load env (if you need any keys for your LLM)
load_dotenv()

# 2) Build a ToolManager and AgentManager for the orchestrator
tool_manager = ToolManager()
agent_manager = AgentManager(os.getenv("AGENT_REGISTRY_URL", "http://localhost:8000"))


# Long memory

memory_prompt = (
    "You are the LongMemory of an orchestator agent that have the role of choosing the right agent or tool to fulfill the user request.\n"
    "You will receive two inputs:\n"
    "1) existing_memories: a JSON array of {id, topic, description}\n"
    "2) chat_history: a string of the latest conversation.\n\n"
    "First you should extract which external agent or tool the orchestator choose to fulfill the user request and store the it to help the orchestator in future choises\n"
    "If you found usefull information in the chast_history, add them to the list. "
    "If this new information replace some of the existing memories, replace them. "
    'Analyze the chat and return a JSON object with exactly one field: "memories_to_add". '
    "The value must be either:\n"
    "  • A list of objects, each with exactly these fields:\n"
    '      – "id": the existing memory id to update, OR null if new\n'
    '      – "topic": a label for the general area of memory (e.g. "agent_to_choose", "cuisine").\n'
    '      – "description": a comprenshicve description about the usefull information to remember.\n'
    '  • The string "NO_MEMORIES_TO_ADD" if nothing has changed.\n'
    "Do NOT include any other fields or commentary."
)

memory = LongMemory(user_id="orchestrator", memory_prompt=memory_prompt)


# 4) Define the orchestrator Agent itself
orchestrator_agent = Agent(
    name="Orchestrator Agent",
    system_prompt=(
        "You are a highly capable orchestrator assistant. Your primary role is to understand user requests "
        "and decide the best course of action. This might involve using your own tools or delegating tasks "
        "to specialized remote agents if the request falls outside your direct capabilities or if a remote agent "
        "is better suited for the task.\n\n"
        "ALWAYS consider the following workflow:\n"
        "1. Understand the user's request.\n"
        "2. Check if any of your locally available tools can directly address the request. If yes, use them.\n"
        "3. If local tools are insufficient or if the task seems highly specialized, consider delegating. "
        "   Use the 'list_delegatable_agents' tool to see available agents and their capabilities. Do not ask the user, just  check available agents\n"
        "4. If you find a suitable agent, use the 'delegate_task_to_agent' tool to assign them the task (without asking the user, just assign the task). "
        "   Clearly formulate the sub-task for the remote agent.\n"
        "5. If no local tool or remote agent seems appropriate, or if you need to synthesize information, "
        "   respond to the user directly.\n"
        "You can have multi-turn conversations involving multiple tool uses and agent delegations to achieve complex goals.\n"
        "Be precise in your tool and agent selection. When delegating, provide all necessary context to the remote agent."
    ),
    tool_manager=tool_manager,
    agent_manager=agent_manager,
    model="gemini-2.0-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    tool_required="auto",
    long_memory=memory,
    # final_tool="delegate_task_to_agent",
)

# 5) Define the Orchestrator’s own AgentCard
orchestrator_card = AgentCard(
    name="Orchestrator Agent",
    description="Orchestrate all the agent in the ecosystem",
    url="http://localhost:8000",
    version="1.0.0",
    skills=[
        AgentSkill(
            id="Orchestrator",
            name="Orchestrator Agent",
            description="Delegates requests to the correct agent or tool",
            examples=[
                "Summarize this PDF for me. It sends the request to the correct agent or tool",
            ],
        )
    ],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    provider="Your Org",
    documentation_url=None,
)

# 6) Build the TaskManager and A2AServer
task_manager = TaskManager()
a2a_server = A2AServer(
    agent=orchestrator_agent,
    agent_card=orchestrator_card,
    task_manager=task_manager,
    host="0.0.0.0",
    port=8000,
)

# 7) Register and run
if __name__ == "__main__":
    # we need to register the remote summarizer before starting
    print("Starting Orchestrator on http://localhost:8000")
    a2a_server.run()
