import os
import logging
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

# Import AgentSDK components
from trento_agent_sdk.agent.agent import Agent
from trento_agent_sdk.a2a.models.AgentCard import AgentCard, AgentSkill
from trento_agent_sdk.a2a.TaskManager import TaskManager
from trento_agent_sdk.a2a_server import A2AServer
from trento_agent_sdk.tool.tool_manager import ToolManager

# Try to import memory if available
try:
    from trento_agent_sdk.memory.memory import LongMemory

    memory_available = True
    logger.info("LongMemory functionality is available")
except ImportError:
    memory_available = False
    logger.warning("LongMemory not available, proceeding without memory capability")

# Import SummarizationAgent tools
from tools.get_text.get_text import getText
from tools.summarizer_type.get_correct_format_prompt import fix_latex_formulas
from tools.summarizer_type.get_summarize_chunk_prompt import summarize_chunks
from tools.summarizer_type.get_final_summary_prompt import combine_chunk_summaries
from tools.chunker.chunker_tool import get_chunks

# Test that SDK logging is using our configuration
sdk_logger = logging.getLogger("trento_agent_sdk")
sdk_logger.info("SDK logger initialized with agent's configuration")


# Import SummarizationAgent tools
from tools.get_text.get_text import getText
from tools.summarizer_type.get_correct_format_prompt import fix_latex_formulas
from tools.summarizer_type.get_summarize_chunk_prompt import (
    summarize_chunks,
)

from tools.summarizer_type.get_final_summary_prompt import combine_chunk_summaries
from tools.chunker.chunker_tool import get_chunks

from trento_agent_sdk.tool.tool_manager import ToolManager

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Test that SDK logging is using our configuration
sdk_logger = logging.getLogger("trento_agent_sdk")
sdk_logger.info("SDK logger initialized with agent's configuration")

# Initialize the Google Generative AI client
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError(
        "GOOGLE_API_KEY environment variable is not set. Please create a .env file with your API key."
    )

# Create a tool manager and register summarization tools
# TODO create a tool to get language from the video
tool_manager = ToolManager()
tool_manager.add_tool(getText)
tool_manager.add_tool(get_chunks)
tool_manager.add_tool(summarize_chunks)
tool_manager.add_tool(combine_chunk_summaries)
tool_manager.add_tool(fix_latex_formulas)


memory_prompt = (
    "You are an assistant whose job is to maintain a list of user preferences. You should also include in the memory info caming from possible validation results."
    "You will receive two inputs:\n"
    "1) existing_memories: a JSON array of {id, topic, description}\n"
    "2) chat_history: a string of the latest conversation.\n\n"
    "First you should extract the latest preferences from the chat_history. "
    "If the user has expressed new preferences, add them to the list. "
    "If they have updated existing memories (that are about the preferences), replace them. "
    'Analyze the chat and return a JSON object with exactly one field: "memories_to_add". '
    "The value must be either:\n"
    "  • A list of objects, each with exactly these fields:\n"
    '       "id": the existing memory id to update, OR null if new\n'
    '       "topic": a label for the general area of preference (e.g. "lecture", "cuisine").\n'
    '       "description": a comprehensive description of the user preferences.\n'
    '  • The string "NO_MEMORIES_TO_ADD" if nothing has changed.\n'
    "Do NOT include any other fields or commentary."
)

memory = (
    LongMemory(user_id="test_user", memory_prompt=memory_prompt)
    if memory_available
    else None
)

# Create the summarization agent
summarization_agent = Agent(
    name="Summarization Agent",
    # TODO dynamic chunk size
    system_prompt="""
    THE EXACT SUMMARIZATION WORKFLOW:
You will be given a Google Drive ID as the initial input.
STEP 1: EXTRACTION
* Action: Call the getText tool.
* Input to Tool: The Google Drive ID of the document.
* Expected Tool Output (for your reference to pass to next step): The extracted text content. If the tool returns a string starting with "Error:", you MUST report this error and STOP the workflow.
* Constraint: You MUST use ONLY the getText tool.
STEP 2: CHUNKING
* Action: Call the get_chunks tool.
* Input to Tool: The extracted text content obtained from getText in Step 1.
* Expected Tool Output: A serialized JSON string containing the chunks and metadata. If the tool returns a JSON string where metadata.success is false, or a string starting with "Error:", you MUST report this error and STOP the workflow.
* Constraint: You MUST use ONLY the get_chunks tool.
STEP 3: CHUNK SUMMARIZATION
* Action: Call the summarize_chunks tool.
* Input to Tool: The *entire serialized JSON string* obtained from get_chunks in Step 2. DO NOT attempt to parse or modify this string yourself; pass it directly.
* Expected Tool Output: A serialized JSON string containing the summaries and metadata. If the tool returns a JSON string where metadata.success is false, or a string starting with "Error:", you MUST report this error and STOP the workflow.
* Constraint: You MUST use ONLY the summarize_chunks tool.
STEP 4: COMBINING SUMMARIES
* Action: Call the combine_chunk_summaries tool.
* Input to Tool: The *entire serialized JSON string* containing summaries obtained from summarize_chunks in Step 3. DO NOT attempt to parse or modify this string yourself; pass it directly.
* Expected Tool Output: A single, combined, coherent draft summary (this will be a plain text string). If the tool returns a string starting with "Error:", you MUST report this error and STOP the workflow.
* Constraint: You MUST use ONLY the combine_chunk_summaries tool.
STEP 5: FINAL FORMATTING
* Action: Call the get_correct_format_prompt tool (tool name is fix_latex_formulas).
* Input to Tool: The combined draft summary (plain text string) obtained from combine_chunk_summaries in Step 4.
* Expected Tool Output: The final summary with proper formatting. If the tool returns a string starting with "Error:", you MUST report this error and STOP the workflow.
* Constraint: You MUST use ONLY the get_correct_format_prompt tool.
FINAL GOAL:
Your goal is to successfully orchestrate this entire 5-step process, resulting in a well-structured summary. Upon successful completion of Step 5, present the final formatted summary to the user. If any step explicitly returns an error or indicates failure (e.g., via a 'success: false' field in its JSON output), you must halt the process and report the failure clearly.
REMEMBER: Your role is ONLY to call the tools in the correct order with the correct inputs. DO NOT DEVIATE.
    """,
    tool_manager=tool_manager,
    model="gemini-2.5-flash-preview-04-17",  # Using Gemini model as seen in the code
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    final_tool="fix_latex_formulas",
    tool_required="required",
    long_memory=memory,
)


# Define the agent's capabilities as an AgentCard
agent_card = AgentCard(
    name="Summarization Agent",
    description="An agent that can summarize text from PDFs, documents, and videos",
    url="http://localhost:8001",
    version="1.0.0",
    skills=[
        AgentSkill(
            id="summarization",
            name="Text Summarization",
            # TODO: cambiare la descrizione è solo per non avere problemi adesso
            description="Can summarize text from various sources including PDFs and videos. I'm also able to access local files so I can also recive path of files",
            examples=[
                "Summarize this PDF: https://example.com/document.pdf",
                "Create a summary of this video: https://youtube.com/watch?v=example",
                "Summarize this text: [long text content]",
            ],
        )
    ],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    provider="Trento AI",
    documentation_url="https://example.com/docs",
)

# Create a task manager to handle task lifecycle
task_manager = TaskManager()

# Create the A2A server
a2a_server = A2AServer(
    agent=summarization_agent,
    agent_card=agent_card,
    task_manager=task_manager,
    host="0.0.0.0",
    port=8001,
)

# Run the server
if __name__ == "__main__":
    logger.info("Starting Summarization A2A Server on http://localhost:8001")
    a2a_server.run()
