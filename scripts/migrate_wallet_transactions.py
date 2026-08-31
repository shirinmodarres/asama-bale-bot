from pathlib import Path
import sys

from pymongo import ASCENDING


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from bot.config import load_mongo_config
from bot.services.wallet_service import transaction_datetime_parts
from bot.utils.mongo import get_database


def detect_source(transaction_id: str) -> str:
    text = str(transaction_id)
    lowered = text.lower()
    if "wallet:ORD-" in text:
        return "commission"
    if "MANUAL-CREDIT" in text:
        return "manual_credit"
    if "lottery-prize" in lowered:
        return "lottery_prize"
    return "legacy"


def migrate_wallet_transactions() -> dict[str, int | str]:
    config = load_mongo_config()
    db = get_database()
    transactions = db["wallet_transactions"]
    transactions.create_index("transaction_id", unique=True)
    transactions.create_index([("telegram_id", ASCENDING), ("created_at", ASCENDING)])
    transactions.create_index([("store_code", ASCENDING), ("created_at", ASCENDING)])
    transactions.create_index([("source", ASCENDING), ("created_at", ASCENDING)])

    copied = 0
    skipped = 0
    users = db["users"].find(
        {"wallet.transactions.0": {"$exists": True}},
        {
            "_id": 0,
            "telegram_id": 1,
            "store_code": 1,
            "wallet.transactions": 1,
        },
    )
    for user in users:
        telegram_id = int(user["telegram_id"])
        store_code = str(user.get("store_code", ""))
        for old in user.get("wallet", {}).get("transactions", []):
            transaction_id = old.get("id") or old.get("transaction_id")
            if not transaction_id:
                skipped += 1
                continue
            if transactions.find_one({"transaction_id": transaction_id}, {"_id": 1}):
                skipped += 1
                continue

            created_at = old.get("created_at", "")
            jalali_date, jalali_month, tehran_time = transaction_datetime_parts(created_at)
            transaction_type = old.get("type", "credit")
            amount = int(old.get("amount") or 0)
            transactions.insert_one(
                {
                    "transaction_id": transaction_id,
                    "telegram_id": telegram_id,
                    "store_code": store_code,
                    "type": transaction_type,
                    "source": detect_source(transaction_id),
                    "amount": amount,
                    "description": old.get("description", ""),
                    "created_at": created_at,
                    "jalali_date": jalali_date,
                    "jalali_month": jalali_month,
                    "tehran_time": tehran_time,
                    "admin_telegram_id": None,
                    "balance_before": None,
                    "balance_after": None,
                }
            )
            copied += 1

    updated_existing = 0
    for transaction in transactions.find(
        {"created_at": {"$nin": [None, ""]}},
        {"_id": 1, "created_at": 1, "jalali_date": 1, "jalali_month": 1, "tehran_time": 1},
    ):
        jalali_date, jalali_month, tehran_time = transaction_datetime_parts(transaction["created_at"])
        if (
            transaction.get("jalali_date") == jalali_date
            and transaction.get("jalali_month") == jalali_month
            and transaction.get("tehran_time") == tehran_time
        ):
            continue
        result = transactions.update_one(
            {"_id": transaction["_id"]},
            {
                "$set": {
                    "jalali_date": jalali_date,
                    "jalali_month": jalali_month,
                    "tehran_time": tehran_time,
                }
            },
        )
        updated_existing += result.modified_count

    return {
        "app_env": config.app_env,
        "db_name": config.mongo_db_name,
        "copied": copied,
        "skipped": skipped,
        "updated_existing": updated_existing,
    }


def main() -> None:
    result = migrate_wallet_transactions()
    print(f"APP_ENV: {result['app_env']}")
    print(f"DB: {result['db_name']}")
    print(f"copied: {result['copied']}")
    print(f"skipped: {result['skipped']}")
    print(f"updated_existing: {result['updated_existing']}")


if __name__ == "__main__":
    main()
