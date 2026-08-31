from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pymongo.errors import DuplicateKeyError

from bot.config import load_mongo_config
from bot.services.order_service import utc_now
from bot.utils.mongo import get_database
from bot.utils.normalize import normalize_digits


def migrate_product_tracking_codes() -> dict[str, int | str]:
    config = load_mongo_config()
    db = get_database()
    tracking_codes = db["product_tracking_codes"]
    tracking_codes.create_index("tracking_code", unique=True)

    copied = 0
    skipped = 0
    orders = db["orders"].find(
        {"units.validation_status": "approved"},
        {"_id": 0, "_sequence": 0},
    )
    for order in orders:
        for unit in order.get("units", []):
            if unit.get("validation_status") != "approved":
                skipped += 1
                continue
            tracking = unit.get("tracking_code", {})
            if tracking.get("type") != "text" or not tracking.get("value"):
                skipped += 1
                continue
            tracking_code = normalize_digits(tracking["value"])
            if tracking_codes.find_one({"tracking_code": tracking_code}, {"_id": 1}):
                skipped += 1
                continue

            now = utc_now()
            try:
                tracking_codes.insert_one(
                    {
                        "tracking_code": tracking_code,
                        "product_key": order.get("product_key", ""),
                        "product_code": order.get("product_code", order.get("product_key", "")),
                        "product_name": order.get("product_name", ""),
                        "order_id": order["id"],
                        "unit_index": int(unit["index"]),
                        "store_code": str(order.get("store_code", "")),
                        "seller_telegram_id": int(order.get("seller_telegram_id")),
                        "status": "sold",
                        "sold_at": unit.get("validation_decision_at") or order.get("updated_at") or now,
                        "returned_at": None,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                copied += 1
            except DuplicateKeyError:
                skipped += 1

    return {
        "app_env": config.app_env,
        "db_name": config.mongo_db_name,
        "copied": copied,
        "skipped": skipped,
    }


def main() -> None:
    result = migrate_product_tracking_codes()
    print(f"APP_ENV: {result['app_env']}")
    print(f"DB: {result['db_name']}")
    print(f"copied: {result['copied']}")
    print(f"skipped: {result['skipped']}")


if __name__ == "__main__":
    main()
