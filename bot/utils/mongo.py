from pymongo import MongoClient

from bot.config import load_mongo_config


def get_mongo_client() -> MongoClient:
    mongo_uri = load_mongo_config().mongo_uri

    if not mongo_uri:
        raise RuntimeError("MONGO_URI is required.")

    return MongoClient(mongo_uri)


def get_database():
    mongo_db_name = load_mongo_config().mongo_db_name

    if not mongo_db_name:
        raise RuntimeError("MONGO_DB_NAME is required.")

    client = get_mongo_client()
    return client[mongo_db_name]
