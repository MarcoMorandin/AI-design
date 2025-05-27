import os
from dotenv import load_dotenv
from trento_agent_sdk.agent.agent import Agent
from trento_agent_sdk.a2a.models.AgentCard import AgentCard, AgentSkill
from trento_agent_sdk.a2a.TaskManager import TaskManager
from trento_agent_sdk.a2a_server import A2AServer
from trento_agent_sdk.memory.memory import LongMemory
from trento_agent_sdk.tool.tool_manager import ToolManager
from tools.rag_tool import RAG_tool

# Load environment variables
load_dotenv()

# Initialize the Google Generative AI client
api_key = os.getenv("GEMINI_API_KEY")


# collecton where to retrieve document
rag_tool = RAG_tool(user_id="RAG_usertest_user")

tool_manager = ToolManager()
tool_manager.add_tool(rag_tool.get_response)


memory_prompt = (
    "You are the LongMemory of an agent that implement the RAG (Retrieval Augmented Generation). Your goal is to store useful information about the user preferences (for instance the structure of the answer or something like this) \n"
    "You will receive two inputs:\n"
    "1) existing_memories: a JSON array of {id, topic, description}\n"
    "2) chat_history: a string of the latest conversation.\n\n"
    "First you should extract the latest preferences from the chat_history. "
    "If the user has expressed new preferences, add them to the list. "
    "If they have updated existing memories (that are about the preferences), replace them. "
    'Analyze the chat and return a JSON object with exactly one field: "memories_to_add". '
    "The value must be either:\n"
    "  • A list of objects, each with exactly these fields:\n"
    '      – "id": the existing memory id to update, OR null if new\n'
    '      – "topic": a label for the general area of preference (e.g. "lecture", "cuisine").\n'
    '      – "description": a comprenshicve description of the user preferences.\n'
    '  • The string "NO_MEMORIES_TO_ADD" if nothing has changed.\n'
    "Do NOT include any other fields or commentary."
)


memory = LongMemory(user_id="rag_agent", memory_prompt=memory_prompt)


# Create the summarization agent
chat_with_document_agent = Agent(
    name="Retrieval Augmented Generation Agent",
    system_prompt="""
    Your an an AI agent that use the RAG (Retrieval Augmented Generation) to answe to the user questions.
    For each question the user ask you must use the get_response tool and answer based on the retrieved information.
    If you have already use the tool does NOT reuse it since it will give the exact same result.
    If the retrieved information are not enough to answer just say that you don't know since there is not enough information.""",
    tool_manager=tool_manager,
    model="gemini-2.0-flash",  # Using Gemini model as seen in the code
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    tool_required="auto",
    long_memory=memory,
)


# Define the agent's capabilities as an AgentCard
agent_card = AgentCard(
    name="Question and answering agent",
    description="An agent that can respond to the user questions",
    url=f"{os.getenv('HOST')}:{os.getenv('PORT')}",
    version="1.0.0",
    skills=[
        AgentSkill(
            id="chat_with_document_rag",
            name="Chat with document",
            description="You can answer to the user questions based on the information retrieved from the RAG (Retrieval Augmented Generation)",
            examples=[
                "User question: What does this document says?",
                "Response: This document is about [rest of the answer...] ",
            ],
        )
    ],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    provider="University of Trento",
    documentation_url="TODO",
)

# Create a task manager to handle task lifecycle
task_manager = TaskManager()

# Create the A2A server
a2a_server = A2AServer(
    agent=chat_with_document_agent,
    agent_card=agent_card,
    task_manager=task_manager,
    host="0.0.0.0",
    port=int(os.getenv("PORT", "8002")),
)

# Run the server
if __name__ == "__main__":
    port = os.getenv("PORT", "8002")
    print(f"Starting RAG A2A Server on http://localhost:{port}")
    a2a_server.run()
