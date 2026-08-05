import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


@dataclass(frozen=True)
class Config:
    app_env: str
    bot_token: str
    mongo_uri: str
    mongo_db_name: str


@dataclass(frozen=True)
class MongoConfig:
    app_env: str
    mongo_uri: str
    mongo_db_name: str


def _load_env_file() -> None:
    if load_dotenv:
        load_dotenv()


def _app_env() -> str:
    app_env = os.getenv("APP_ENV", "local").strip().lower()
    if app_env not in {"local", "production"}:
        raise RuntimeError("APP_ENV must be 'local' or 'production'.")
    return app_env


def _suffix(app_env: str) -> str:
    return "PRODUCTION" if app_env == "production" else "LOCAL"


def load_mongo_config() -> MongoConfig:
    _load_env_file()
    app_env = _app_env()
    suffix = _suffix(app_env)

    mongo_uri = (
        os.getenv(f"MONGO_URI_{suffix}")
        or "mongodb://localhost:27017"
    ).strip()
    mongo_db_name = (
        os.getenv(f"MONGO_DB_NAME_{suffix}")
        or ("asama_bot" if app_env == "production" else "asama_bot_local")
    ).strip()

    if not mongo_uri:
        raise RuntimeError(f"MONGO_URI_{suffix} is required.")

    if not mongo_db_name:
        raise RuntimeError(f"MONGO_DB_NAME_{suffix} is required.")

    return MongoConfig(
        app_env=app_env,
        mongo_uri=mongo_uri,
        mongo_db_name=mongo_db_name,
    )


def load_config() -> Config:
    _load_env_file()
    app_env = _app_env()
    mongo_config = load_mongo_config()

    suffix = _suffix(app_env)
    token = (os.getenv(f"BOT_TOKEN_{suffix}") or "").strip()

    if not token:
        raise RuntimeError(f"BOT_TOKEN_{suffix} is required.")

    return Config(
        app_env=app_env,
        bot_token=token,
        mongo_uri=mongo_config.mongo_uri,
        mongo_db_name=mongo_config.mongo_db_name,
    )
