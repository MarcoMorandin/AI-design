from fastapi import FastAPI
from pymongo import MongoClient

# Adjust imports to be absolute for direct execution from main.py
from config import (
    MONGO_URI,
    MONGO_DB_NAME,
)

app = FastAPI()


@app.on_event("startup")
async def startup_db_client():
    try:
        app.state.mongo_client = MongoClient(MONGO_URI)
        app.state.db = app.state.mongo_client[MONGO_DB_NAME]
        app.state.users_collection = app.state.db["users"]
        app.state.users_collection.create_index("googleId", unique=True)
        print("Successfully connected to MongoDB and attached to app.state.")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        app.state.mongo_client = None
        app.state.db = None
        app.state.users_collection = None


@app.on_event("shutdown")
async def shutdown_db_client():
    if hasattr(app.state, "mongo_client") and app.state.mongo_client:
        app.state.mongo_client.close()
        print("MongoDB connection closed.")


# Adjust import to be absolute
import routes
