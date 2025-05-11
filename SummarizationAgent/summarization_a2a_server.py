from google import genai
import os
from dotenv import load_dotenv

# Import AgentSDK components
from trento_agent_sdk.agent.agent import Agent
from trento_agent_sdk.agent.swarm import Swarm
from trento_agent_sdk.a2a.models.AgentCard import AgentCard, AgentSkill
from trento_agent_sdk.a2a.TaskManager import TaskManager
from trento_agent_sdk.a2a_server import A2AServer

# Import SummarizationAgent tools
from tools.get_text.get_text import getTextFromPdf, getTextFromVideo
from tools.summarizer_type.get_correct_format_prompt import get_correct_format
from tools.summarizer_type.get_summarize_chunk_prompt import (
    summarize_chunk,
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

client = genai.Client(api_key=api_key)

# Create a tool manager and register summarization tools
#TODO create a tool to get language from the video
tool_manager = ToolManager()
tool_manager.add_tool(getTextFromPdf)
tool_manager.add_tool(getTextFromVideo)
tool_manager.add_tool(get_chunks)
tool_manager.add_tool(get_correct_format)
tool_manager.add_tool(summarize_chunk)
tool_manager.add_tool(generate_final_summary)

# Create the summarization agent
summarization_agent = Agent(
    name="Summarization Agent",
    instructions="""You are an agent that gets text and provides a summary of it. 
If you think the text is too long to provide a good summary, you can split it, 
summarize the chunks, and then combine them. At the end, if the summary contains 
formulas, you must ensure they are properly formatted.

For each step, use the appropiate tool DON'T do it in one shot. Using the appropiate tool, the perfermormance will be much better

When given a document or video, follow these steps:
1. Extract the text using the appropriate tool (getTextFromPdf or getTextFromVideo)
2. If the text is long, use get_chunks tool to split it into manageable pieces
3. For each chunk, use summarize_chunk tool to generate a summary
4. Combine the summaries using generate_final_summary tool
5. Ensure proper formatting with get_correct_format tool

ENSURE THAT YOU FOLLOW ALL THE STEPS ABOVE""",
    tool_manager=tool_manager,
    model="gemini-2.0-flash",  # Using Gemini model as seen in the code
)

# Create a swarm to manage the agent
swarm = Swarm(client)

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
    swarm=swarm,
    agent_card=agent_card,
    task_manager=task_manager,
    host="0.0.0.0",
    port=8000,
)

# Run the server
if __name__ == "__main__":
    print("Starting Summarization A2A Server on http://localhost:8000")
    a2a_server.run()
