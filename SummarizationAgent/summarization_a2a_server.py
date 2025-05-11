from google import genai
import os
from dotenv import load_dotenv

# Import AgentSDK components
from trento_agent_sdk.agent.agent import Agent
from trento_agent_sdk.a2a.models.AgentCard import AgentCard, AgentSkill
from trento_agent_sdk.a2a.TaskManager import TaskManager
from trento_agent_sdk.a2a_server import A2AServer

# Import SummarizationAgent tools
from tools.get_text.get_text import getTextFromPdf, getTextFromVideo
from tools.summarizer_type.get_correct_format_prompt import get_correct_format_prompt
from tools.summarizer_type.get_summarize_chunk_prompt import (
    get_prompt_to_summarize_chunk,
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
tool_manager.add_tool(getTextFromPdf)
tool_manager.add_tool(getTextFromVideo)
tool_manager.add_tool(get_chunks)
tool_manager.add_tool(get_correct_format_prompt)
tool_manager.add_tool(get_prompt_to_summarize_chunk)
tool_manager.add_tool(generate_final_summary)


# Create the summarization agent
summarization_agent = Agent(
    name="Summarization Agent",
    system_prompt="""You are an agent that summarizes text from various sources. You MUST follow this exact process using the provided tools:

1. EXTRACTION: Extract the text using ONLY the appropriate tool:
   - For PDFs: Use the getTextFromPdf tool
   - For videos: Use the getTextFromVideo tool
   
2. CHUNKING: Check if the text is long (over 4000 characters):
   - If it is, use ONLY the get_chunks tool to split it into manageable pieces
   - If not, proceed to step 5 directly with the full text
   
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
    final_tool="get_correct_format_prompt",
    user_id="test_user"
)


# Define the agent's capabilities as an AgentCard
agent_card = AgentCard(
    name="Summarization Agent",
    description="An agent that can summarize text from PDFs, documents, and videos",
    url="http://localhost:8000",
    version="1.0.0",
    skills=[
        AgentSkill(
            id="summarization",
            name="Text Summarization",
            description="Can summarize text from various sources including PDFs and videos",
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
    port=8000,
)

# Run the server
if __name__ == "__main__":
    print("Starting Summarization A2A Server on http://localhost:8000")
    a2a_server.run()
