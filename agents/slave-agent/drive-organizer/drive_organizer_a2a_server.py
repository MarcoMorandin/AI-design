import os
import sys
import signal
import traceback
import logging
from typing import Dict, Any
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import AgentSDK components
from trento_agent_sdk.agent.agent import Agent
from trento_agent_sdk.a2a.models.AgentCard import AgentCard, AgentSkill
from trento_agent_sdk.a2a.TaskManager import TaskManager
from trento_agent_sdk.a2a_server import A2AServer
from trento_agent_sdk.tool.tool_manager import ToolManager

# Import Drive Organizer tools
from tools.retrieve_user_data.retrieve_user_data import retrieve_user_data
from tools.get_folder_structure.get_folder_structure import get_folder_structure
from tools.get_document_content.get_document_content import get_document_content
from tools.analyze_document.analyze_document import analyze_document
from tools.generate_folder_structure.generate_folder_structure import (
    generate_folder_structure,
)
from tools.reorganize_drive.reorganize_drive import reorganize_drive
from tools.get_course_folder_id.get_course_folder_id import get_course_folder_id

from trento_agent_sdk.memory.memory import LongMemory

# Set up proper logging for production environment
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get environment settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
API_KEY = os.getenv("GEMINI_API_KEY")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))
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
    logger.info(f"Starting Drive Organizer A2A Server in {ENVIRONMENT} environment")
    logger.info(f"Service version: {SERVICE_VERSION}")

    # Register signal handlers for graceful shutdown
    def handle_sigterm(signum, frame):
        logger.info("Received SIGTERM. Initiating graceful shutdown...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    # Yield control back to FastAPI
    yield

    # Shutdown: log service shutdown
    logger.info("Shutting down Drive Organizer A2A Server")


# Create FastAPI app with lifespan management
app = FastAPI(lifespan=lifespan)

# Configure CORS middleware
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=(origins if ENVIRONMENT != "production" else ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create and register tools
try:
    logger.info("Initializing tool manager")
    tool_manager = ToolManager()
    tool_manager.add_tool(retrieve_user_data)
    tool_manager.add_tool(get_folder_structure)
    tool_manager.add_tool(get_document_content)
    tool_manager.add_tool(analyze_document)
    tool_manager.add_tool(generate_folder_structure)
    tool_manager.add_tool(reorganize_drive)
    tool_manager.add_tool(get_course_folder_id)
    logger.info("Tool manager initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize tool manager: {str(e)}")
    logger.debug(traceback.format_exc())
    sys.exit(1)

# Create the drive organizer agent with comprehensive system prompt
try:
    logger.info(f"Initializing Drive Organizer Agent with model {MODEL}")

    memory = LongMemory(
        user_id="drive_organizer_agent",
        memory_prompt="Remember previous folder organization tasks you've completed and use that experience to improve your organization strategy.",
    )

    drive_organizer_agent = Agent(
        name="Drive Organizer Agent",
        system_prompt="""You are an agent that organizes Google Drive folders for university courses. You MUST follow this exact process using the provided tools:

1. USER AUTHENTICATION: Retrieve user data using the retrieve_user_data tool:
   - Extract the user_id from the input message (the user will provide it)
   - Call retrieve_user_data with the user_id and course_name
   - This returns a JSON response like: {"success": true, "user_data": {...}}
   - EXTRACT and SAVE the "user_data" field (which is a dictionary) from this response
   - The user_data field contains the full user profile with Google Drive credentials
   
2. COURSE FOLDER LOOKUP: Find the course folder ID using the get_course_folder_id tool:
   - Pass the user_data DICTIONARY (extracted from step 1) as the user_data parameter
   - Pass the course_name as the course_name parameter
   - DO NOT pass the entire response from retrieve_user_data - only pass the user_data field
   - This will return the folder ID for the specified course, or an error if not found
   
3. FOLDER EXPLORATION: Get the folder structure using the get_folder_structure tool:
   - Pass the folder ID from step 2 as the folder_id parameter
   - Pass the user_data DICTIONARY (from step 1) as the user_data parameter
   - This will return a list of files and folders in the specified location
   
4. CONTENT ANALYSIS: For EACH document in the folder:
   - Use the get_document_content tool with file_id and the user_data DICTIONARY
   - Use the analyze_document tool to create a summary and identify topics/categories
   
5. ORGANIZATION PLANNING: Once all documents are analyzed:
   - Use the generate_folder_structure tool to propose a logical organization
   - This will create a plan with folders representing course sections
   
6. REORGANIZATION: Implement the organization plan:
   - Use the reorganize_drive tool with the proposed_structure, user_data DICTIONARY, and folder_id
   - Confirm the changes were successful

CRITICAL EXAMPLE OF CORRECT USAGE:
1. Call: retrieve_user_data(user_id="123", course_name="Math")
   Response: {"success": true, "user_data": {"googleTokens": {...}, "googleId": "123", ...}}
2. Extract user_data: user_data = {"googleTokens": {...}, "googleId": "123", ...}
3. Call: get_course_folder_id(user_data=user_data, course_name="Math")

CRITICAL: Always pass the user_data DICTIONARY (not the entire response from retrieve_user_data) to tools that require user_data parameter.

DO NOT skip any steps. DO NOT try to complete any step without using the appropriate tool. Every step MUST use the corresponding tool.""",
        tool_manager=tool_manager,
        model=MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        final_tool="reorganize_drive",
        long_memory=memory,
        tool_required="required",
    )
    logger.info("Drive Organizer Agent initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize agent: {str(e)}")
    logger.debug(traceback.format_exc())
    sys.exit(1)

# Define the agent's capabilities as an AgentCard
agent_card = AgentCard(
    name="Drive Organizer Agent",
    description="An agent that organizes Google Drive folders for university courses into logical sections.",
    url=f"{HOST}:{PORT}",
    version=SERVICE_VERSION,
    skills=[
        AgentSkill(
            id="organize-drive",
            name="Google Drive Folder Organization",
            description="Can organize Google Drive folders based on document content analysis",
            examples=[
                "organize my course 'Introduction to Computer Science' for user 111369155660754322920",
                "reorganize my course materials for 'Data Structures' for user 111369155660754322920",
                "structure my university course 'Machine Learning Fundamentals' for user 111369155660754322920",
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
try:
    logger.info("Initializing A2A Server")
    a2a_server = A2AServer(
        agent=drive_organizer_agent,
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
        if drive_organizer_agent and tool_manager:
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
        logger.info(f"Starting Drive Organizer A2A Server on http://{HOST}:{PORT}")
        # Use uvicorn server for better performance in production
        if ENVIRONMENT == "production" and int(os.getenv("WORKER_COUNT", "4")) > 1:
            # For production with multiple workers, use the import string
            import subprocess

            subprocess.run(
                [
                    "uvicorn",
                    "drive_organizer_a2a_server:app",
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
