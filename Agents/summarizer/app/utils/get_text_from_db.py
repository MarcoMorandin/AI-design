import uuid
from app.db.mongodb import get_task_collection

async def get_text_by_id(task_id: uuid.UUID):
    task_collection = get_task_collection()
    task = await task_collection.find_one({"_id": task_id})
    if task is None:
        return None
    
    text = task.get("summary") # poi mettere text
    if text is None:
        return None
    return text