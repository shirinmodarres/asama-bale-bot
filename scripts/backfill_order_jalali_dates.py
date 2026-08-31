from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from bot.config import load_mongo_config
from bot.utils.datetime_format import jalali_datetime_parts
from bot.utils.mongo import get_database


def backfill_order_jalali_dates() -> dict[str, int | str]:
    config = load_mongo_config()
    db = get_database()
    updated = 0
    skipped = 0

    orders = db["orders"].find(
        {},
        {
            "_id": 1,
            "id": 1,
            "created_at": 1,
            "jalali_date": 1,
            "jalali_month": 1,
            "tehran_time": 1,
        },
    )

    for order in orders:
        created_at = order.get("created_at")
        if not created_at:
            skipped += 1
            continue
        jalali_date, jalali_month, tehran_time = jalali_datetime_parts(created_at)
        if (
            order.get("jalali_date") == jalali_date
            and order.get("jalali_month") == jalali_month
            and order.get("tehran_time") == tehran_time
        ):
            skipped += 1
            continue
        result = db["orders"].update_one(
            {"_id": order["_id"]},
            {
                "$set": {
                    "jalali_date": jalali_date,
                    "jalali_month": jalali_month,
                    "tehran_time": tehran_time,
                }
            },
        )
        updated += result.modified_count

    return {
        "app_env": config.app_env,
        "db_name": config.mongo_db_name,
        "updated": updated,
        "skipped": skipped,
    }


def main() -> None:
    result = backfill_order_jalali_dates()
    print(f"APP_ENV: {result['app_env']}")
    print(f"DB: {result['db_name']}")
    print(f"updated: {result['updated']}")
    print(f"skipped: {result['skipped']}")


if __name__ == "__main__":
    main()
