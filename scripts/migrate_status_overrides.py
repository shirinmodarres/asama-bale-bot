from datetime import datetime, timezone
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from bot.config import load_mongo_config
from bot.utils.mongo import get_database


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def migrate_status_overrides() -> dict[str, int | str]:
    config = load_mongo_config()
    db = get_database()
    now = utc_now()

    product_count = 0
    for item in db["admin_product_status"].find({}):
        category_key = item.get("category_key")
        product_key = item.get("product_key")
        if not category_key or not product_key:
            continue
        result = db["products"].update_one(
            {
                "category_key": category_key,
                "$or": [
                    {"product_key": product_key},
                    {"product_code": product_key},
                ],
            },
            {
                "$set": {
                    "is_active": bool(item.get("active", True)),
                    "active": bool(item.get("active", True)),
                    "updated_at": now,
                }
            },
        )
        product_count += result.modified_count

    store_count = 0
    for item in db["admin_store_status"].find({}):
        code = str(item.get("_id") or item.get("code") or item.get("store_code") or "").strip()
        if not code:
            continue
        result = db["stores"].update_one(
            {"code": code},
            {
                "$set": {
                    "is_active": bool(item.get("active", True)),
                    "active": bool(item.get("active", True)),
                    "updated_at": now,
                }
            },
        )
        store_count += result.modified_count

    expert_count = 0
    for item in db["admin_expert_status"].find({}):
        expert_key = str(item.get("_id") or item.get("expert_key") or item.get("key") or "").strip()
        if not expert_key:
            continue
        result = db["sales_experts"].update_one(
            {"expert_key": expert_key},
            {
                "$set": {
                    "is_active": bool(item.get("active", True)),
                    "active": bool(item.get("active", True)),
                    "updated_at": now,
                }
            },
        )
        expert_count += result.modified_count

    return {
        "app_env": config.app_env,
        "db_name": config.mongo_db_name,
        "products_updated": product_count,
        "stores_updated": store_count,
        "experts_updated": expert_count,
    }


def main() -> None:
    result = migrate_status_overrides()
    print(f"APP_ENV: {result['app_env']}")
    print(f"DB: {result['db_name']}")
    print(f"products_updated: {result['products_updated']}")
    print(f"stores_updated: {result['stores_updated']}")
    print(f"experts_updated: {result['experts_updated']}")


if __name__ == "__main__":
    main()
