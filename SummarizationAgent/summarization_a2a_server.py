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
tool_manager.add_tool(getTextFromPdf)
tool_manager.add_tool(getTextFromVideo)
tool_manager.add_tool(get_chunks)
tool_manager.add_tool(fix_latex_formulas)
tool_manager.add_tool(summarise_chunk)
tool_manager.add_tool(generate_final_summary)


# Create the summarization agent
summarization_agent = Agent(
    name="Summarization Agent",
    system_prompt = """
You are a pipeline summarisation agent. Strictly follow the steps:

1. **Extract text**
   • For PDFs call `get_text_from_pdf`
   • For videos call `get_text_from_video`

2. **Chunk if needed**
   • If the extracted text is > 4000 characters call `get_chunks`
   • Else skip to step 3 with a single‑item list `[full_text]`

3. **Summarise each chunk**
   • For every chunk in the list call `summarise_chunk`

4. **Combine**
   • When all chunks are summarised call `combine_chunk_summaries`
     (argument `chunks_summaries` = the list returned in step 3)

5. **Latex / Markdown fix (final tool)**
   • Call `fix_latex_formulas` on the combined summary.  
     Return its output to the user with no further tool calls.

TOOLS MUST BE CALLED IN THIS ORDER. Do not call any tool twice unless you really need to
process another chunk. When step 5 is done, answer the user.""",

    tool_manager=tool_manager,
    model="gemini-2.0-flash",  # Using Gemini model as seen in the code
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    final_tool="fix_latex_formulas",
    user_id="test_user",
    tool_required="auto" #TODO: mettere required per farlo funzionare
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
            #TODO: cambiare la descrizione è solo per non avere problemi adesso
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
    port=8000,
)

# Run the server
if __name__ == "__main__":
    print("Starting Summarization A2A Server on http://localhost:8000")
    a2a_server.run()
