import uuid
from venv import logger
from app.db.mongodb import get_summary_collection

logger = logger.getLogger(__name__)

async def get_text_by_id(summary_id: uuid.UUID):
    try:
        summary_collection = get_summary_collection()
        task = await summary_collection.find_one({"_id": summary_id})
        if task is None:
            return None
        
        text = task.get("summary") # poi mettere text
        if text is None:
            return None
        return text

    except Exception as e:
        error_msg = f"Error getting text by summary id {e}"
        logger.error(f"[Task:{summary_id}] {error_msg}")