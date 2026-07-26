import os

from pymongo import MongoClient


def get_mongo_client() -> MongoClient:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017").strip()

    if not mongo_uri:
        raise RuntimeError("MONGO_URI is required.")

    return MongoClient(mongo_uri)


def get_database():
    mongo_db_name = os.getenv("MONGO_DB_NAME", "asama_bot").strip()

    if not mongo_db_name:
        raise RuntimeError("MONGO_DB_NAME is required.")

    client = get_mongo_client()
    return client[mongo_db_name]
