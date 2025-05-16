import os
from typing import Optional, Dict, Any
from pymongo import MongoClient
import logging
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
logger = logging.getLogger(__name__)

# MongoDB connection settings from environment variables
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")


def convert_datetime_to_str(data):
    """
    Recursively convert datetime objects to strings in a dictionary or list.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, (dict, list)):
                data[key] = convert_datetime_to_str(value)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, datetime):
                data[i] = item.isoformat()
            elif isinstance(item, (dict, list)):
                data[i] = convert_datetime_to_str(item)
    return data


async def retrieve_user_data(user_id: str, course_name: str = None) -> Dict[str, Any]:
    """Retrieves user data from MongoDB based on Google user ID.
    Returns the full user object including Google credentials for Drive operations.

    Args:
        user_id: The user ID to retrieve data for
        course_name: The name of the course to be organized

    Returns:
        Dict containing user data, success status and message

    Tool:
        name: retrieve_user_data
        description: Retrieves user data from the database
        input_schema:
            type: object
            properties:
                user_id:
                    type: string
                    description: The user ID to retrieve data for
                course_name:
                    type: string
                    description: The name of the course to be organized
            required:
                - user_id
        output_schema:
            type: object
            properties:
                user_data:
                    type: object
                    description: The user data from MongoDB including Google credentials
                success:
                    type: boolean
                    description: Whether the operation was successful
                message:
                    type: string
                    description: Status message
    """
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        users_collection = db["users"]

        # Find user by Google ID
        user_data = users_collection.find_one({"googleId": user_id})

        # Close MongoDB connection
        client.close()

        if not user_data:
            logger.error(f"User with Google ID {user_id} not found")
            return {
                "success": False,
                "message": f"User with Google ID {user_id} not found",
                "user_data": None,
            }

        # Convert ObjectId to string for JSON serialization
        if "_id" in user_data:
            user_data["_id"] = str(user_data["_id"])
            
        # Convert datetime objects to strings for JSON serialization
        user_data = convert_datetime_to_str(user_data)

        logger.debug(f"Successfully retrieved user data for {user_id}")
        return {
            "success": True,
            "message": "User data retrieved successfully",
            "user_data": user_data,
        }

    except Exception as e:
        logger.error(f"Error retrieving user data: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error retrieving user data: {str(e)}",
            "user_data": None,
        }
