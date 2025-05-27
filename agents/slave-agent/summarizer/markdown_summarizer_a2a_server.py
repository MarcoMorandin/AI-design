import os
import sys
import signal
import traceback  # Added
import logging
from typing import Dict, Any
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI, Response, status  # Added Response, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import AgentSDK components
from trento_agent_sdk.agent.agent import Agent
from trento_agent_sdk.a2a.models.AgentCard import AgentCard, AgentSkill
from trento_agent_sdk.a2a.TaskManager import TaskManager
from trento_agent_sdk.a2a_server import A2AServer
from trento_agent_sdk.tool.tool_manager import ToolManager

# Import utility functions
from api_utils import retry_api_call

# Import Markdown Summarizer tools
from tools.chunk_markdown.chunk_markdown import chunk_markdown
from tools.summarize_chunk.summarize_chunk import summarize_chunk
from tools.format_summary.format_summary import format_summary
from tools.fetch_markdown_content.fetch_markdown_content import fetch_markdown_content
from trento_agent_sdk.memory.memory import LongMemory

# Set up proper logging (simplified to match the first example)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get environment settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
API_KEY = os.getenv("GEMINI_API_KEY")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))  # Kept specific port for this service
MODEL = os.getenv("MODEL", "gemini-2.0-flash")
BASE_URL = os.getenv(
    "BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
)
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")

# Validate essential environment variables
if not API_KEY:
    logger.critical(
        "GEMINI_API_KEY environment variable is not set. Please create a .env file with your API key."
    )
    sys.exit(1)


# FastAPI startup and shutdown events (Copied and adapted from first)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: log service start and register signal handlers
    logger.info(
        f"Starting Markdown Summarizer A2A Server in {ENVIRONMENT} environment"
    )  # Adapted name
    logger.info(f"Service version: {SERVICE_VERSION}")

    # Register signal handlers for graceful shutdown
    def handle_signal(signum, frame):
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        logger.info(f"Received {signal_name}. Initiating graceful shutdown...")
        sys.exit(0)  # Or raise an exception that uvicorn can catch for shutdown

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)  # Handle Ctrl+C

    # Yield control back to FastAPI
    yield

    # Shutdown: cleanup and close resources
    logger.info("Shutting down Markdown Summarizer A2A Server")


# Create FastAPI app with lifespan management (Copied from first)
app = FastAPI(lifespan=lifespan)

# Configure CORS middleware (Copied from first)
origins = ["*"]  # Allow all origins for simplicity or configure as needed

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        origins if ENVIRONMENT != "production" else ["*"]
    ),  # Simplified for example
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create and register tools
try:
    logger.info("Initializing tool manager")
    tool_manager = ToolManager()

    # Register markdown summarization tools
    tool_manager.add_tool(chunk_markdown)
    tool_manager.add_tool(summarize_chunk)
    tool_manager.add_tool(format_summary)
    tool_manager.add_tool(fetch_markdown_content)

    logger.info(
        "Tool manager initialized successfully"
    )  # Changed message slightly for consistency
except Exception as e:
    logger.critical(f"Failed to initialize tool manager: {str(e)}")  # Changed message
    logger.debug(traceback.format_exc())  # Added traceback
    sys.exit(1)

    # Create the agent with tools

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

# Initialize memory with error handling
base_memory = LongMemory(user_id="test_user", memory_prompt=memory_prompt)


logger.info(
    f"Initializing Markdown Summarizer Agent with model {MODEL}"
)  # Changed message

try:
    # Initialize the agent with retry mechanism
    def create_agent():
        return Agent(
            name="Markdown Summarizer Agent",
            instructions="""You are an intelligent Markdown Summarizer Agent that helps users create high-quality summaries of markdown documents.

Your capabilities include:
1. Retrieving markdown documents from a database using their document ID.
2. Chunking large markdown documents into semantically meaningful sections.
3. Generating summaries of each chunk in the user's preferred style.
4. Combining and formatting these summaries into a cohesive final summary.

Available summary styles:
- Technical: Preserves mathematical formulas, technical terms, and uses LaTeX formatting where appropriate.
- Bullet-points: Creates hierarchical bullet-point lists that capture key information.
- Standard: Creates a flowing narrative summary with cohesive paragraphs.
- Concise: Creates a very brief summary focusing only on essential information.
- Detailed: Creates a comprehensive summary with main points and supporting details.

Always maintain markdown formatting where appropriate in your summaries.

When processing requests, follow these steps:
1. If given a document ID, use fetch_markdown_content to retrieve the document from the database
2. If the markdown content is long, use chunk_markdown to split it into manageable chunks
3. Use summarize_chunk to summarize each chunk in the requested style
4. Use format_summary to combine the summaries into a cohesive final document

Always maintain proper error handling and inform the user if a document cannot be found or if any step fails.
""",
            tool_manager=tool_manager,
            model=MODEL,
            api_key=API_KEY,
            base_url=BASE_URL,  # Corrected BASE_URL for Gemini (or None if appropriate)
            final_tool="format_summary",
            tool_required="required",
            long_memory=base_memory,
        )

    # Use retry logic when creating the agent
    summarizer_agent = retry_api_call(
        create_agent, max_retries=3, initial_delay=2.0, backoff_factor=2.0
    )

    logger.info("Markdown Summarizer Agent initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize agent: {str(e)}")
    logger.debug(traceback.format_exc())
    sys.exit(1)


# Define the agent's capabilities as an AgentCard
agent_card = AgentCard(
    name="Markdown Summarizer Agent",
    description="An intelligent agent that summarizes markdown documents in various styles",
    url=f"{HOST}:{PORT}",
    version=SERVICE_VERSION,
    skills=[
        AgentSkill(
            id="markdown-summarization",
            name="Markdown Summarization",
            description="Can retrieve, chunk, summarize, and format markdown documents in various styles (technical, bullet-points, standard, concise, detailed)",
            examples=[
                "Summarize this markdown document in a technical style",
                "Create a bullet-point summary of this content",
                "Generate a concise summary of this document",
                "Retrieve and summarize document with ID 'doc123' in bullet-point style",
            ],
        )
    ],
    default_input_modes=["text/plain", "text/markdown"],
    default_output_modes=["text/plain", "text/markdown"],
    provider="University of Trento",
    documentation_url="TODO",
)

# Create a task manager to handle task lifecycle
task_manager = TaskManager()

# Create the A2A server
try:
    logger.info("Initializing A2A Server")

    # Use retry logic for A2A server initialization
    def create_a2a_server():
        return A2AServer(
            agent=summarizer_agent,  # Use the correct agent
            agent_card=agent_card,
            task_manager=task_manager,
            host=HOST,
            port=PORT,
        )

    a2a_server = retry_api_call(
        create_a2a_server, max_retries=3, initial_delay=2.0, backoff_factor=2.0
    )

    # Mount the A2A server's FastAPI app to our app at the root path
    app.mount("/", a2a_server.app)
    logger.info("A2A Server initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize A2A server: {str(e)}")
    logger.debug(traceback.format_exc())
    sys.exit(1)


# Add custom health check endpoint (Copied and adapted from first)
@app.get("/health", include_in_schema=False)
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring and container orchestration."""
    try:
        # Check if the agent and tool manager are initialized
        if summarizer_agent and tool_manager:  # Adapted to summarizer_agent
            return {
                "status": "ok",
                "version": SERVICE_VERSION,
                "environment": ENVIRONMENT,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }
        else:
            logger.error("Health check failed: agent or tool manager not initialized")
            return Response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content="Service components not fully initialized",
            )
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content="Internal server error during health check",
        )


# Run the server (Copied and adapted from first)
if __name__ == "__main__":
    try:
        logger.info(
            f"Starting Markdown Summarizer A2A Server on http://{HOST}:{PORT}"
        )  # Adapted name
        # Use uvicorn server for better performance in production
        if ENVIRONMENT == "production" and int(os.getenv("WORKER_COUNT", "4")) > 1:
            # For production with multiple workers, use the import string
            # Assuming the file is named markdown_summarizer_a2a_server.py
            # You might need to adjust "markdown_summarizer_a2a_server:app"
            # if your filename is different.
            import subprocess

            try:
                subprocess.run(
                    [
                        "uvicorn",
                        f"{__name__}:app",  # Dynamically use module name
                        "--host",
                        "0.0.0.0",  # HOST variable could also be used
                        "--port",
                        str(PORT),
                        "--log-level",
                        "info",
                        "--workers",
                        os.getenv("WORKER_COUNT", "4"),
                    ]
                )
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt. Shutting down gracefully...")
        else:
            # For development or single worker, we can use the app instance
            uvicorn.run(
                app,  # Run the main app instance
                host="0.0.0.0",  # HOST variable could also be used
                port=PORT,
                log_level="info" if ENVIRONMENT == "production" else "debug",
                workers=1,  # Or read from WORKER_COUNT for consistency
            )
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down gracefully...")
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}")
        logger.debug(traceback.format_exc())  # Added traceback
        sys.exit(1)
