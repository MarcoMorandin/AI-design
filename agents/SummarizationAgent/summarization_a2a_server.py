from google import genai
import os
from dotenv import load_dotenv

# Import AgentSDK components
from trento_agent_sdk.agent.agent import Agent
from trento_agent_sdk.a2a.models.AgentCard import AgentCard, AgentSkill
from trento_agent_sdk.a2a.TaskManager import TaskManager
from trento_agent_sdk.a2a_server import A2AServer
from trento_agent_sdk.memory.memory import LongMemory


# Import SummarizationAgent tools
from tools.get_text.get_text import getText
from tools.summarizer_type.get_correct_format_prompt import fix_latex_formulas
from tools.summarizer_type.get_summarize_chunk_prompt import (
    summarise_chunk,
)
from tools.summarizer_type.get_final_summary_prompt import generate_final_summary
from tools.chunker.chunker_tool import get_chunks
from trento_agent_sdk.tool.tool_manager import ToolManager

# Load environment variables
load_dotenv()

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
tool_manager.add_tool(fix_latex_formulas)
tool_manager.add_tool(summarise_chunk)
tool_manager.add_tool(generate_final_summary)


memory_prompt = (
    "You are an assistant whose job is to maintain a list of user preferences. "
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

memory = LongMemory(user_id="test_user", memory_prompt=memory_prompt)

# Create the summarization agent
summarization_agent = Agent(
    name="Summarization Agent",
    # TODO dynamic chunk size
    system_prompt="""
    You are an agent that doesn't know how to summarize document but know which tool has to be called to summarize texts.
    You MUST follow this exact process using the provided tools:

1. EXTRACTION: Extract the text using the getText tool:
   - Pass the Google Drive ID of the document to the getText tool
   - The tool will retrieve the already processed text from MongoDB
   
2. CHUNKING: Split into manageable chunks:
   - use ONLY the get_chunks tool to split it into manageable pieces
   
3. CHUNK SUMMARIZATION: For EACH chunk:
   - Use ONLY the get_prompt_to_summarize_chunk tool to get the prompt
   - Summarize each chunk one by one, using the prompt from the tool
   
4. COMBINING SUMMARIES: When all chunks are summarized:
   - Use ONLY the get_final_summary_prompt tool with text_was_splitted=True
   - Combine all summaries into a final coherent summary
   
5. FINAL FORMATTING: For the final summary:
   - Use ONLY the get_correct_format_prompt tool to ensure proper formatting of any formulas
   - Apply any final formatting corrections

DO NOT skip any steps. DO NOT try to complete any step without using the appropriate tool. Every step MUST use the corresponding tool. Your goal is to generate clear, well-structured summaries that accurately capture the key points of the original content.""",
    tool_manager=tool_manager,
    model="gemini-2.0-flash",  # Using Gemini model as seen in the code
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
    print("Starting Summarization A2A Server on http://localhost:8001")
    a2a_server.run()
