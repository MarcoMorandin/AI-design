import os
import sys
import signal
import traceback
import logging
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI, Response, status, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import logging configuration
from logging_config import setup_logging

# Import AgentSDK components
from trento_agent_sdk.agent.agent import Agent
from trento_agent_sdk.a2a.models.AgentCard import AgentCard, AgentSkill
from trento_agent_sdk.a2a.TaskManager import TaskManager
from trento_agent_sdk.a2a_server import A2AServer
from trento_agent_sdk.tool.tool_manager import ToolManager

# Import SummarizationAgent tools
from tools.get_text.get_text import getTextFromPdf, getTextFromVideo
from tools.summarizer_type.get_correct_format_prompt import get_correct_format_prompt
from tools.summarizer_type.get_summarize_chunk_prompt import (
    get_prompt_to_summarize_chunk,
)
from tools.summarizer_type.get_final_summary_prompt import get_final_summary_prompt
from tools.chunker.chunker_tool import get_chunks

# Set up proper logging for production environment
setup_logging()
logger = logging.getLogger(__name__)

# Load environment variables - prioritize .env file in production
load_dotenv()

# Get environment settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
API_KEY = os.getenv("GEMINI_API_KEY")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
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


# FastAPI startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: log service start and register signal handlers
    logger.info(f"Starting Summarization A2A Server in {ENVIRONMENT} environment")
    logger.info(f"Service version: {SERVICE_VERSION}")

    # Register signal handlers for graceful shutdown
    def handle_sigterm(signum, frame):
        logger.info("Received SIGTERM. Initiating graceful shutdown...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    # Yield control back to FastAPI
    yield

    # Shutdown: log service shutdown
    logger.info("Shutting down Summarization A2A Server")


# Create FastAPI app with lifespan management
app = FastAPI(lifespan=lifespan)

# Configure CORS middleware
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        origins if ENVIRONMENT != "production" else ["*"]
    ),  # More permissive in dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create and register tools
try:
    logger.info("Initializing tool manager")
    tool_manager = ToolManager()
    tool_manager.add_tool(getTextFromPdf)
    tool_manager.add_tool(getTextFromVideo)
    tool_manager.add_tool(get_chunks)
    tool_manager.add_tool(get_correct_format_prompt)
    tool_manager.add_tool(get_prompt_to_summarize_chunk)
    tool_manager.add_tool(get_final_summary_prompt)
    logger.info("Tool manager initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize tool manager: {str(e)}")
    logger.debug(traceback.format_exc())
    sys.exit(1)

# Create the summarization agent with comprehensive system prompt
try:
    logger.info(f"Initializing Summarization Agent with model {MODEL}")
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
        model=MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        final_tool="get_correct_format_prompt",
    )
    logger.info("Summarization Agent initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize agent: {str(e)}")
    logger.debug(traceback.format_exc())
    sys.exit(1)

# Define the agent's capabilities as an AgentCard
agent_card = AgentCard(
    name="Summarization Agent",
    description="An agent that is specialized in summarizing text from PDFs and videos.",
    url=f"http://{HOST}:{PORT}",
    version=SERVICE_VERSION,
    skills=[
        AgentSkill(
            id="summarization",
            name="Text Summarization",
            description="Can summarize text from PDFs and videos",
            examples=[
                "Summarize this PDF: test.pdf",
                "explain with bullet point this PDF: test.pdf",
                "make a technical explanation of this PDF: test.pdf",
            ],
        )
    ],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    provider="Arcangeli and Morandin",
    documentation_url="Work in progress",
)

# Create a task manager to handle task lifecycle
task_manager = TaskManager()

# Create the A2A server
try:
    logger.info("Initializing A2A Server")
    a2a_server = A2AServer(
        agent=summarization_agent,
        agent_card=agent_card,
        task_manager=task_manager,
        host=HOST,
        port=PORT,
    )
    # Mount the A2A server's FastAPI app to our app at the root path
    app.mount("/", a2a_server.app)
    logger.info("A2A Server initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize A2A server: {str(e)}")
    logger.debug(traceback.format_exc())
    sys.exit(1)


# Add custom health check endpoint
@app.get("/health", include_in_schema=False)
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring and container orchestration."""
    try:
        # Check if the agent and tool manager are initialized
        if summarization_agent and tool_manager:
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


# Run the server
if __name__ == "__main__":
    try:
        logger.info(f"Starting Summarization A2A Server on http://{HOST}:{PORT}")
        # Use uvicorn server for better performance in production
        if ENVIRONMENT == "production" and int(os.getenv("WORKER_COUNT", "4")) > 1:
            # For production with multiple workers, use the import string
            import subprocess

            subprocess.run(
                [
                    "uvicorn",
                    "summarization_a2a_server:app",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    str(PORT),
                    "--log-level",
                    "info",
                    "--workers",
                    os.getenv("WORKER_COUNT", "4"),
                ]
            )
        else:
            # For development or single worker, we can use the app instance
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=PORT,
                log_level="info" if ENVIRONMENT == "production" else "debug",
                workers=1,
            )
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}")
        logger.debug(traceback.format_exc())
        sys.exit(1)
