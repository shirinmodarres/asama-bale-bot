from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from bot.config import load_mongo_config
from bot.utils.mongo import get_database
from data.static_data import ADMINS, SALES_EXPERTS, SALES_MANAGER, STORES


ORG_COLLECTIONS = ("admins", "sales_managers", "sales_experts", "stores")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def seed_org_data(replace: bool = False) -> dict[str, int | str]:
    config = load_mongo_config()
    db = get_database()
    now = utc_now()

    if replace:
        for collection_name in ORG_COLLECTIONS:
            db[collection_name].delete_many({})

    admin_count = 0
    for admin in ADMINS:
        db.admins.update_one(
            {"telegram_id": int(admin["telegram_id"])},
            {
                "$set": {
                    "telegram_id": int(admin["telegram_id"]),
                    "full_name": admin.get("full_name", ""),
                    "is_active": admin.get("is_active", admin.get("active", True)),
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        admin_count += 1

    manager_count = 0
    if SALES_MANAGER:
        db.sales_managers.update_one(
            {"telegram_id": int(SALES_MANAGER["telegram_id"])},
            {
                "$set": {
                    "telegram_id": int(SALES_MANAGER["telegram_id"]),
                    "full_name": SALES_MANAGER.get("full_name", ""),
                    "is_active": SALES_MANAGER.get("is_active", SALES_MANAGER.get("active", True)),
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        manager_count = 1

    expert_count = 0
    for expert_key, expert in SALES_EXPERTS.items():
        db.sales_experts.update_one(
            {"expert_key": expert_key},
            {
                "$set": {
                    "expert_key": expert_key,
                    "telegram_id": int(expert["telegram_id"]),
                    "full_name": expert.get("full_name", ""),
                    "is_active": expert.get("is_active", expert.get("active", True)),
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        expert_count += 1

    store_count = 0
    for code, store in STORES.items():
        db.stores.update_one(
            {"code": str(code)},
            {
                "$set": {
                    "code": str(code),
                    "name": store.get("name", ""),
                    "expert_key": store.get("expert_key", ""),
                    "is_active": store.get("is_active", store.get("active", True)),
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        store_count += 1

    return {
        "app_env": config.app_env,
        "db_name": config.mongo_db_name,
        "admins": admin_count,
        "sales_managers": manager_count,
        "sales_experts": expert_count,
        "stores": store_count,
    }


def main() -> None:
    parser = ArgumentParser(description="Seed organization data into MongoDB.")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete org collections before seeding.",
    )
    args = parser.parse_args()

    result = seed_org_data(replace=args.replace)
    print(f"APP_ENV: {result['app_env']}")
    print(f"DB: {result['db_name']}")
    print(f"admins: {result['admins']}")
    print(f"sales_managers: {result['sales_managers']}")
    print(f"sales_experts: {result['sales_experts']}")
    print(f"stores: {result['stores']}")


if __name__ == "__main__":
    main()
