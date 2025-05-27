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
from trento_agent_sdk.memory.memory import LongMemory

# Import API utility functions
from api_utils import retry_api_call

# Import Exam Generator tools
from tools.fetch_document_content import fetch_document_content
from tools.generate_exam_structure import generate_exam_structure
from tools.generate_exam_questions import generate_exam_questions
from tools.format_exam import format_exam

# Import custom logging config - just importing is enough to initialize it
import logging_config

# Set up proper logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get environment settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8003"))
MODEL = os.getenv("MODEL", "gemini-2.0-flash")
BASE_URL = os.getenv(
    "BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
)
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")

# Validate essential environment variables
if not API_KEY:
    logger.critical(
        "API_KEY (GEMINI_API_KEY or OPENAI_API_KEY) not set. Please create a .env file with your API key."
    )
    sys.exit(1)


# FastAPI startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting Exam Generator Agent")
    signal.signal(signal.SIGINT, lambda sig, frame: shutdown(app))
    signal.signal(signal.SIGTERM, lambda sig, frame: shutdown(app))

    yield

    # Shutdown logic
    logger.info("Shutting down Exam Generator Agent")


def shutdown(app: FastAPI = None):
    logger.info("Shutdown signal received, exiting...")
    sys.exit(0)


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
    tool_manager.add_tool(fetch_document_content)
    tool_manager.add_tool(generate_exam_structure)
    tool_manager.add_tool(generate_exam_questions)
    tool_manager.add_tool(format_exam)
    logger.info("Tool manager initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize tool manager: {str(e)}")
    logger.debug(traceback.format_exc())
    sys.exit(1)

# Create memory prompt for the agent
memory_prompt = (
    "You are the LongMemory of an exam generator agent. Your goal is to store useful information about the user preferences.\n"
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
    '      – "topic": a label for the general area of preference (e.g. "exam_type", "format", "difficulty").\n'
    '      – "description": a comprehensive description of the user preference.\n'
    '  • The string "NO_MEMORIES_TO_ADD" if nothing has changed.\n'
    "Do NOT include any other fields or commentary."
)

memory = LongMemory(user_id="exam_generator", memory_prompt=memory_prompt)

# Create the Exam Generator agent
try:
    logger.info("Initializing Exam Generator Agent")
    exam_generator_agent = Agent(
        name="Exam Generator Agent",
        instructions="""You are an Exam Generator Agent that creates academic exams based on educational content stored in MongoDB.

Your capabilities include:
1. Retrieving document content from MongoDB using Google Drive file IDs
2. Analyzing content to generate exam structures with appropriate topics and question types
3. Creating comprehensive exam questions with answers based on the document content
4. Formatting exams into professional documents ready for use

When processing requests to generate an exam, follow these steps in order:

1. RETRIEVE DOCUMENT: Use the fetch_document_content tool to retrieve the document content using the provided Google Drive file ID
2. GENERATE STRUCTURE: Use the generate_exam_structure tool to create an exam structure with topics and question types
   - Pass the document content, file name, exam type, difficulty level, and number of questions
   - This will return a structured plan for the exam
3. CREATE QUESTIONS: Use the generate_exam_questions tool to create the actual exam questions
   - Pass the document content and exam structure from the previous step
   - Specify whether answers should be included
4. FORMAT EXAM: Use the format_exam tool to format the exam into a presentable document
   - Choose the format type (markdown, plain_text)
   - Specify whether to include an answer key

DO NOT skip any steps. Use the tools in the exact order listed above. Each step requires the output from the previous step.

You may ask the user for preferences on:
- Exam type (quiz, test, final exam)
- Difficulty level (easy, moderate, difficult)
- Number of questions
- Whether to include answers
- Format type (markdown, plain_text)

The final output should be a well-formatted exam document and optionally an answer key.""",
        tool_manager=tool_manager,
        model=MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        final_tool="format_exam",
        long_memory=memory,
        tool_required="required",
    )
    logger.info("Exam Generator Agent initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize agent: {str(e)}")
    logger.debug(traceback.format_exc())
    sys.exit(1)

# Define the agent's capabilities as an AgentCard
agent_card = AgentCard(
    name="Exam Generator Agent",
    description="An agent that generates academic exams based on content from Google Drive documents.",
    url=f"{HOST}:{PORT}",
    version=SERVICE_VERSION,
    skills=[
        AgentSkill(
            id="generate-exam",
            name="Academic Exam Generation",
            description="Can create academic exams based on content from Google Drive documents",
            examples=[
                "Generate a quiz from document ID 12345abcde",
                "Create a difficult final exam from document ID 98765fghij with 20 questions",
                "Make an easy test from document ID abcde12345 and include answers",
            ],
        )
    ],
    default_input_modes=["text/plain"],
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
            agent=exam_generator_agent,
            agent_card=agent_card,
            task_manager=task_manager,
            host="0.0.0.0",
            port=PORT,
        )

    a2a_server = retry_api_call(
        create_a2a_server, max_retries=3, initial_delay=2.0, backoff_factor=2.0
    )

    logger.info("A2A Server initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize A2A server: {str(e)}")
    logger.debug(traceback.format_exc())
    sys.exit(1)


# Add health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Exam Generator Agent"}


# Run the server
if __name__ == "__main__":
    logger.info(f"Starting Exam Generator A2A Server on http://{HOST}:{PORT}")
    a2a_server.run()
