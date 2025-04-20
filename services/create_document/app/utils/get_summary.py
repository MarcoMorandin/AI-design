import uuid
from app.db.mongodb import get_summary_collection
from app.core.config import settings
import logging
import re

logger = logging.getLogger(__name__)


async def get_text_by_id(summary_id: uuid.UUID):
    try:
        summary_collection = get_summary_collection()
        task = await summary_collection.find_one({"_id": summary_id})
        if task is None:
            return None
        
        text = task.get("summary") # poi mettere text
        if text is None:
            return None
        return clean_markdown_file(text)

        

    except Exception as e:
        error_msg = f"Error getting text by summary id {e}"
        logger.error(f"[Task:{summary_id}] {error_msg}")

def clean_markdown_file(content):
    try:
        # Read the file content
        
        
        # Remove leading and trailing ```markdown and ``` patterns
        content = re.sub(r'^```markdown\s*\n', '', content)
        content = re.sub(r'\n```\s*$', '', content)
        
        # Also handle cases where there might be multiple backtick blocks
        content = re.sub(r'```markdown\s*\n', '', content)
        content = re.sub(r'\n```\s*', '\n', content)
        
        # Fix any special characters that might have been incorrectly encoded
        content = content.replace('�', '°')  # Fix degree symbol
        
        return content

    except Exception as e:
        print(f"Error cleaning markdown file: {str(e)}")
        return None

def create_md_file(text, summary_id):
    temp_file_path = settings.TEMP_DIR / f"{str(summary_id)}_downloaded.mmd"
    with open(temp_file_path, "w") as file:
        file.write(text)
    return temp_file_path

