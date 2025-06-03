import os
from dotenv import load_dotenv

from trento_agent_sdk.agent.agent import Agent
from trento_agent_sdk.a2a.models.AgentCard import AgentCard, AgentSkill
from trento_agent_sdk.a2a.TaskManager import TaskManager
from trento_agent_sdk.a2a_server import A2AServer
from trento_agent_sdk.tool.tool_manager import ToolManager
from trento_agent_sdk.agent.agent_manager import (AgentManager,)
from trento_agent_sdk.memory.memory import LongMemory


# 1) Load env (if you need any keys for your LLM)
load_dotenv()

# 2) Build a ToolManager and AgentManager for the orchestrator
tool_manager = ToolManager()
agent_manager = AgentManager(os.getenv("AGENT_REGISTRY_URL"))


# Long memory
memory_prompt = (
    "You are the LongMemory of an orchestrator agent. Your role is to store general user preferences and context, but NEVER store specific agent routing decisions.\n"
    "You will receive two inputs:\n"
    "1) existing_memories: a JSON array of {id, topic, description}\n"
    "2) chat_history: a string of the latest conversation.\n\n"
    "Extract and store user preferences about formats, styles, or general requirements. DO NOT store which specific agents were chosen - the orchestrator must always use its tools to discover and select agents dynamically.\n"
    "If you found useful information in the chat_history, add them to the list. "
    "If this new information replaces some of the existing memories, replace them. "
    'Analyze the chat and return a JSON object with exactly one field: "memories_to_add". '
    "The value must be either:\n"
    "  • A list of objects, each with exactly these fields:\n"
    '      – "id": the existing memory id to update, OR null if new\n'
    '      – "topic": a label for the general area of memory (e.g. "format_preference", "style_preference", "requirements").\n'
    '      – "description": a comprehensive description about the useful information to remember (NO agent routing decisions).\n'
    '  • The string "NO_MEMORIES_TO_ADD" if nothing has changed.\n'
    "Do NOT include any other fields or commentary."
)

memory = LongMemory(user_id="orchestratore", memory_prompt=memory_prompt)


# 4) Define the orchestrator Agent itself
orchestrator_agent = Agent(
    name="Orchestrator Agent",
    system_prompt="""
        You are a highly capable orchestrator assistant. Your primary role is to precisely understand user requests and autonomously determine the best way to fulfill them. You must NEVER ask the user which agent or tool to use. Instead, ALWAYS delegate tasks directly and efficiently.

Follow this workflow strictly and automatically:

1. **Understand** the user's request clearly.
2. **Evaluate** your locally available tools first. If a local tool perfectly matches the request, use it immediately without hesitation.
3. If local tools are insufficient or the request requires specialized knowledge or skills, **ALWAYS use the `list_delegatable_agents_tool` FIRST** to discover what agents are available. DO NOT rely on memory for agent selection - always check what agents are currently available.
4. **Automatically delegate** the task to an appropriate agent using the `delegate_task_to_agent_tool`. Select the agent based on the current list from step 3, not from memory. Clearly and comprehensively formulate the sub-task, providing all relevant context the agent might require.
5. If neither local tools nor remote agents can fulfill the request adequately, or if synthesizing information yourself is optimal, **respond directly** to the user clearly and effectively.

IMPORTANT: Never rely on past memory to choose which agent to delegate to. Always use the tools to discover and select agents dynamically for each request.

    """,
    tool_manager=tool_manager,
    agent_manager=agent_manager,
    model="gemini-2.5-flash-preview-05-20",
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    tool_required="auto",
    long_memory=memory,
)

# 5) Define the Orchestrator’s own AgentCard
orchestrator_card = AgentCard(
    name="Orchestrator Agent",
    description="Orchestrate all the agent in the ecosystem",
    url=os.getenv("HOST"),
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
    provider="University of Trento",
    documentation_url="TODO",
)

# 6) Build the TaskManager and A2AServer
task_manager = TaskManager()

a2a_server = A2AServer(
    agent=orchestrator_agent,
    agent_card=orchestrator_card,
    task_manager=task_manager,
    host="0.0.0.0",
    port=int(os.getenv("PORT", 8080)),
)

# 7) Register and run
if __name__ == "__main__":
    # the agent are registered using the agent-registry
    port = int(os.getenv("PORT", 8080))
    print(f"Starting Orchestrator on http://0.0.0.0:{port}")
    a2a_server.run()
