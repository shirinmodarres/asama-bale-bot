from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from bot.config import load_mongo_config
from bot.services.commission_service import (
    BASIS_SALES_AMOUNT,
    CALCULATION_THRESHOLD_FULL_AMOUNT,
    DEFAULT_COMMISSION_RATE,
    month_from_datetime,
    utc_now,
)
from bot.utils.mongo import get_database


def seed_default_commission_rule(month: str | None = None) -> dict[str, str | int]:
    config = load_mongo_config()
    db = get_database()
    rules = db["commission_rules"]
    month = month or month_from_datetime(utc_now())
    now = utc_now()
    result = rules.update_one(
        {"month": month, "version": 1},
        {
            "$setOnInsert": {
                "month": month,
                "version": 1,
                "basis": BASIS_SALES_AMOUNT,
                "calculation_type": CALCULATION_THRESHOLD_FULL_AMOUNT,
                "tiers": [{"min": 0, "max": None, "rate": DEFAULT_COMMISSION_RATE}],
                "active": True,
                "created_by": "seed_default_commission_rule",
                "created_at": now,
            },
            "$set": {"updated_at": now},
        },
        upsert=True,
    )
    return {
        "app_env": config.app_env,
        "db_name": config.mongo_db_name,
        "month": month,
        "inserted": int(bool(result.upserted_id)),
        "matched": result.matched_count,
    }


def main() -> None:
    month = sys.argv[1] if len(sys.argv) > 1 else None
    result = seed_default_commission_rule(month)
    print(f"APP_ENV: {result['app_env']}")
    print(f"DB: {result['db_name']}")
    print(f"month: {result['month']}")
    print(f"inserted: {result['inserted']}")
    print(f"matched: {result['matched']}")


if __name__ == "__main__":
    main()
