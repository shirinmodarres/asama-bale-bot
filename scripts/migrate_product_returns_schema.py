from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from bot.config import load_mongo_config
from bot.utils.datetime_format import jalali_datetime_parts
from bot.utils.mongo import get_database


def migrate_product_returns_schema() -> dict[str, int | str]:
    config = load_mongo_config()
    db = get_database()
    returns = db["product_returns"]
    orders = db["orders"]
    updated = 0
    skipped = 0

    returns.create_index("return_id", unique=True)
    returns.create_index("tracking_code")
    returns.create_index([("status", 1), ("store_code", 1), ("requested_at", 1)])

    for product_return in returns.find({}):
        changes = {}
        created_at = product_return.get("created_at") or product_return.get("requested_at")
        if not created_at:
            skipped += 1
            continue

        if not product_return.get("status"):
            changes["status"] = "approved"
        changes.setdefault("requested_at", product_return.get("requested_at") or created_at)
        changes.setdefault("reviewed_at", product_return.get("reviewed_at") or created_at)
        changes.setdefault("reviewed_by", product_return.get("reviewed_by"))
        changes.setdefault("rejection_reason", product_return.get("rejection_reason"))
        changes.setdefault("updated_at", product_return.get("updated_at") or created_at)

        if not product_return.get("jalali_date") or not product_return.get("jalali_month"):
            jalali_date, jalali_month, tehran_time = jalali_datetime_parts(created_at)
            changes["jalali_date"] = jalali_date
            changes["jalali_month"] = jalali_month
            changes["tehran_time"] = product_return.get("tehran_time") or tehran_time

        if not product_return.get("product_price") or not product_return.get("sale_month"):
            order = orders.find_one({"id": product_return.get("order_id")}, {"_id": 0})
            unit = None
            if order:
                unit = next(
                    (
                        item
                        for item in order.get("units", [])
                        if int(item.get("index", 0)) == int(product_return.get("unit_index", 0))
                    ),
                    None,
                )
            sold_at = product_return.get("sold_at")
            if not sold_at and unit:
                sold_at = unit.get("validation_decision_at")
            if not sold_at and order:
                sold_at = order.get("updated_at") or order.get("created_at")
            if sold_at:
                changes["sold_at"] = sold_at
                changes["sale_month"] = product_return.get("sale_month") or jalali_datetime_parts(sold_at)[1]
            if order and unit and not product_return.get("product_price"):
                changes["product_price"] = int(unit.get("product_price") or order.get("product_price") or 0)

        result = returns.update_one({"_id": product_return["_id"]}, {"$set": changes})
        updated += result.modified_count

    return {
        "app_env": config.app_env,
        "db_name": config.mongo_db_name,
        "updated": updated,
        "skipped": skipped,
    }


def main() -> None:
    result = migrate_product_returns_schema()
    print(f"APP_ENV: {result['app_env']}")
    print(f"DB: {result['db_name']}")
    print(f"updated: {result['updated']}")
    print(f"skipped: {result['skipped']}")


if __name__ == "__main__":
    main()
