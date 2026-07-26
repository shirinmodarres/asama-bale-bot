import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bot_token: str
    mongo_uri: str
    mongo_db_name: str


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "333801949:rZQidZ6apGIDa7mKxH6oMRQLc39YYA0QAtk").strip()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017").strip()
    mongo_db_name = os.getenv("MONGO_DB_NAME", "asama_bot").strip()

    if not token:
        raise RuntimeError("BOT_TOKEN is required.")

    if not mongo_uri:
        raise RuntimeError("MONGO_URI is required.")

    return Config(
        bot_token=token,
        mongo_uri=mongo_uri,
        mongo_db_name=mongo_db_name,
    )
